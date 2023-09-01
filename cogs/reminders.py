import asyncio
import datetime
import time
import inspect
import logging
import os
import random
import sys
import traceback
import uuid as uuid_generator #prevent conflict with the local variable 'uuid'

import discord
import humanize
from discord.ext import commands

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
    '''Reminders to do stuff. (and to-do lists!)'''
    __slots__ = ("bot", "logger", "todo_lists", "active_reminders", "deletions")

    def __init__(self, bot, load=False):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.todo_lists = {}
        self.active_reminders = {}
        self.deletions = {}
        #don't update cache on teardown (manual unload or automatic unload on shutdown)
        if load:
            self.bot.settings.add_category("reminders", {"pagination":"Experimental embed pagination features"}, {"pagination":None}, {"pagination":None})
            asyncio.create_task(self.update_todo_cache())
            asyncio.create_task(self.update_reminder_cache(True))

    async def update_reminder_cache(self, load=False):
        await self.bot.wait_until_ready()
        self.logger.info("Updating reminder cache...")
        new_reminders = {}
        active_reminders = {}
        try:
            active_reminders = await self.bot.db.exec("select * from reminders order by user_id desc", ())
            for item in active_reminders:
                new_reminders[item['user_id']] = [i for i in active_reminders if i['user_id'] == item['user_id']]
                #only start handling reminders if the extension was loaded, we don't want reminders to fire twice once this function is
                #called by handle_reminder
                if load:
                    asyncio.create_task(self.handle_reminder(item['user_id'], item['channel_id'], item['reminder_time'], item['now'], item['reminder_text'], item['uuid']))
                    self.logger.info(f"Started handling a reminder for user {item['user_id']}")
            self.active_reminders = new_reminders
        except:
            self.logger.info("Couldn't update reminder cache! Is there anything in the database?")
            self.logger.debug(traceback.format_exc())
        self.logger.info("Updated reminder cache!")
        
    async def update_todo_cache(self):
        await self.bot.wait_until_ready()
        self.logger.info("Updating to-do cache...")
        new_todo_entries = {}
        try:
            todolists = await self.bot.db.exec("select * from todo order by timestamp desc", ())
            if not isinstance(todolists, list):
                todolists = [todolists]
            for item in todolists:
                new_todo_entries[item['user_id']] = [i for i in todolists if i['user_id'] == item['user_id']]
        except:
            self.logger.info("Couldn't update to-do cache! Is anything in the database?")
            traceback.print_exc()
        self.todo_lists = new_todo_entries
        self.logger.info("Updated to-do cache!")
    
    async def handle_reminder(self, user_id, channel_id, remindertime, reminderstarted, remindertext, uuid):
        #waait for as long as needed
        self.logger.info("handling reminder...")
        #make timestamp human readable before sleeping (otherwise it just shows up as 0 seconds)
        try:
            channel = await self.bot.core.getch_channel(channel_id)
            hrtimedelta = humanize.precisedelta(remindertime-reminderstarted, format='%0.0f')
            await discord.utils.sleep_until(remindertime)
            #then send the reminder, with the time in a more human readable form than a bunch of seconds. (i.e '4 hours ago' instead of '14400 seconds ago')
            #TODO: get_channel RELIES ON CACHE SO THIS MAY NOT BE RELIABLE!!!!!!
            #Consider writing a method that falls back to an API call if get_channel fails.
            await channel.send(self.bot.strings["REMINDER"].format(user_id, hrtimedelta, remindertext))
        except OverflowError:
            await channel.send(self.bot.strings["REMINDER_OVERFLOW_ERROR"])
        except:
            pass
        #and delete it from the database
        await self.bot.db.exec(f"delete from reminders where uuid=%s", (uuid))
        await self.update_reminder_cache()

    @commands.command(aliases=['reminder'], extras={'localized_help':{}})
    async def remind(self, ctx, time, *, reminder):
        """Set a reminder for sometime in the future. This reminder will persist even if the bot is restarted."""
        time = await self.bot.common.TimeConverter(self.bot.strings, ("w", "d", "h", "m", "s")).convert(ctx, time)
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

    @commands.command(hidden=True)
    async def reminders(self, ctx):
        #Display a list of reminders.
        try:
            active_reminders = self.active_reminders[ctx.author.id]
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

    async def show_list(self, ctx):
        await self.bot.settings.reminders.wait_ready()
        entrystring = ""
        pagination_enabled = self.bot.settings.reminders.pagination.enabled(ctx.guild.id)
        try:
            if not self.todo_lists[ctx.author.id]:
                return await ctx.send(self.bot.strings["LIST_EMPTY"])
            for count, value in enumerate(self.todo_lists[ctx.author.id]):
                entrystring += self.bot.strings["ENTRY"].format(count+1, value['entry'], humanize.precisedelta(value['timestamp'], format='%0.0f'))
                if len(entrystring) > 3800 and not pagination_enabled:
                    await ctx.send(self.bot.strings["LIST_TOO_LONG"].format(count+1))
                    break
            if entrystring:
                embed = discord.Embed(title=self.bot.strings["LIST_HEADER"].format(ctx.author), description=entrystring, color=self.bot.config['theme_color'])
                if pagination_enabled:
                    return await self.bot.core.send_paginated(embed, ctx, prefix="", suffix="")
                return await ctx.send(embed=embed)
        except KeyError:
            return await ctx.send(self.bot.strings["LIST_EMPTY"])
        except discord.HTTPException:
            return await ctx.send(self.bot.strings["ENTRY_TOO_LONG_LIST"].format(count))
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
        await self.bot.settings.reminders.wait_ready()
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

    @todo.command(help="Adds an item to your to-do list.", localized_help={"owo":"A test string to test localized_help"})
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

    @todo.command(help="Deletes an item from your to-do list.", aliases=['remove'])
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

    @todo.command(help="Clears your entire to-do list.")
    async def clear(self, ctx):
        if not self.bot.common.get_value(self.todo_lists, ctx.author.id, None):
            return await ctx.send(self.bot.strings["LIST_EMPTY"])
        try:
            return await self.bot.deletion_request(self.bot).create_request("todo", ctx)
        except self.bot.DeletionRequestAlreadyActive:
            return await ctx.send(self.bot.strings["DELETION_ACTIVE"])
    
    @todo.command(help="Shows your to-do list.")
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
