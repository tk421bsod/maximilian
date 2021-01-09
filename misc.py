import discord
from discord.ext import commands
import time
import aiohttp
import io
import asyncio
import datetime
from zalgo_text import zalgo as zalgo_text_gen
from dateparser.search import search_dates
import typing
import humanize
from aioconsole import ainput

class misc(commands.Cog):
    '''Some commands that don\'t really fit into other categories'''
    def __init__(self, bot):
        self.bot = bot
        self.bot.waiting_for_reaction = False

    @commands.command(aliases=["owner"])
    async def hi(self, ctx):
        print("said hi")
        await ctx.send("Hello! I'm a robot. tk421#7244 made me!")

    @commands.command(help="zalgo text")
    async def zalgo(self, ctx, *, arg):
        print("generated zalgo text")
        await ctx.send(zalgo_text_gen.zalgo().zalgofy(str(arg)))

    @commands.command(help="Get an image of a cat.", aliases=["cats"])
    async def thiscatdoesntexist(self, ctx):
        await ctx.trigger_typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://thiscatdoesnotexist.com') as r:
                buffer = io.BytesIO(await r.read())
                print("got a cat image")
                await ctx.send(file=discord.File(buffer, filename="cat.jpeg"))

    @commands.command(aliases=['pong'])
    async def ping(self, ctx):
        print("sent latency")
        await ctx.send(f"Pong! My latency is {str(round(self.bot.latency*1000, 1))} ms.")

    @commands.command(help="Get some info about the bot and commands")
    async def about(self, ctx):
        embed = discord.Embed(title="About", color=discord.Color.blurple())
        embed.add_field(name="Useful links", value=f"Use `{str(self.bot.commandprefix)}help command` for more info on a certain command. \n For more help, join the support server at https://discord.gg/PJ94gft. \n To add Maximilian to your server, with only the required permissions, click [here](https://discord.com/api/oauth2/authorize?client_id=620022782016618528&permissions=335923264&scope=bot). \nIf you want to contribute to my development, visit my Gitlab repository, at https://gitlab.com/tk421bsod/maximilian.", inline=False)
        embed.add_field(name="Fun Commands", value="Commands that have no purpose. \n `zalgo` `cats` `ping`", inline=True)
        embed.add_field(name="Other Commands", value="Commands that actually have a purpose. \n `about` `help` `userinfo` `reactionroles` `commands` `prefix` `listprefixes` `hi` `privacy` `deleteall`", inline=True)
        print("sent some info about me")
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def listguildnames(self, ctx):
        guildstring = ""
        for each in self.bot.guilds:
            guildstring = guildstring + each.name + "(" + str(len(list(each.members))) + " members), "
        await ctx.send("Guilds: " + guildstring[:-2])

    @commands.command(help="View information about what data Maximilian accesses and stores.")
    async def privacy(self, ctx):
        embed = discord.Embed(title="Maximilian Privacy Policy", color=discord.Color.blurple())
        embed.add_field(name="Why Maximilian collects data", value="Maximilian accesses/stores certain information that is necessary for certain functions (types of data collected are described below)", inline=False)
        embed.add_field(name="Data that Maximilian collects", value="**-Server IDs**\nMaximilian stores server IDs when you create a custom command, add a reaction role, or change its prefix to distinguish between different servers.\n\n**-Role IDs**\nMaximilian stores role IDs whenever you add a reaction role so it can assign the correct role to users.\n\n**-User Info**\nTo show information about users, Maximilian accesses, but doesn't store, certain data about users like their roles, permissions, status, and account age.", inline=False)
        embed.add_field(name="I want to delete my server's data, how do I request that?", value=f"You can delete all the data in your server by using{self.bot.commandprefix}deleteall`. This will irreversibly delete all of the reaction roles and custom commands you have set up and reset the prefix to the default of `!`. Only people with the Administrator permission can use this.", inline=False)
        await ctx.send(embed=embed)

    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.command(help="**Permanently** delete all data that Maximilian's stored about your server. (requires the Administrator permission)")
    async def deleteall(self, ctx):
        if not self.bot.waiting_for_reaction:
            embed = discord.Embed(title="Delete all data?", description=f"You've requested that I delete all the information I have stored about this server. (see `{self.bot.commandprefix}privacy` for details on the data I collect)", color=discord.Color.blurple())
            embed.add_field(name="Effects", value="If you proceed, all of the reaction roles and custom commands you've set up will be deleted, and my prefix will be reset to `!`.\n**THIS CANNOT BE UNDONE.**", inline=False)
            embed.add_field(name="Your options", value="React with \U00002705 to proceed, or react with \U0000274c to stop the deletion process.", inline=False)
            deletionmessage = await ctx.send(embed=embed)
            await deletionmessage.add_reaction("\U00002705")
            await deletionmessage.add_reaction("\U0000274c")
            try:
                #this is to prevent the bot's reactions from triggering wait_for
                await asyncio.sleep(1)
                #this while loop is to prevent reactions from other users from ending the deletion request, it's also for preventing multiple deletion requests
                while True:
                    self.bot.waiting_for_reaction = True
                    #maybe I should create a check?
                    reaction = await self.bot.wait_for('reaction_add', timeout=120.0)
                    async for each in reaction[0].users():
                        if ctx.message.author == each:
                            self.bot.waiting_for_reaction = False
                            if str(reaction[0].emoji) == '\U00002705':
                                await ctx.send("Deleting data for this server...")
                                await ctx.trigger_typing()
                                self.bot.dbinst.delete(self.bot.database, "roles", str(ctx.guild.id), "guild_id", "", "", False)
                                self.bot.dbinst.delete(self.bot.database, "responses", str(ctx.guild.id), "guild_id", "", "", False)
                                self.bot.dbinst.delete(self.bot.database, "prefixes", str(ctx.guild.id), "guild_id", "", "", False)
                                await ctx.guild.me.edit(nick=f"[!] Maximilian")
                                await self.bot.responsesinst.get_responses()
                                await self.bot.prefixesinst.reset_prefixes()
                                embed = discord.Embed(title="\U00002705 All data for this server has been cleared!", color=discord.Color.blurple())
                                await ctx.send(embed=embed)
                                return
                            if str(reaction[0].emoji) == '\U0000274c':
                                await ctx.send("Ok. I won't delete anything.")
                                return
            except asyncio.TimeoutError:
                self.bot.waiting_for_reaction = False
                await ctx.send('Deletion request timed out.')
        else:
            await ctx.send("It looks like you already have an active deletion request.")

    @commands.command(hidden=True)
    async def emojiinfo(self, ctx, emoji : typing.Optional[typing.Union[discord.PartialEmoji, str]]=None):
        print(str(emoji))
        if isinstance(emoji, discord.PartialEmoji):
            await ctx.send(f"`<{emoji.name}:{emoji.id}>`")
            return
        await ctx.send(f"`{emoji}`")
    
    async def handle_reminder(self, ctx, remindertimeseconds, remindertext):
        #wait for as long as needed
        while True:
            try:
                await asyncio.sleep(remindertimeseconds)
                print(remindertimeseconds)
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

    @commands.command(hidden=True, aliases=["reminder", "reminders"])
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
            await self.handle_reminder(ctx, round(remindertimeseconds), remindertext)
        


def setup(bot):
    bot.add_cog(misc(bot))

def teardown(bot):
    bot.remove_cog(misc(bot))
