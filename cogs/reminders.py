import asyncio
import datetime
import inspect
import logging
import os
import random
import re
import sys
import traceback
import uuid as uuid_generator #prevent conflict with the local variable 'uuid'

import discord
import humanize
from discord.ext import commands

time_regex = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
time_dict = {"h":3600, "s":1, "m":60, "d":86400}

class RelativeTimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        matches = time_regex.findall(argument.lower())
        time = 0
        if argument == "add":
            await ctx.send("The 'add' option was removed in 1.1.0. Remove it from the command so the time value gets interpreted correctly.")
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument(f"{k} is an invalid unit of time! only h/m/s are valid!")
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number!")
        if time == 0:
            raise commands.BadArgument("Sorry, that amount of time is invalid.")
        return time
    
class AbsoluteTimeConverter:
    """Convert an absolute date & time to a datetime."""

    FORMAT_STRINGS = {"NUMERIC_MONTH_DAY_YEAR":"%m/%d/%Y,%H:%M:%S", "NUMERIC_DAY_MONTH_YEAR":"%d/%m/%Y,%H:%M:%S", "ABBREVIATED_MONTH_DAY_YEAR":"%b,%d,%Y,%H:%M:%S", "ABBREVIATED_DAY_MONTH_YEAR":"%d,%b,%Y,%H:%M:%S", "FULL_MONTH_DAY_YEAR":"%B,%d,%Y,%H:%M:%S", "FULL_DAY_MONTH_YEAR":"%d,%B,%Y,%H:%M:%S"}

    @staticmethod
    def _preprocess(t):
        logger = logging.getLogger("common")
        t = t.strip()
        #Replace all spaces with commas w/o putting 2 commas next to each other
        t = t.replace(', ', ',').replace(' ', ',')
        #Remove punctuation from abbreviations and remove date suffixes (3rd, 4th, 1st, etc)
        for item in ['.', 'st', 'nd', 'rd', 'th']:
            t_replaced = t.replace(item, '')
            if t_replaced != t:
                logger.debug(f"Removed '{item}'")
            t = t_replaced
        #If there's no time, append a default time
        if ":" not in t:
            logger.debug("No time provided, assuming noon")
            t += ",12:00:00"
        #Pad time value with seconds if needed
        if len(t.split(":")) == 2:
            logger.debug("Adding seconds to time")
            parts = t.split(":")
            #Is this 12 hour time?
            if ',' in parts[1]:
                m, p = parts[1].split(",")
                parts[1] = f':{m}:00,{p}'
            else:
                parts[1] = f':{parts[1]}:00'
            t = parts[0] + parts[1]
        return t

    @staticmethod
    def convert(t):
        logger = logging.getLogger("common")
        logger.debug(f"Trying to convert provided absolute time {t}")
        #Get the time value into a format we can apply our format strings to
        t = AbsoluteTimeConverter._preprocess(t)
        logger.debug(f"Time string after preprocessing: {t}")
        for format_type, format_string in AbsoluteTimeConverter.FORMAT_STRINGS.items():
            logger.debug(f"Trying format {format_type}")
            try:
                ret = datetime.datetime.strptime(t, format_string)
            except ValueError:
                logger.debug("Trying 12 hour time")
                try:
                    format_string_12hr = format_string.replace("%H", "%I") + ",%p"
                    ret = datetime.datetime.strptime(t, format_string_12hr)
                except ValueError:
                    continue
            logger.debug("Converted time string to datetime.")
            return ret 
        logger.debug("Couldn't convert the provided time.")
        return None

