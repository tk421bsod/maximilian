import datetime
from dateparser.search import search_dates
import humanize
from aioconsole import ainput

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
                await ctx.send(f"{ctx.author.mention} {humanize.naturaldelta(remindertimeseconds)} ago: '{remindertext}'")
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
            remindertimelist = search_dates(parsablereminder)
            if len(remindertimelist) > 1:
                await ctx.send("You can't include more than 1 time in your reminder.")
                return
            elif remindertimelist == None:
                await ctx.send("You need to specify a time that you want to be reminded at.")
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
            await self.handle_reminder(ctx, remindertimeseconds, remindertext)

def setup(bot):
    bot.add_cog(reminders(bot))

def teardown(bot):
    bot.remove_cog(reminders(bot))
    