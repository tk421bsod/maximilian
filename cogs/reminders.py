import datetime
from dateparser.search import search_dates
import humanize
from aioconsole import ainput
from discord.ext import commands
import discord
import asyncio

class reminders(commands.Cog):
    '''Reminders to do stuff.'''
    def __init__(self, bot):
        self.bot = bot

    async def handle_reminder(self, ctx, remindertimeseconds, remindertext):
        #wait for as long as needed
        while True:
            try:
                await asyncio.sleep(remindertimeseconds)
                #then send the reminder, with the time in a more human readable form than a bunch of seconds. (i.e '4 hours ago' instead of '14400 seconds ago')
                await ctx.send(f"{ctx.author.mention} {humanize.precisedelta(remindertimeseconds)} ago: '{remindertext}'")
                break
            except KeyboardInterrupt:
                self.bot.logger.warning("One or more reminders is running. Stopping the bot now will cause a loss of data. Do you want to stop it? (Y/N)")
                choice = await ainput()
                if choice.lower.strip() == "y":
                    print("Stopping the bot...")
                    self.bot.logout()
                    break
                elif choice.lower.strip() == "n":
                    print("Continuing...")
                    continue

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
        if entry is None or action == "list":
            entrystring = ""
            for count, value in enumerate(self.bot.dbinst.exec_query(self.bot.database, "select entry from todo where user_id={}".format(ctx.author.id), False, True)):
                entrystring += f"{count+1}. `{value['entry']}`\n"
            if entrystring.strip() != "":
                embed = discord.Embed(title=f"{ctx.author}'s todo list", description=entrystring, color=discord.Color.blurple())
                await ctx.send(embed=embed)
                return
            await ctx.send("It doesn't look like you have anything in your todo list. Try adding something to it.")
            return
        if action == "add":
            if self.bot.dbinst.insert(self.bot.database, "todo", {"user_id":ctx.author.id, "entry":entry}, None, False, None, False, None, False) == "success":
                await ctx.send("Todo entry added successfully.")
        if action == "delete":
            if self.bot.dbinst.delete(self.bot.database, "todo", entry, "entry", "user_id", ctx.author.id, True) == "successful":
                await ctx.send("Todo entry deleted successfully.")

            


def setup(bot):
    bot.add_cog(reminders(bot))

def teardown(bot):
    bot.remove_cog(reminders(bot))
    