class reminders(commands.Cog):
    '''Reminders to do stuff. (and to-do lists!)'''
    def __init__(self, bot, load=False):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.bot.todo_entries = {}
        self.bot.reminders = {}
        #don't update cache on teardown (manual unload or automatic unload on shutdown)
        if load:
            asyncio.create_task(self.update_todo_cache())
            asyncio.create_task(self.update_reminder_cache(True))

    async def update_reminder_cache(self, load=False):
        await self.bot.wait_until_ready()
        self.logger.info("Updating reminder cache...")
        new_reminders = {}
        reminders = {}
        try:
            reminders = self.bot.db.exec("select * from reminders order by user_id desc", ())
            if not reminders:
                 reminders = []
            if not isinstance(reminders, list):
                reminders = [reminders]
            for item in reminders:
                new_reminders[item['user_id']] = [i for i in reminders if i['user_id'] == item['user_id']]
                #only start handling reminders if the extension was loaded, we don't want reminders to fire twice once this function is
                #called by handle_reminder
                if load:
                    asyncio.create_task(self.handle_reminder(item['user_id'], item['channel_id'], item['reminder_time'], item['now'], item['reminder_text'], item['uuid']))
                    self.logger.info(f"Started handling a reminder for user {item['user_id']}")
            self.bot.reminders = new_reminders
        except:
            self.logger.info("Couldn't update reminder cache! Is there anything in the database?")
            traceback.print_exc()
        self.logger.info("Updated reminder cache!")
        
    async def update_todo_cache(self):
        await self.bot.wait_until_ready()
        self.logger.info("Updating todo cache...")
        new_todo_entries = {}
        try:
            todolists = self.bot.db.exec("select * from todo order by timestamp desc", ())
            if not isinstance(todolists, list):
                todolists = [todolists]
            for item in todolists:
                new_todo_entries[item['user_id']] = [i for i in todolists if i['user_id'] == item['user_id']]
        except:
            self.logger.info("Couldn't update todo cache! Is anything in the database?")
            traceback.print_exc()
        self.bot.todo_entries = new_todo_entries
        self.logger.info("Updated todo cache!")
    
    async def handle_reminder(self, user_id, channel_id, remindertime, reminderstarted, remindertext, uuid):
        #waait for as long as needed
        self.logger.info("handling reminder...")
        #make timestamp human readable before sleeping (otherwise it just shows up as 0 seconds)
        hrtimedelta = humanize.precisedelta(remindertime-reminderstarted, format='%0.0f')
        await discord.utils.sleep_until(remindertime)
        #then send the reminder, with the time in a more human readable form than a bunch of seconds. (i.e '4 hours ago' instead of '14400 seconds ago')
        await self.bot.get_channel(channel_id).send(f"<@{user_id}> {hrtimedelta} ago: '{remindertext}'")
        #and delete it from the database
        self.bot.db.exec(f"delete from reminders where uuid=%s", (uuid))
        await self.update_reminder_cache()

    async def _get_target_relative_time(self, ctx, time_string):
        #Obtain our time offset in seconds.
        target_time = await RelativeTimeConverter().convert(ctx, time_string)
        #Make a datetime representing when this reminder will fire.
        currenttime = datetime.datetime.now()
        target_time = currenttime + datetime.timedelta(0, round(target_time))
        return target_time

    @commands.command(aliases=['reminder'], help="Set a reminder for sometime in the future. This reminder will persist even if the bot is restarted.\n\nThis command lets you specify a moment in time through its `time` or `target_time` parameter.\nThe following formats are supported:\nMM/DD/YYYY,HH:MM - `04/26/2025,13:50`\nMonth names (abbreviated or full) followed by day and year - `April 26 2025 23:00`\nDay/Month/Year also works, as well as 12 hour time.\nYou can also specify seconds if you want to be extra precise.\nYour specified time will need to be put in quotes if there are spaces in it.\nSomething like `\"26 April 2025 1:50 PM\"` would work perfectly fine.")
    async def remind(self, ctx, time_string, *, reminder):
        logger = logging.getLogger(__name__)
        #First, convert the time string into a datetime.
        #Did we receive an absolute time? We can make a good guess, but we can't be 100% sure. 
        #Something like "20d 4h" could get interpreted as an absolute time.
        processed_as_absolute = False
        time_string = time_string.strip()
        if [marker in time_string for marker in [' ', ',', '/', ':']]:
            #Try to convert the given time.
            logger.debug("Time is probably absolute, trying to convert to datetime")
            target_time = AbsoluteTimeConverter.convert(time_string)
            #If we couldn't convert, try to process it like a relative time.
            if not target_time:
                try:
                    logger.debug("Trying to process as relative time")
                    target_time = await self._get_target_relative_time(ctx, time_string)
                    logger.debug("Processed as relative time")
                except:
                    import traceback;traceback.print_exc()
                    return await ctx.send("Sorry, the amount of time you provided couldn't be interpreted. You'll need to provide it in a format I can understand.\nCheck the help entry for this command for details on the accepted formats.")
            else:
                logger.debug("Conversion finished")
                processed_as_absolute = True
        else:
            logger.debug("Time is probably relative, converting to datetime")
            target_time = await self._get_target_relative_time(ctx, time_string)
        if target_time < datetime.datetime.now():
            return await ctx.send("Your reminder can't be set for a date/time in the past.")
        #Now, ask if this time was correct.
        #If confirmed, calls set_reminder with our new datetime and reminder.
        #Build the message to send:
        if processed_as_absolute:
            desc = "The amount of time you provided was interpreted as a specific point in time.\n"
        else:
            desc = "The amount of time you provided was added to the current time to get a new time.\n"
        #Add the target time to the confirmation.
        desc += f"Your reminder is going to be set for: \n**{target_time}**\nIf this looks correct, press \u2705 to finish setting your reminder."
        reminder_confirmation_embed = discord.Embed(title="Does this time look right?", description=desc, color=self.bot.config['theme_color'])
        reminder_confirmation_embed.set_footer(text="If this isn't correct, try a different date/time format. Check the help entry for this command for details. Still not correct? Consider reporting the issue.")
        logger.debug("Sending confirmation")
        msg = await ctx.send(embed=reminder_confirmation_embed)
        self.bot.confirmation(self.bot, msg, ctx, self.set_reminder, target_time, reminder)

    async def set_reminder(self, reaction, confirmation_message, ctx, confirmed, target_time, reminder):
        if not confirmed:
            return await ctx.send("Not setting the reminder.")
        await ctx.send("Setting your reminder...")
        currenttime = datetime.datetime.now()
        #generate uuid
        uuid = str(uuid_generator.uuid4())
        #add the reminder to the database
        self.bot.db.exec(f"insert into reminders(user_id, channel_id, reminder_time, now, reminder_text, uuid) values(%s, %s, %s, %s, %s, %s)", (ctx.author.id, ctx.channel.id, target_time, datetime.datetime.now(), reminder, uuid))
        await self.update_reminder_cache()
        await ctx.send("Ok, in {}: '{}'".format(humanize.precisedelta(target_time-currenttime, format='%0.0f'), reminder))
        await self.handle_reminder(ctx.author.id, ctx.channel.id, target_time, currenttime, reminder, uuid)

    @commands.command(hidden=True)
    async def reminders(self, ctx):
        #Display a list of reminders.
        try:
            active_reminders = self.bot.reminders[ctx.author.id]
            if not active_reminders:
                return await ctx.send("You don't have any reminders set.")
        except KeyError:
            return await ctx.send("You don't have any reminders set.")
        desc = ""
        for count, reminder in enumerate(active_reminders):
            desc += f"**{count+1}:**\n"
            desc += f"*Created {humanize.naturaldelta(datetime.datetime.now()-reminder['now'])} ago.*\n"
            try:
                scheduled = humanize.naturaltime(reminder['reminder_time'],future=True)
            except OverflowError:
                scheduled = "wayyyyyyyyyy too far in the future to display"
            desc += f"*Scheduled for {scheduled}.*\n"
            desc += f"*Message: `{reminder['reminder_text']}`*\n\n"
        await ctx.send(embed=discord.Embed(title=f"{ctx.author.name}'s reminders:", description=desc, color=self.bot.config['theme_color']))

    @commands.command(aliases=["to-do", "todos"], help=f"A list of stuff to do. You can view your to-do list by using `<prefix>todo` and add stuff to it using `<prefix>todo add <thing>`. You can delete stuff from the list using `<prefix>todo delete <thing>`.")
    async def todo(self, ctx, action="list", *, entry=None):
        #TODO: subcommands?
        if action == "add":
            try:
                if not entry:
                    return await ctx.send(f"You didn't say what you wanted to add to your to-do list. Run this command again with what you wanted to add. For example, you can add 'fix error handling' to your to-do list by using `{await self.bot.get_prefix(ctx.message)}todo add fix error handling`.")
                elif entry in [i['entry'] for i in [j for j in list(self.bot.todo_entries.values())][0] if i['user_id'] == ctx.author.id]:
                    return await ctx.send("That entry already exists.")
            except IndexError:
                pass
            try:
                self.bot.db.exec("insert into todo values(%s, %s, %s)", (ctx.author.id, entry, datetime.datetime.now()))
                await self.update_todo_cache()
                entrycount = self.bot.db.exec(f'select count(entry) from todo where user_id=%s', (ctx.author.id))['count(entry)']
                await ctx.send(embed=discord.Embed(title=f"\U00002705 Successfully added that to your to-do list. \nYou now have {entrycount} {'entries' if entrycount != 1 else 'entry'} in your list.", color=self.bot.config['theme_color']))
            except:
                #dm traceback
                await self.bot.core.send_traceback()
                await ctx.send("There was an error while adding that to your to-do list. Try again later.")
                await self.bot.core.send_debug(ctx)
            return
        if action == "delete" or action == "remove":
            try:
                if not entry:
                    return await ctx.send("You didn't say what entry you wanted to delete. For example, if 'fix to-do deletion' was the first entry in your list and you wanted to delete it, use 'to-do delete 1'.")
                try:
                    int(entry)
                except (TypeError, ValueError):
                    return await ctx.send("You need to specify the number of the entry you want to delete. For example, if 'fix to-do deletion' was the first entry in your list and you wanted to delete it, you would use `todo delete 1`.")
                self.bot.db.exec("delete from todo where entry=%s and user_id=%s", (self.bot.todo_entries[ctx.author.id][int(entry)-1]['entry'], ctx.author.id))
                entrycount = self.bot.db.exec(f'select count(entry) from todo where user_id=%s', (ctx.author.id))['count(entry)']
                await self.update_todo_cache()
                await ctx.send(embed=discord.Embed(title=f"\U00002705 Successfully deleted that from your to-do list. \nYou now have {entrycount} {'entries' if entrycount != 1 else 'entry'} in your list.", color=self.bot.config['theme_color']))
            except IndexError:
                return await ctx.send("Sorry, that entry couldn't be found.")
            except KeyError:
                await ctx.send("You don't have anything in your to-do list.")
            except:
                await self.bot.core.send_traceback()
                await ctx.send("Hmm, something went wrong while deleting that from your to-do list. Try again later.")
                await self.bot.core.send_debug(ctx)
            return
        if action == "deleteall":
            try:
                return await self.bot.deletion_request(self.bot).create_request("todo", ctx)
            except self.bot.DeletionRequestAlreadyActive:
                return await ctx.send("A deletion request is already active.")
        if action == "list" or entry == None:
            entrystring = ""
            try:
                for count, value in enumerate(self.bot.todo_entries[ctx.author.id]):
                    entrystring += f"{count+1}. `{value['entry']}`\nCreated {humanize.precisedelta(value['timestamp'], format='%0.0f')} ago.\n\n"
                    if len(entrystring) > 3800:
                        await ctx.send(f"\U000026a0 It looks like your to-do list is too long to show in a single message.\nOnly showing entries 1-{count+1}.")
                        break
                if entrystring:
                    embed = discord.Embed(title=f"{ctx.author}'s to-do list", description=entrystring, color=self.bot.config['theme_color'])
                    return await ctx.send(embed=embed)
            except KeyError:
                return await ctx.send("It doesn't look like you have anything in your to-do list. Try adding something to it.")
            except discord.HTTPException:
                return await ctx.send(f"Sorry, entry {count} in your to-do list is wayyyy too long to display. Try deleting it or viewing it on its own.")
                #paginator when
            except:
                await self.bot.core.send_traceback()
                await ctx.send("Hmm, something went wrong while trying to show your to-do list. Try again later.")
                await self.bot.core.send_debug(ctx)
        if action in ["display", "show"]:
            if not entry:
                return await ctx.send("You didn't say what entry you wanted to show. Want to show the first entry? Use `todo show 1`.")
            try:
                entry = int(entry)
            except (TypeError, ValueError):
                return await ctx.send("You need to specify the number of the entry you want to show. Want to show the first entry? Use `todo show 1`.")
            try:
                if entry < 1:
                    #wrap around to 2 more than max length
                    entry = len(self.bot.todo_entries[ctx.author.id])+2
                await ctx.send(embed=discord.Embed(title=f"Entry \#{entry}", description=f"Created {humanize.precisedelta(self.bot.todo_entries[ctx.author.id][entry-1]['timestamp'], format='%0.0f')} ago.\n Entry text:\n`{self.bot.todo_entries[ctx.author.id][entry-1]['entry']}`", color=self.bot.config['theme_color']))
            except discord.HTTPException:
                return await ctx.send("Sorry, that entry is wayyyyyyyyy too long to display. You should probably delete it.")
            except IndexError:
                return await ctx.send(f"Sorry, that entry couldn't be found. Your to-do list currently has {len(self.bot.todo_entries[ctx.author.id])} entries.")
            except KeyError:
                return await ctx.send("It doesn't look like you have anything in your to-do list.")
            except:
                await self.bot.core.send_traceback()
                await ctx.send("Sorry, something went wrong when trying to show that entry. Try again later.")
                await self.bot.core.send_debug(ctx)

async def setup(bot):
    await bot.add_cog(reminders(bot, True))

async def teardown(bot):
    await bot.remove_cog(reminders(bot))
