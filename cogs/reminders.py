import datetime
from dateparser.search import search_dates
import humanize
from discord.ext import commands
import discord
import asyncio
import random
import logging

class reminders(commands.Cog):
    '''Reminders to do stuff.'''
    def __init__(self, bot, teardown=False):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.bot.todo_entries = {}
        #don't update cache on teardown (manual unload or automatic unload on shutdown)
        if not teardown:
            self.bot.loop.create_task(self.update_todo_cache())

    async def update_todo_cache(self):
        await self.bot.prefixesinst.check_if_ready()
        self.logger.info("Updating todo cache...")
        try:
            for item in (todolists := self.bot.dbinst.exec_query(self.bot.database, "select * from todo order by timestamp desc", False, True)):
                self.bot.todo_entries[item['user_id']] = [i for i in todolists if i['user_id'] == item['user_id']]
        except:
            self.logger.info("Couldn't update todo cache. Is anything in the database?")
        self.logger.info("Updated todo cache!")
    
    async def handle_reminder(self, ctx, remindertimeseconds, remindertext):
        #wait for as long as needed
        await asyncio.sleep(remindertimeseconds)
        #then send the reminder, with the time in a more human readable form than a bunch of seconds. (i.e '4 hours ago' instead of '14400 seconds ago')
        await ctx.send(f"{ctx.author.mention} {humanize.precisedelta(remindertimeseconds)} ago: '{remindertext}'")

    @commands.command(hidden=True)
    async def remind(self, ctx, action, *, reminder):
        if action == "add":
            await ctx.send("Setting your reminder...")
            parsablereminder = reminder.strip(",")
            #search for dates in the string provided, if found get a datetime object that represents that date
            #TODO: improve date parsing using regex as dateparser is very picky about what dates it accepts (it accepts "in 5 minutes" but not "5m" or "5 minutes from now", for example)
            remindertimelist = search_dates(parsablereminder)
            if remindertimelist == None:
                await ctx.send("You need to specify a time that you want to be reminded at.")
                return
            elif len(remindertimelist) > 1:
                await ctx.send("You can't include more than 1 time in your reminder.")
                return
            elif remindertimelist[0][1] < datetime.datetime.now():
                await ctx.send("You can't specify a date in the past.")
            #get the object
            remindertime = remindertimelist[0][1]
            #get the current time
            currenttime = datetime.datetime.now()
            #take the date out of the string
            remindertext = reminder.replace(remindertimelist[0][0], "")
            #then subtract the current time from the date provided, and get the total number of seconds for that difference
            remindertimeseconds = (remindertime - currenttime).total_seconds()
            #self.bot.dbinst.exec_query(self.bot.database, f"insert into reminders(user_id, reminder_time) values ({ctx.author.id}, '{remindertimeseconds}', False, None)
            await ctx.send("Your reminder has been added!")
            #we need to round remindertimeseconds as humanize hates decimals (not rounding this sometimes causes the precisedeltas to be one off, like 14 minutes instead of 15 minutes)
            await self.handle_reminder(ctx, round(remindertimeseconds), remindertext)
                
    
    @commands.command(aliases=["to-do", "TODO"], help=f"A list of stuff to do. You can view your todo list by using `<prefix>todo` and add stuff to it using `<prefix>todo add <thing>`. You can delete stuff from the list using `<prefix>todo delete <thing>`. I'm working on making deletion easier to use.")
    async def todo(self, ctx, action="list", *, entry=None):
        if action == "add":
            if not entry:
                return await ctx.send(f"You didn't say what you wanted to add to your todo list. Run this command again with what you wanted to add. For example, you can add 'foo' to your todo list by using `{await self.bot.get_prefix(ctx.message)}todo add foo`.")
            elif entry in [i['entry'] for i in [j for j in list(self.bot.todo_entries.values())][0] if i['user_id'] == ctx.author.id]:
                return await ctx.send("That entry already exists.")
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
            if not self.bot.waiting_for_reaction:
                embed = discord.Embed(title="Delete your todo list?", description=f"You've requested that I delete your todo list, and I need you to confirm that you actually want to do this.", color=discord.Color.blurple())
                embed.add_field(name="Effects", value="If you proceed, your todo list will be deleted. **THIS CANNOT BE UNDONE.**")
                embed.add_field(name="Your options", value="React with \U00002705 to proceed, or react with \U0000274c to cancel.", inline=False)
                deletionmessage = await ctx.send(embed=embed)
                await deletionmessage.add_reaction("\U00002705")
                await deletionmessage.add_reaction("\U0000274c")
                try:
                    await asyncio.sleep(1)
                    while True:
                        self.bot.waiting_for_reaction = True
                        #maybe I should create a check?
                        reaction = await self.bot.wait_for('reaction_add', timeout=120.0)
                        async for each in reaction[0].users():
                            if ctx.message.author == each:
                                self.bot.waiting_for_reaction = False
                                if str(reaction[0].emoji) == '\U00002705':
                                    self.bot.dbinst.delete(self.bot.database, "todo", str(ctx.author.id), "user_id", "", "", False)
                                    embed = discord.Embed(title="\U00002705 Cleared your todo list!", color=discord.Color.blurple())
                                    await self.update_todo_cache()
                                    await ctx.send(embed=embed)
                                    return
                                if str(reaction[0].emoji) == '\U0000274c':
                                    await ctx.send("Ok. I won't clear your todo list.")
                                    return
                except asyncio.TimeoutError:
                    self.bot.waiting_for_reaction = False
                    await ctx.send("Deletion request timed out. I won't clear your todo list.")
                    return
            else:
                await ctx.send("It looks like you already have an active deletion request.")
                return
        if action == "list" or entry == None:
            entrystring = ""
            try:
                for count, value in enumerate(self.bot.todo_entries[ctx.author.id]):
                    entrystring += f"{count+1}. `{value['entry']}`\nCreated {humanize.precisedelta(value['timestamp'], format='%0.0f')} ago.\n"
                if entrystring:
                    embed = discord.Embed(title=f"{ctx.author}'s todo list", description=entrystring, color=discord.Color.blurple())
                    return await ctx.send(embed=embed)
            except KeyError:
                return await ctx.send("It doesn't look like you have anything in your todo list. Try adding something to it.")

def setup(bot):
    bot.add_cog(reminders(bot))

def teardown(bot):
    bot.remove_cog(reminders(bot, True))
    
