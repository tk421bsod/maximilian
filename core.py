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
import errors
import inspect

def get_prefix(bot, message):
    if not bot.prefixes:
        bot.prefixinst.update_prefix_cache()
    if not message.guild:
        return "!"
    try:
        return bot.prefixes[message.guild.id]
    except KeyError:
        bot.prefixes[message.guild.id] = "!"
        return "!"

class deletion_request():
    def __init__(self, bot):
        self.waiting_for_reaction = False
        #mainembeds is a mapping of type to embed (see https://discord.com/developers/docs/resources/channel#embed-object for information on the format of these embeds)
        self.mainembeds = {"todo":{'fields': [{'inline': True, 'name': 'Effects', 'value': 'If you proceed, your todo list will be deleted. **THIS CANNOT BE UNDONE.**'}, {'inline': False, 'name': 'Your options', 'value': 'React with ✅ to proceed, or react with <:red_x:813135049083191307> to cancel.'}], 'color': 7506394, 'type': 'rich', 'description': "You've requested that I delete your todo list, and I need you to confirm that you actually want to do this.", 'title': 'Delete your todo list?'}, "all":{'fields': [{'inline': True, 'name': 'Effects', 'value': 'If you proceed, all reaction roles and custom commands you\'ve set up will be deleted, and my prefix will be reset to `!`. **THIS CANNOT BE UNDONE.**'}, {'inline': False, 'name': 'Your options', 'value': 'React with ✅ to proceed, or react with <:red_x:813135049083191307> to cancel.'}], 'color': 7506394, 'type': 'rich', 'description': "You've requested that I delete all the information I have stored about this server (use the `privacy` command to view details on the data I collect). I need you to confirm that you actually want to do this.", 'title': 'Delete all data?'}}
        self.clearedembeds = {"todo":{'color': 7506394, 'type': 'rich', 'title': '\U00002705 Cleared your todo list!'}, "all":{'color': 7506394, 'type': 'rich', 'title': '\U00002705 All data for this server has been cleared!'}}
        self.bot = bot


    async def _handle_request(self, id, requesttype, ctx):
        deletionmessage = await ctx.send(embed=discord.Embed.from_dict(self.mainembeds[requesttype]))
        await deletionmessage.add_reaction("\U00002705")
        await deletionmessage.add_reaction("<:red_x:813135049083191307>")
        await asyncio.sleep(0.5)
        self.waiting_for_reaction = True
        try:
            while self.waiting_for_reaction:
                reaction = await self.bot.wait_for('reaction_add', timeout=60.0)
                async for each in reaction[0].users():
                    if ctx.message.author == each:
                        self.waiting_for_reaction = False
                        if str(reaction[0].emoji) == '\U00002705':
                            if requesttype == "todo":
                                self.bot.dbinst.delete(self.bot.database, "todo", str(ctx.author.id), "user_id", "", "", False)
                                await self.bot.get_cog('reminders').update_todo_cache()
                            elif requesttype == "all":
                                await self.delete_all(ctx)
                            self.bot.dbinst.exec_safe_query(self.bot.database, "delete from active_requests where id=%s", (id,))
                            await ctx.send(embed=discord.Embed.from_dict(self.clearedembeds[requesttype]))
                            return
                        if str(reaction[0].emoji) == '<:red_x:813135049083191307>':
                            await ctx.send("Ok. I won't delete anything.")
                            return
        except asyncio.TimeoutError:
            self.waiting_for_reaction = False
            self.bot.dbinst.exec_safe_query(self.bot.database, "delete from active_requests where id=%s", (id,))
            await ctx.send("Deletion request timed out. I won't delete anything.")
            return

    async def create_request(self, requesttype, ctx):
        '''Attempts to create a deletion request, raises errors.DeletionRequestAlreadyActive if one's active'''
        id = ctx.guild.id if requesttype == 'all' else ctx.author.id
        if not (result := self.bot.dbinst.exec_safe_query(self.bot.database, "select id from active_requests where id=%s", (id,))):
            self.bot.dbinst.exec_safe_query(self.bot.database, "insert into active_requests values(%s)", (id,))
            await self._handle_request(id, requesttype, ctx)
        elif result:
            print(result)
            raise errors.DeletionRequestAlreadyActive()

    async def delete_all(self, ctx):
        self.bot.dbinst.delete(self.bot.database, "roles", str(ctx.guild.id), "guild_id", "", "", False)
        self.bot.dbinst.delete(self.bot.database, "responses", str(ctx.guild.id), "guild_id", "", "", False)
        self.bot.dbinst.delete(self.bot.database, "prefixes", str(ctx.guild.id), "guild_id", "", "", False)
        await ctx.guild.me.edit(nick=f"[!] Maximilian")
        await self.bot.responsesinst.get_responses()
        await self.bot.prefixesinst.update_prefix_cache()

