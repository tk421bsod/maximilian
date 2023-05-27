import asyncio
import datetime
import time
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

class Deletion:
    __slots__ = ("timestamp")

    def __init__(self):
        self.timestamp = time.time()

class UserDeletions:
    __slots__ = ("deletions")

    def __init__(self):
        self.deletions = []
    
    @property
    def amount(self):
        return len(self.deletions)

class reminders(commands.Cog):
    '''Reminders to do stuff. (and todo lists!)'''
    __slots__ = ("bot", "logger", "todo_lists", "reminders", "deletions")

    def __init__(self, bot, load=False):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.todo_lists = {}
        self.reminders = {}
        self.deletions = {}
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
            reminders = await self.bot.db.exec("select * from reminders order by user_id desc", ())
            for item in reminders:
                new_reminders[item['user_id']] = [i for i in reminders if i['user_id'] == item['user_id']]
                #only start handling reminders if the extension was loaded, we don't want reminders to fire twice once this function is
                #called by handle_reminder
                if load:
                    asyncio.create_task(self.handle_reminder(item['user_id'], item['channel_id'], item['reminder_time'], item['now'], item['reminder_text'], item['uuid']))
                    self.logger.info(f"Started handling a reminder for user {item['user_id']}")
            self.reminders = new_reminders
        except:
            self.logger.info("Couldn't update reminder cache! Is there anything in the database?")
            self.logger.debug(traceback.format_exc())
        self.logger.info("Updated reminder cache!")
        
    async def update_todo_cache(self):
        await self.bot.wait_until_ready()
        self.logger.info("Updating todo cache...")
        new_todo_entries = {}
        try:
            todolists = await self.bot.db.exec("select * from todo order by timestamp desc", ())
            if not isinstance(todolists, list):
                todolists = [todolists]
            for item in todolists:
                new_todo_entries[item['user_id']] = [i for i in todolists if i['user_id'] == item['user_id']]
        except:
            self.logger.info("Couldn't update todo cache! Is anything in the database?")
            traceback.print_exc()
        self.todo_lists = new_todo_entries
        self.logger.info("Updated todo cache!")
    
    async def handle_reminder(self, user_id, channel_id, remindertime, reminderstarted, remindertext, uuid):
        #waait for as long as needed
        self.logger.info("handling reminder...")
        #make timestamp human readable before sleeping (otherwise it just shows up as 0 seconds)
        hrtimedelta = humanize.precisedelta(remindertime-reminderstarted, format='%0.0f')
        await discord.utils.sleep_until(remindertime)
        #then send the reminder, with the time in a more human readable form than a bunch of seconds. (i.e '4 hours ago' instead of '14400 seconds ago')
        await self.bot.get_channel(channel_id).send(self.bot.strings["REMINDER"].format(user_id, hrtimedelta, remindertext))
        #and delete it from the database
        await self.bot.db.exec(f"delete from reminders where uuid=%s", (uuid))
        await self.update_reminder_cache()

    @commands.command(aliases=['reminders', 'reminder'], help="Set a reminder for sometime in the future. This reminder will persist even if the bot is restarted.", localized_help={'en':'Set a reminder.'})
    async def remind(self, ctx, time:TimeConverter, *, reminder):
        await ctx.send(self.bot.strings["SETTING_REMINDER"])
        #get the date the reminder will fire at
        currenttime = datetime.datetime.now()
        remindertime = currenttime+datetime.timedelta(0, round(time))
        #generate uuid
        uuid = str(uuid_generator.uuid4())
        #add the reminder to the database
        await self.bot.db.exec(f"insert into reminders(user_id, channel_id, reminder_time, now, reminder_text, uuid) values(%s, %s, %s, %s, %s, %s)", (ctx.author.id, ctx.channel.id, remindertime, datetime.datetime.now(), reminder, uuid))
        await self.update_reminder_cache()
        await ctx.send(self.bot.strings["REMINDER_SET"].format(humanize.precisedelta(remindertime-currenttime, format='%0.0f'), reminder))
        await self.handle_reminder(ctx.author.id, ctx.channel.id, remindertime, currenttime, reminder, uuid)

    async def show_list(self, ctx):
        entrystring = ""
        try:
            if not self.todo_lists[ctx.author.id]:
                return await ctx.send(self.bot.strings["LIST_EMPTY"])
            for count, value in enumerate(self.todo_lists[ctx.author.id]):
                entrystring += self.bot.strings["ENTRY"].format(count+1, value['entry'], humanize.precisedelta(value['timestamp'], format='%0.0f'))
                if len(entrystring) > 3800:
                    await ctx.send(self.bot.strings["LIST_TOO_LONG"].format(count+1))
                    break
            if entrystring:
                embed = discord.Embed(title=self.bot.strings["LIST_HEADER"].format(ctx.author), description=entrystring, color=self.bot.config['theme_color'])
                return await ctx.send(embed=embed)
        except KeyError:
            return await ctx.send(self.bot.strings["LIST_EMPTY"])
        except discord.HTTPException:
            return await ctx.send(self.bot.strings["ENTRY_TOO_LONG_LIST"].format(count))
            #paginator when
        except:
            await self.bot.core.send_traceback()
            await ctx.send(self.bot.strings["ERROR_LIST_FAILED"])
            await self.bot.core.send_debug(ctx)

    def get_entrycount_string(self, entrycount):
        base = self.bot.strings["ENTRY_COUNT"]
        if entrycount == 1:
            return base.format(entrycount, self.bot.strings["ENTRY_SINGLE"])
        if entrycount == 0:
            return self.bot.strings["LIST_NOW_EMPTY"]
        return base.format(entrycount, self.bot.strings["ENTRY_PLURAL"])

    async def process_deletion(self, ctx, entry):
        await self.bot.db.exec("delete from todo where entry=%s and user_id=%s", (self.todo_lists[ctx.author.id][int(entry)-1]['entry'], ctx.author.id))
        del self.todo_lists[ctx.author.id][int(entry)-1]
        self.deletions[ctx.author.id].deletions.append(Deletion())
        entrycount = len(self.todo_lists[ctx.author.id])
        await ctx.send(embed=discord.Embed(title=self.bot.strings["ENTRY_DELETED"]+self.get_entrycount_string(entrycount), color=self.bot.config['theme_color']))

    async def rapid_deletion_confirmation_callback(self, message, ctx, confirmed, entry):
        if confirmed:
            await self.process_deletion(ctx, entry)
            #reset deletion info
            self.deletions[ctx.author.id] = UserDeletions()
        
    async def prune_deletions(self, ctx):
        now = time.time()
        for deletion in self.deletions[ctx.author.id].deletions:
            if now - deletion.timestamp >= 60:
                del deletion
            else:
                break

    async def check_deletions(self, ctx, entry, count):
        await self.prune_deletions(ctx)
        if self.deletions[ctx.author.id].amount < 2:
            return False
        embed = discord.Embed(title=self.bot.strings["RAPID_DELETION_CONFIRMATION_TITLE"], description=self.bot.strings["RAPID_DELETION_CONFIRMATION_DESCRIPTION"], color=self.bot.config['theme_color'])
        embed.add_field(name=self.bot.strings["ENTRY_SHOW_TITLE"].format(count), value=entry)
        embed.set_footer(text=self.bot.strings["RAPID_DELETION_CONFIRMATION_FOOTER"])
        followups = [self.bot.strings["ENTRY_DELETION_CONFIRMED"], self.bot.strings["ENTRY_DELETION_DENIED"]]
        self.bot.confirmation(self.bot, followups, embed, ctx, self.rapid_deletion_confirmation_callback, count)
        return True

    @commands.group(invoke_without_command=True, aliases=["to-do", "todos"], help=f"A list of stuff to do.")
    async def todo(self, ctx):
        await self.show_list(ctx)

    @todo.command(help="Adds an item to your todo list.")
    async def add(self, ctx, *, entry=None):
        try:
            if not entry:
                return await ctx.send(self.bot.strings["ENTRY_NOT_SPECIFIED_ADD"].format(await self.bot.get_prefix(ctx.message)))
            elif entry in [i['entry'] for i in [j for j in list(self.todo_lists.values())][0] if i['user_id'] == ctx.author.id]:
                return await ctx.send(self.bot.strings["ENTRY_ALREADY_EXISTS"])
        except IndexError:
            pass
        timestamp = datetime.datetime.now()
        try:
            await self.bot.db.exec("insert into todo values(%s, %s, %s)", (ctx.author.id, entry, timestamp))
            try:
                self.todo_lists[ctx.author.id]
            except KeyError:
                self.todo_lists[ctx.author.id] = []
            self.todo_lists[ctx.author.id].insert(0, {"user_id":ctx.author.id, "entry":entry, "timestamp":timestamp})
            entrycount = len(self.todo_lists[ctx.author.id])
            await ctx.send(embed=discord.Embed(title=self.bot.strings["ENTRY_ADDED"]+self.get_entrycount_string(entrycount), color=self.bot.config['theme_color']))
        except:
            #dm traceback
            await self.bot.core.send_traceback()
            await ctx.send(self.bot.strings["ERROR_ENTRY_ADD_FAILED"])
            await self.bot.core.send_debug(ctx)

    @todo.command(help="Deletes an item from your todo list.", aliases=['remove'])
    async def delete(self, ctx, entry = None):
        try:
            try:
                self.deletions[ctx.author.id]
            except:
                self.deletions[ctx.author.id] = UserDeletions()
            if not entry:
                return await ctx.send(self.bot.strings["ENTRY_NOT_SPECIFIED_DELETE"])
            try:
                int(entry)
            except (TypeError, ValueError):
                return await ctx.send(self.bot.strings["ENTRY_NAN_DELETE"])
            if await self.check_deletions(ctx, self.todo_lists[ctx.author.id][int(entry)-1]['entry'], entry):
                return
            await self.process_deletion(ctx, entry)
        except IndexError:
            return await ctx.send(self.bot.strings["ENTRY_NOT_FOUND"])
        except KeyError:
            await ctx.send(self.bot.strings["LIST_EMPTY"])
        except:
            await self.bot.core.send_traceback()
            await ctx.send(self.bot.strings["ERROR_ENTRY_DELETE_FAILED"])
            await self.bot.core.send_debug(ctx)
        return

    @todo.command(help="Clears your entire todo list.")
    async def clear(self, ctx):
        if not self.bot.common.get_value(self.todo_lists, ctx.author.id, None):
            return await ctx.send(self.bot.strings["LIST_EMPTY"])
        try:
            return await self.bot.deletion_request(self.bot).create_request("todo", ctx)
        except self.bot.DeletionRequestAlreadyActive:
            return await ctx.send(self.bot.strings["DELETION_ACTIVE"])
    
    @todo.command(help="Shows your todo list.")
    async def list(self, ctx):
        await self.show_list(ctx)

    @todo.command(help="Shows a specific entry from your list.")
    async def show(self, ctx, entry=None):
        if not entry:
            return await ctx.send(self.bot.strings["ENTRY_NOT_SPECIFIED_SHOW"])
        try:
            entry = int(entry)
        except (TypeError, ValueError):
            return await ctx.send(self.bot.strings["ENTRY_NAN_SHOW"])
        try:
            if entry < 1:
                #wrap around to 2 more than max length
                entry = len(self.todo_lists[ctx.author.id])+2
            await ctx.send(embed=discord.Embed(title=self.bot.strings["ENTRY_SHOW_TITLE"].format(entry), description=self.bot.strings["ENTRY_SHOW_DESC"].format(humanize.precisedelta(self.todo_lists[ctx.author.id][entry-1]['timestamp'], format='%0.0f'), self.todo_lists[ctx.author.id][entry-1]['entry']), color=self.bot.config['theme_color']))
        except discord.HTTPException:
            return await ctx.send(self.bot.strings["ENTRY_TOO_LONG_SHOW"])
        except IndexError:
            return await ctx.send(self.bot.strings["ENTRY_NOT_FOUND_SHOW"].format(len(self.todo_lists[ctx.author.id])))
        except KeyError:
            return await ctx.send(self.bot.strings["LIST_EMPTY"])
        except:
            await self.bot.core.send_traceback()
            await ctx.send(self.bot.strings["ERROR_SHOW_FAILED"])
            await self.bot.core.send_debug(ctx)

async def setup(bot):
    await bot.add_cog(reminders(bot, True))

async def teardown(bot):
    await bot.remove_cog(reminders(bot))
