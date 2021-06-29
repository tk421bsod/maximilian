import datetime
import humanize
import re
from discord.ext import commands
import discord
import asyncio
import random
import logging
import sys
import os 
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 
import core
import errors

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
    def __init__(self, bot, teardown=False):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.bot.todo_entries = {}
        self.bot.reminders = {}
        #don't update cache on teardown (manual unload or automatic unload on shutdown)
        if not teardown:
            self.bot.loop.create_task(self.update_todo_cache())
            self.bot.loop.create_task(self.update_reminder_cache(True))

    async def update_reminder_cache(self, load=False):
        await self.bot.coreinst.check_if_ready()
        self.logger.info("Updating reminder cache...")
        self.bot.newreminders = {}
        try:
            for item in (reminders := self.bot.dbinst.exec_query(self.bot.database, "select * from reminders order by user_id desc", False, True)):
                self.bot.newreminders[item['user_id']] = [i for i in reminders if i['user_id'] == item['user_id']]
                #only start handling reminders if the extension was loaded, we don't want reminders to fire twice once this function is
                #called by handle_reminder
                if load:
                    self.bot.loop.create_task(self.handle_reminder(item['user_id'], item['channel_id'], item['reminder_time'], item['now'], item['reminder_text']))
                    self.logger.info(f"Started handling a reminder for user {item['user_id']}")
            self.bot.reminders = self.bot.newreminders
        except:
            self.bot.reminders = {}
            self.logger.info("Couldn't update reminder cache! Is there anything in the database?")
        self.logger.info("Updated reminder cache!")
        
    async def update_todo_cache(self):
        await self.bot.coreinst.check_if_ready()
        self.logger.info("Updating todo cache...")
        try:
            for item in (todolists := self.bot.dbinst.exec_query(self.bot.database, "select * from todo order by timestamp desc", False, True)):
                self.bot.todo_entries[item['user_id']] = [i for i in todolists if i['user_id'] == item['user_id']]
        except:
            self.logger.info("Couldn't update todo cache! Is anything in the database?")
        self.logger.info("Updated todo cache!")
    
    async def handle_reminder(self, user_id, channel_id, remindertime, reminderstarted, remindertext):
        #wait for as long as needed
        self.logger.info("handling reminder...")
        #make timestamp human readable before sleeping (otherwise it just shows up as 0 seconds)
        hrtimedelta = humanize.precisedelta(remindertime-reminderstarted, format='%0.0f')
        await discord.utils.sleep_until(remindertime)
        #then send the reminder, with the time in a more human readable form than a bunch of seconds. (i.e '4 hours ago' instead of '14400 seconds ago')
        await self.bot.get_channel(channel_id).send(f"<@{user_id}> {hrtimedelta} ago: '{remindertext}'")
        #and delete it from the database
        self.bot.dbinst.exec_safe_query(self.bot.database, f"delete from reminders where user_id=%s and channel_id=%s and reminder_time=%s and now=%s and reminder_text=%s", (user_id, channel_id, remindertime, reminderstarted, remindertext))
        await self.update_reminder_cache()


    @commands.command(hidden=True, aliases=['reminders', 'reminder'], help="Set a reminder for sometime in the future. This reminder will persist even if the bot is restarted.")
    async def remind(self, ctx, action, time:TimeConverter, *, reminder):
        if action == "add":
            await ctx.send("Setting your reminder...")
            #get the date the reminder will fire at
            currenttime = datetime.datetime.now()
            remindertime = currenttime+datetime.timedelta(0, round(time))
            #add the reminder to the database
            self.bot.dbinst.exec_safe_query(self.bot.database, f"insert into reminders(user_id, channel_id, reminder_time, now, reminder_text) values(%s, %s, %s, %s, %s)", (ctx.author.id, ctx.channel.id, remindertime, datetime.datetime.now(), reminder))
            await ctx.send(f"Ok, in {humanize.precisedelta(remindertime-currenttime, format='%0.0f')}: '{reminder}'")
            await self.handle_reminder(ctx.author.id, ctx.channel.id, remindertime, currenttime, reminder)
                
    
    @commands.command(aliases=["to-do", "todos"], help=f"A list of stuff to do. You can view your todo list by using `<prefix>todo` and add stuff to it using `<prefix>todo add <thing>`. You can delete stuff from the list using `<prefix>todo delete <thing>`.")
    async def todo(self, ctx, action="list", *, entry=None):
        if action == "add":
            if not entry:
                return await ctx.send(f"You didn't say what you wanted to add to your todo list. Run this command again with what you wanted to add. For example, you can add 'foo' to your todo list by using `{await self.bot.get_prefix(ctx.message)}todo add foo`.")
            elif entry in [i['entry'] for i in [j for j in list(self.bot.todo_entries.values())][0] if i['user_id'] == ctx.author.id]:
                return await ctx.send("That todo entry already exists.")
            result = self.bot.dbinst.insert(self.bot.database, "todo", {"user_id":ctx.author.id, "entry":entry, "timestamp":datetime.datetime.now()}, None)
            if result == "success":
                await self.update_todo_cache()
                entrycount = self.bot.dbinst.exec_query(self.bot.database, f'select count(entry) from todo where user_id={ctx.author.id}')['count(entry)']
                await ctx.send(embed=discord.Embed(title=f"\U00002705 Todo entry added successfully. \nYou now have {entrycount} todo entries.", color=discord.Color.blurple()))
            elif result == "error-duplicate":
                await ctx.send("That todo entry already exists.")
            else:
                #dm traceback
                owner = self.bot.get_user(self.bot.owner_id)
                owner.send(f"Error while adding to the todo list: {result}")
                await ctx.send("There was an error while adding that todo entry. I've made my developer aware of this.")
            return
        if action == "delete":
            try:
                self.bot.todo_entries[ctx.author.id][int(entry)-1]['entry']
                if self.bot.dbinst.delete(self.bot.database, "todo", self.bot.todo_entries[ctx.author.id][int(entry)-1]['entry'], "entry", "user_id", ctx.author.id, True) == "successful" and entry:
                    entrycount = self.bot.dbinst.exec_query(self.bot.database, f'select count(entry) from todo where user_id={ctx.author.id}')['count(entry)']
                    await self.update_todo_cache()
                    await ctx.send(embed=discord.Embed(title=f"\U00002705 Todo entry `{entry}` deleted successfully. \nYou now have {entrycount} todo entries.", color=discord.Color.blurple()))
            except:
                await ctx.send("Something went wrong while deleting that todo entry. Make sure that the todo entry you're trying to delete actually exists.")
            return
        if action == "deleteall":
            try:
                return await core.deletion_request(self.bot).create_request("todo", ctx)
            except errors.DeletionRequestAlreadyActive:
                return await ctx.send("A deletion request is already active.")
        if action == "list" or entry == None:
            entrystring = ""
            try:
                for count, value in enumerate(self.bot.todo_entries[ctx.author.id]):
                    entrystring += f"{count+1}. `{value['entry']}`\nCreated {humanize.precisedelta(value['timestamp'], format='%0.0f')} ago.\n\n"
                if entrystring:
                    embed = discord.Embed(title=f"{ctx.author}'s todo list", description=entrystring, color=discord.Color.blurple())
                    return await ctx.send(embed=embed)
            except KeyError:
                return await ctx.send("It doesn't look like you have anything in your todo list. Try adding something to it.")
            except discord.HTTPException:
                return await ctx.send("Your todo list is too long to show in a single message.")
                #maybe work on a paginator???

def setup(bot):
    bot.add_cog(reminders(bot))

def teardown(bot):
    bot.remove_cog(reminders(bot, True))
    
