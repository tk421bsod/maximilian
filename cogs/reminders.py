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

#Thanks to Vexs for help with this.
time_regex = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
time_dict = {"h":3600, "s":1, "m":60, "d":86400}

class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        matches = time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument(f"{k} is an invalid unit of time! only h/m/s/d are valid!")
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number!")
        return time

class reminders(commands.Cog):
    '''Reminders to do stuff. (and todo lists!)'''
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
            reminders = self.bot.db.exec_query("select * from reminders order by user_id desc", False, True)
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


    @commands.command(hidden=True, aliases=['reminders', 'reminder'], help="Set a reminder for sometime in the future. This reminder will persist even if the bot is restarted.")
    async def remind(self, ctx, action, time:TimeConverter, *, reminder):
        if action == "add":
            await ctx.send("Setting your reminder...")
            #get the date the reminder will fire at
            currenttime = datetime.datetime.now()
            remindertime = currenttime+datetime.timedelta(0, round(time))
            #generate uuid
            uuid = str(uuid_generator.uuid4())
            #add the reminder to the database
            self.bot.db.exec(f"insert into reminders(user_id, channel_id, reminder_time, now, reminder_text, uuid) values(%s, %s, %s, %s, %s, %s)", (ctx.author.id, ctx.channel.id, remindertime, datetime.datetime.now(), reminder, uuid))
            await self.update_reminder_cache()
            await ctx.send(f"Ok, in {humanize.precisedelta(remindertime-currenttime, format='%0.0f')}: '{reminder}'")
            await self.handle_reminder(ctx.author.id, ctx.channel.id, remindertime, currenttime, reminder, uuid)

    @commands.command(aliases=["to-do", "todos"], help=f"A list of stuff to do. You can view your todo list by using `<prefix>todo` and add stuff to it using `<prefix>todo add <thing>`. You can delete stuff from the list using `<prefix>todo delete <thing>`.")
    async def todo(self, ctx, action="list", *, entry=None):
        #TODO: subcommands?
        if action == "add":
            try:
                if not entry:
                    return await ctx.send(f"You didn't say what you wanted to add to your todo list. Run this command again with what you wanted to add. For example, you can add 'fix error handling' to your todo list by using `{await self.bot.get_prefix(ctx.message)}todo add fix error handling`.")
                elif entry in [i['entry'] for i in [j for j in list(self.bot.todo_entries.values())][0] if i['user_id'] == ctx.author.id]:
                    return await ctx.send("That entry already exists.")
            except IndexError:
                pass
            try:
                self.bot.db.exec("insert into todo values(%s, %s, %s)", (ctx.author.id, entry, datetime.datetime.now()))
                await self.update_todo_cache()
                entrycount = self.bot.db.exec(f'select count(entry) from todo where user_id=%s', (ctx.author.id))['count(entry)']
                await ctx.send(embed=discord.Embed(title=f"\U00002705 Successfully added that to your todo list. \nYou now have {entrycount} {'entries' if entrycount != 1 else 'entry'} in your list.", color=self.bot.config['theme_color']))
            except:
                #dm traceback
                await self.bot.core.send_traceback()
                await ctx.send("There was an error while adding that to your todo list. Try again later.")
                await self.bot.core.send_debug(ctx)
            return
        if action == "delete" or action == "remove":
            try:
                if not entry:
                    return await ctx.send("You didn't say what entry you wanted to delete. For example, if 'fix todo deletion' was the first entry in your list and you wanted to delete it, use 'todo delete 1'.")
                try:
                    int(entry)
                except (TypeError, ValueError):
                    return await ctx.send("You need to specify the number of the entry you want to delete. For example, if 'fix todo deletion' was the first entry in your list and you wanted to delete it, you would use `todo delete 1`.")
                self.bot.db.exec("delete from todo where entry=%s and user_id=%s", (self.bot.todo_entries[ctx.author.id][int(entry)-1]['entry'], ctx.author.id))
                entrycount = self.bot.db.exec(f'select count(entry) from todo where user_id=%s', (ctx.author.id))['count(entry)']
                await self.update_todo_cache()
                await ctx.send(embed=discord.Embed(title=f"\U00002705 Successfully deleted that from your todo list. \nYou now have {entrycount} {'entries' if entrycount != 1 else 'entry'} in your list.", color=self.bot.config['theme_color']))
            except IndexError:
                return await ctx.send("Sorry, that entry couldn't be found.")
            except KeyError:
                await ctx.send("You don't have anything in your todo list.")
            except:
                await self.bot.core.send_traceback()
                await ctx.send("Hmm, something went wrong while deleting that from your todo list. Try again later.")
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
                        await ctx.send(f"\U000026a0 It looks like your todo list is too long to show in a single message.\nOnly showing entries 1-{count+1}.")
                        break
                if entrystring:
                    embed = discord.Embed(title=f"{ctx.author}'s todo list", description=entrystring, color=self.bot.config['theme_color'])
                    return await ctx.send(embed=embed)
            except KeyError:
                return await ctx.send("It doesn't look like you have anything in your todo list. Try adding something to it.")
            except discord.HTTPException:
                return await ctx.send(f"Sorry, entry {count} in your todo list is wayyyy too long to display. Try deleting it or viewing it on its own.")
                #paginator when
            except:
                await self.bot.core.send_traceback()
                await ctx.send("Hmm, something went wrong while trying to show your todo list. Try again later.")
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
                return await ctx.send(f"Sorry, that entry couldn't be found. Your todo list currently has {len(self.bot.todo_entries[ctx.author.id])} entries.")
            except KeyError:
                return await ctx.send("It doesn't look like you have anything in your todo list.")
            except:
                await self.bot.core.send_traceback()
                await ctx.send("Sorry, something went wrong when trying to show that entry. Try again later.")
                await self.bot.core.send_debug(ctx)

async def setup(bot):
    await bot.add_cog(reminders(bot, True))

async def teardown(bot):
    await bot.remove_cog(reminders(bot))
