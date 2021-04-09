import discord
from discord.ext import commands
import git
import helpcommand
import os
import pymysql
import traceback
import logging
import asyncio
import datetime
import time
import humanize

def get_prefix(bot, message):
    if not bot.prefixes:
        bot.prefixinst.update_prefix_cache()
    return bot.prefixes[message.guild.id]

class core(commands.Cog):
    '''Utility commands and a few events. The commands here are only usable by the owner.'''
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(f'maximilian.{__name__}')

    @commands.group(invoke_without_command=False, hidden=True)
    async def utils(self, ctx):
        pass

    @commands.is_owner()
    @utils.command(hidden=True)
    async def reload(self, ctx, *targetextensions):
        await ctx.trigger_typing()
        try:
            if len(targetextensions) == 1:
                extensionsreloaded = "Successfully reloaded 1 extension."
            elif len(targetextensions) == 0:
                extensionsreloaded=f"Successfully reloaded all extensions."
                targetextensions = list(self.bot.extensions.keys())
            else:
                extensionsreloaded = f"Successfully reloaded {str(len(targetextensions))} extensions."
            reloadmessage = await ctx.send("Fetching latest revision...", delete_after=20)
            try:
                repo = git.Repo(os.getcwd())
                o = repo.remotes.origin
                o.pull()
                await reloadmessage.edit(content="Got latest revision. Reloading extensions...")
            except:
                await reloadmessage.edit(content="\U000026a0 Failed to get latest revision. Make sure you've set up the proper SSH keys. Reloading local copies of extensions...")
                extensionsreloaded = f"Reloaded {'1 extension' if len(targetextensions) == 1 else ''}{'all extensions' if len(targetextensions) == 0 else ''}{f'{len(targetextensions)} extensions' if len(targetextensions) > 1 else ''}, but no changes were pulled."
            for each in targetextensions:
                self.bot.reload_extension(each)
            self.bot.prefixesinst = self.bot.get_cog('prefixes')
            self.bot.responsesinst = self.bot.get_cog('Custom Commands')
            self.bot.miscinst = self.bot.get_cog('misc')
            self.bot.reactionrolesinst = self.bot.get_cog('reaction roles')
            await self.bot.prefixesinst.update_prefix_cache()
            await self.bot.responsesinst.get_responses()
            embed = discord.Embed(title=f"\U00002705 {extensionsreloaded}", color=discord.Color.blurple())
        except Exception as e:
            print(e)
            if len(list(str(e))) >= 200:
                embed = discord.Embed(title=f"\U0000274c Error while reloading extensions.")
                embed.add_field(name="Error:", value=str(e))
            else:
                embed = discord.Embed(title=f"\U0000274c Error while reloading extensions: {str(e)}.")
        await ctx.send(embed=embed) 

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f"on_ready was dispatched {time.time()-self.bot.start_time} seconds after init started")
        self.logger.info("finishing startup...")
        self.bot.commandnames = [i.name for i in self.bot.commands if not i.hidden and i.name != "jishaku"]
        try:
            await self.bot.prefixesinst.update_cache()
            await self.bot.responsesinst.get_responses()
        except pymysql.OperationalError:
            traceback.print_exc()
            self.logger.critical("Couldn't fetch prefixes or custom commands from the database.")
            await self.bot.logout()    
        self.bot.help_command = helpcommand.HelpCommand(verify_checks=False)
        self.logger.info(f"ready, full startup took {time.time()-self.bot.start_time} seconds")

    async def prepare(self, message):
        if message.author != self.bot.user:
            if message.guild is not None:
                #required because a bunch of other stuff relies on it, will change it later
                self.bot.commandprefix = self.bot.command_prefix
                for each in range(len(self.bot.responses)):
                    if int(self.bot.responses[each][0]) == int(message.guild.id):
                        if self.bot.prefixes[str(message.guild.id)] + self.bot.responses[each][1].lower() == message.content.lower():
                            await message.channel.send(self.bot.responses[each][2])
                            return False
            return True
        else:
            return False

    @commands.is_owner()
    @utils.command(hidden=True)
    async def change_status(self, ctx, type, newstatus=None):
        await ctx.send("Changing status...")
        if type.lower() == "streaming":
            await self.bot.change_presence(activity=discord.Streaming(name=" my development!", url=newstatus))
        elif type.lower() == "listening":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=newstatus))
        elif type.lower() == "watching":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=newstatus))
        elif type.lower() == "default":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=" v0.5.2 (stable)"))
        else:
            await ctx.send("That's an invalid status type!")
            return
        await ctx.send("Changed status!")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def sql(self, ctx, query):
        try:
            result=self.bot.dbinst.exec_query(self.bot.database, query, False, True)
        except:
            await ctx.message.add_reaction("\U00002757")
            return await ctx.send(traceback.format_exc())
        await ctx.message.add_reaction("\U00002705")
        if result and result != ():
            await ctx.send(f"`{result}`")
   
    @commands.is_owner()
    @utils.command(hidden=True, aliases=["info"])
    async def stats(self, ctx):
        newline="\n"
        embed=discord.Embed(title="bot information stuff").add_field(name="Extensions", value=f"Extensions loaded ({len(list(self.bot.extensions.keys()))} in total): \n{f'{newline}'.join([i for i in list(self.bot.extensions.keys())}")
        embed.add_field(name="Uptime", value=humanize.naturaltime(time.time()-self.bot.start_time))
        embed.add_field(name="misc", value="{len([i for i in self.bot.commands if not i.hidden and i.name != "jishaku"])} commands \n{sum([len(open(i, 'r').splitlines()) for i in os.listdir('.') if i.endswith('.py')])+sum([len(open(i, 'r').splitlines()) for i in os.listdir('./cogs') if i.endswith('.py')])} lines of code \n{len([i for i in os.listdir('.') if i.endswith('.py')])+len([i for i in os.listdir('./cogs') if i.endswith('.py')} Python files"))
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.logger.info("joined guild, adding guild id to list of guilds and resetting prefixes")
        self.bot.guildlist.append(str(guild.id))
        await self.bot.prefixesinst.update_prefix_cache(guild.id)
        #await guild.system_channel.send("Hi! I'm Maximilian, a constantly evolving bot with many useful features, like music, image effects (beta), and reaction roles! \n\U000026a0 This is a version of Maximilian that's under active development (and used for testing by the developer). This allows you to have access to the latest features before they come out on Maximilian Beta or Stable (regular Maximilian), but it comes at a cost of usablity. Uptime might not be consistent, and features may have a lot of bugs or be unfinished. If you want to switch to using the most stable version of Maximilian, use the `about` command, and you'll see an invite link.")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.logger.info("removed from guild, removing that guild from list of guilds and resetting prefixes")
        self.bot.guildlist.remove(str(guild.id))
        await self.bot.prefixesinst.update_prefix_cache(guild.id)
    
    async def cog_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("How did you find these commands? These aren't supposed to be used by anyone but the owner. \nIf you're selfhosting and want to make yourself the owner to prevent this from happening, replace the id after `owner_id=` and before the comma on line 18 of main.py with your user id.")
        pass

def setup(bot):
    bot.add_cog(core(bot))

def teardown(bot):
    bot.remove_cog(core(bot))