class core(commands.Cog):
    '''Utility commands and a few events. The commands here are only usable by the owner.'''
    def __init__(self, bot):
        self.bot = bot
        self.waiting = []
        self.logger = logging.getLogger(f'maximilian.{__name__}')

    async def check_if_ready(self):
        if not self.bot.is_ready():
            self.logger.debug(f"Cache isn't ready yet! Waiting to call {inspect.stack()[1][3]} until cache is ready.")
            await self.bot.wait_until_ready()
            self.logger.debug(f"Cache is now ready. Running {inspect.stack()[1][3]}.")
        else:
            self.logger.debug(f"Cache is already ready, running {inspect.stack()[1][3]}")

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
                repo = git.Repo(os.getcwd()).remotes.origin.pull()
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
            embed = discord.Embed(title=f"\U0000274c Error while reloading extensions.")
            embed.add_field(name="Error:", value=traceback.format_exc())
        await ctx.send(embed=embed) 

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f"on_ready was dispatched {time.time()-self.bot.start_time} seconds after init started")
        self.logger.info("finishing startup...")
        self.bot.commandnames = [i.name for i in self.bot.commands if not i.hidden and i.name != "jishaku"]
        self.bot.help_command = helpcommand.HelpCommand(verify_checks=False)
        self.logger.info(f"full startup took {time.time()-self.bot.start_time} seconds")
        print("Ready")

    async def prepare(self, message):
        if message.author != self.bot.user:
            if message.guild is not None:
                #required because a bunch of other stuff relies on it, will change it later
                for each in range(len(self.bot.responses)):
                    if int(self.bot.responses[each][0]) == int(message.guild.id):
                        if await self.bot.get_prefix(message) + self.bot.responses[each][1].lower() == message.content.lower():
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
            await ctx.send("oh :blobpaiN; invalid status! ¯\_(ツ)_/¯")
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
        embed=discord.Embed(title="bot information stuff").add_field(name="Extensions", value=f"Extensions loaded ({len(list(self.bot.extensions.keys()))} in total): \n{f'{newline}'.join([i for i in list(self.bot.extensions.keys())])}")
        embed.add_field(name="Uptime", value=humanize.naturaltime(time.time()-self.bot.start_time))
        embed.add_field(name="misc", value=f"{len([i for i in self.bot.commands if not i.hidden and i.name != 'jishaku'])} commands \n{sum([len(open(i, 'r').readlines()) for i in os.listdir('.') if i.endswith('.py')])+sum([len(open(i, 'r').readlines()) for i in os.listdir('./cogs') if i.endswith('.py')])} lines of code \n{len([i for i in os.listdir('.') if i.endswith('.py')])+len([i for i in os.listdir('./cogs') if i.endswith('.py')])} Python files")
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
        else:
            await self.bot.get_user(self.bot.owner_id).send("oh :blobpaiN; here's an error" + traceback.format_exc())

def setup(bot):
    bot.add_cog(core(bot))

def teardown(bot):
    bot.remove_cog(core(bot))
