#core.py: deletion/confirmation handlers, event listeners, helpers, owner-only commands

import asyncio
import datetime
import inspect
import logging
import os
import time
import traceback
import typing

import discord
from discord.ext import commands

import helpcommand

try:
    import git
except (ImportError, ModuleNotFoundError):
    pass #we'll deal with it in a bit

def get_prefix(bot, message):
    if not bot.prefixes:
        try:
            bot.loop.create_task(bot.prefixinst.update_prefix_cache())
        #fall back if something goes wrong
        except:
            bot.logger.error("Something went wrong while updating the prefix cache. Falling back to '!'.")
            bot.logger.error(traceback.format_exc())
            return "!"
    if not message.guild:
        return "!"
    try:
        return bot.prefixes[message.guild.id]
    except KeyError:
        bot.prefixes[message.guild.id] = "!"
        return "!"

class DeletionRequestAlreadyActive(BaseException):
    pass

class confirmation:
    def __init__(self, bot, message, ctx, callback, *additional_callback_args):
        '''A class that handles a bit of confirmation logic for you. You\'ll need to provide a callback coroutine that takes: (reaction:discord.RawReactionActionEvent, message:discord.Message, ctx:discord.ext.commands.Context, confirmed:bool) and whatever other arguments you pass to additional_callback_args.'''
        self.bot = bot
        self.GREEN_CHECK = '\U00002705'
        self.RED_X = '<:red_x:813135049083191307>'
        if not inspect.iscoroutinefunction(callback):
            raise TypeError("callback must be a coroutine!!!")
        #call handle_confirmation to prevent weird syntax like
        #await confirmation()._handle_confirmation()
        bot.loop.create_task(self._handle_confirmation(message, ctx, callback, *additional_callback_args))

    async def _check_confirmed(self, ctx, message, reaction):
        '''Check if the user confirmed the action by reacting with GREEN_CHECK. '''
        emoji = str(reaction[0].emoji)
        async for each in reaction[0].users():
            #make sure we're only looking at a: the confirmation message and b: the reaction added by the command's invoker
            if ctx.message.author == each and reaction[0].message.id == message.id:
                if emoji == self.GREEN_CHECK:
                    return True
                elif emoji == self.RED_X:
                    return False
        #wait for another reaction (without running the callback) if the user that reacted wasn't the command's invoker
        return None

    async def _handle_confirmation(self, message, ctx, callback, *additional_callback_args):
        '''Handles a confirmation, transferring control to a callback if _check_confirmed returns a non-None value'''
        await message.add_reaction(self.GREEN_CHECK)
        await message.add_reaction(self.RED_X)
        while True:
            reaction = await self.bot.wait_for('reaction_add', timeout=60.0)
            confirmed = await self._check_confirmed(ctx, message, reaction)
            if confirmed != None:
                ret = await callback(reaction, message, ctx, confirmed, *additional_callback_args)
                if ret:
                    break

class deletion_request:
    def __init__(self, bot):
        '''A class that handles some deletion request logic. Has some similar attributes to `confirmation` but doesn't subclass as `confirmation`'s __init__ calls _handle_confirmation (subclassing may cause naming conflicts too)'''
        #mainembeds and clearedembeds are mappings of type to embed (see https://discord.com/developers/docs/resources/channel#embed-object for information on the format of these embeds)
        self.mainembeds = {"todo":{'fields': [{'inline': True, 'name': 'Effects', 'value': 'If you proceed, your todo list will be deleted. **THIS CANNOT BE UNDONE.**'}, {'inline': False, 'name': 'Your options', 'value': 'React with ✅ to proceed, or react with <:red_x:813135049083191307> to cancel.'}], 'color': 7506394, 'type': 'rich', 'description': "You've requested that I delete your todo list, and I need you to confirm that you actually want to do this.", 'title': 'Delete your todo list?'}, "all":{'fields': [{'inline': True, 'name': 'Effects', 'value': 'If you proceed, all reaction roles and custom commands you\'ve set up will be deleted, and my prefix will be reset to `!`. **THIS CANNOT BE UNDONE.**'}, {'inline': False, 'name': 'Your options', 'value': 'React with ✅ to proceed, or react with <:red_x:813135049083191307> to cancel.'}], 'color': 7506394, 'type': 'rich', 'description': "You've requested that I delete all the information I have stored about this server (use the `privacy` command to view details on the data I collect). I need you to confirm that you actually want to do this.", 'title': 'Delete all data?'}}
        self.clearedembeds = {"todo":{'color': 7506394, 'type': 'rich', 'title': '\U00002705 Cleared your todo list!'}, "all":{'color': 7506394, 'type': 'rich', 'title': '\U00002705 All data for this server has been cleared!'}}
        self.bot = bot

    async def confirmation_callback(self, reaction, message, ctx, confirmed, requesttype, id):
        try:
            if confirmed:
                if requesttype == "todo":
                    self.bot.dbinst.exec_safe_query("delete from todo where user_id = %s", (ctx.author.id,))
                    await self.bot.get_cog('reminders').update_todo_cache()
                elif requesttype == "all":
                    await self.delete_all(ctx)
                self.bot.dbinst.exec_safe_query("delete from active_requests where id = %s", (id,))
                await ctx.send(embed=discord.Embed.from_dict(self.clearedembeds[requesttype]))
                return True
            if not confirmed:
                await ctx.send("Ok. I won't delete anything.")
                self.bot.dbinst.exec_safe_query("delete from active_requests where id = %s", (id,))
                return True
        except Exception as e:
            #clean up
            self.bot.dbinst.exec_safe_query("delete from active_requests where id = %s", (id,))
            #then re-raise the error
            #this **will** cancel the confirmation
            raise e
        return False

    async def _handle_request(self, id, requesttype, ctx):
        deletionmessage = await ctx.send(embed=discord.Embed.from_dict(self.mainembeds[requesttype]))
        try:
            confirmation(self.bot, deletionmessage, ctx, self.confirmation_callback, requesttype, id)
        except asyncio.TimeoutError:
            self.bot.dbinst.exec_safe_query("delete from active_requests where id = %s", (id,))
            await ctx.send("Deletion request timed out. I won't delete anything.")
            return

    async def create_request(self, requesttype, ctx):
        '''Attempts to create a deletion request, raises errors.DeletionRequestAlreadyActive if one's active'''
        id = ctx.guild.id if requesttype == 'all' else ctx.author.id
        result = self.bot.dbinst.exec_safe_query("select id from active_requests where id=%s", (id,))
        if not result:
            self.bot.dbinst.exec_safe_query("insert into active_requests values(%s)", (id,))
            await self._handle_request(id, requesttype, ctx)
        elif result:
            raise DeletionRequestAlreadyActive()

    async def delete_all(self, ctx):
        self.bot.dbinst.exec_safe_query("delete from roles where guild_id = %s", (ctx.guild.id,))
        self.bot.dbinst.exec_safe_query("delete from responses where guild_id = %s", (ctx.guild.id,))
        self.bot.dbinst.exec_safe_query("delete from prefixes where guild_id = %s", (ctx.guild.id,))
        await ctx.guild.me.edit(nick=f"[!] Maximilian")
        await self.bot.responsesinst.get_responses()
        await self.bot.prefixesinst.update_prefix_cache()

class core(commands.Cog):
    '''Utility commands and a few events. The commands here are only usable by the owner.'''
    def __init__(self, bot, load=False):
        self.bot = bot
        #we can't easily import this file from files in the cogs folder
        #provide references to other classes in the file to prevent this
        #this class is referenced by bot.coreinst after extensions are loaded
        #none of these classes should be used before extensions are loaded anyways as they require the bot to be ready
        self.bot.confirmation = confirmation
        self.bot.deletion_request = deletion_request
        self.bot.DeletionRequestAlreadyActive = DeletionRequestAlreadyActive
        self.bot.core = self
        self.waiting = []
        self.bot.blocklist = []
        self.logger = logging.getLogger(f'maximilian.{__name__}')
        self.bot.ready = False
        if load:
            self.bot.loop.create_task(self.update_blocklist())
            #disable reload command if gitpython isn't installed
            #this is done in a task to make sure it's done after commands have been registered
            self.bot.loop.create_task(self.check_for_git())

    async def check_for_git(self):
        try:
            import git
        except (ImportError, ModuleNotFoundError):
            self.bot.get_command("utils reload").enabled = False
            self.logger.info("Disabled reload command as gitpython isn't installed.")

    @commands.group(invoke_without_command=False, hidden=True)
    async def utils(self, ctx):
        pass

    @commands.is_owner()
    @utils.command(hidden=True)
    async def blocklist(self, ctx):
        await ctx.send("Fetching blocklist...")
        users = "\n".join([str(self.bot.get_user(i)) for i in self.bot.blocklist]) 
        await ctx.send(f"I have {len(self.bot.blocklist)} users blocked. They are: \n{users}")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def reload(self, ctx, *targetextensions):
        await ctx.trigger_typing()
        try:
            if "--nofetch" in targetextensions:
                #couldn't I just use targetextensions.remove for this
                targetextensions = [i for i in targetextensions if i != "--nofetch"]
                nofetch = True
            else:
                nofetch = False
            if len(targetextensions) == 1:
                extensionsreloaded = "Successfully reloaded 1 extension."
            elif len(targetextensions) == 0:
                extensionsreloaded=f"Successfully reloaded all extensions."
                targetextensions = list(self.bot.extensions.keys())
            else:
                extensionsreloaded = f"Successfully reloaded {str(len(targetextensions))} extensions."
            if nofetch:
                await ctx.send("Ok, I won't fetch the latest revision. Reloading extensions...")
            else:
                 reloadmessage = await ctx.send("Fetching latest revision...")
                 try:
                     git.Repo(os.getcwd()).remotes.origin.pull()
                     await reloadmessage.edit(content=f"Reloading extensions...")
                 except:
                     await ctx.send(traceback.print_exc())
                     await ctx.send("\U000026a0 Failed to get latest revision. Reloading local copies of extensions...")
                     extensionsreloaded = f"Reloaded {'1 extension' if len(targetextensions) == 1 else ''}{'all extensions' if len(targetextensions) == 0 else ''}{f'{len(targetextensions)} extensions' if len(targetextensions) > 1 else ''}, but no changes were pulled."
            for each in targetextensions:
                self.bot.reload_extension(each)
            self.bot.prefixesinst = self.bot.get_cog('prefixes')
            self.bot.responsesinst = self.bot.get_cog('Custom Commands')
            self.bot.miscinst = self.bot.get_cog('misc')
            self.bot.reactionrolesinst = self.bot.get_cog('reaction roles')
            embed = discord.Embed(title=f"\U00002705 {extensionsreloaded}", color=discord.Color.blurple())
        except:
            embed = discord.Embed(title=f"\U0000274c Error while reloading extensions.")
            embed.add_field(name="Error:", value=traceback.format_exc())
        await ctx.send(embed=embed) 

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.ready = True
            self.logger.info(f"on_ready was dispatched {time.time()-self.bot.start_time} seconds after init started")
            self.logger.info("finishing startup...")
            self.bot.commandnames = [i.name for i in self.bot.commands if not i.hidden and i.name != "jishaku"]
            self.bot.help_command = helpcommand.HelpCommand(verify_checks=False)
            self.logger.info(f"full startup took {time.time()-self.bot.start_time} seconds")
            return print("Ready")

    async def prepare(self, message):
        if message.author != self.bot.user:
            if message.author.id in self.bot.blocklist:
                return False
            if message.guild is not None:
                for each in range(len(self.bot.responses)):
                    if int(self.bot.responses[each][0]) == int(message.guild.id):
                        if await self.bot.get_prefix(message) + self.bot.responses[each][1].lower() == message.content.lower().strip():
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
        elif type.lower() == "playing":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=newstatus))
        elif type.lower() == "default":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=" v0.6 (stable)"))
        else:
            await ctx.send("oh :blobpaiN; invalid status! ¯\_(ツ)_/¯")
            return
        await ctx.send("Changed status!")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def sql(self, ctx, *, query):
        try:
            result=self.bot.dbinst.exec_safe_query(query, (), fetchall=True)
        except:
            await ctx.message.add_reaction("\U00002757")
            return await ctx.send(f"{traceback.format_exc()}")
        await ctx.message.add_reaction("\U00002705")
        print(result)
        if result:
            try:
                await ctx.send(f"`{result}`")
            except discord.HTTPException:
                paginator = commands.Paginator()
                for line in result:
                    paginator.add_line(str(line))
                [await ctx.send(page) for page in paginator.pages]

    async def update_blocklist(self):
        self.logger.info("Updating blocklist...")
        newblocklist = []
        try:
            newblocklist = [i['user_id'] for i in self.bot.dbinst.exec_safe_query("select * from blocked", fetchall=True)]
            self.bot.blocklist = newblocklist
        except TypeError:
            return self.logger.info("Failed to update blocklist, is there anything in the database?")
        self.logger.info("Updated blocklist!")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def block(self, ctx, member:typing.Union[discord.Member, discord.User]):
        if member.id in self.bot.blocklist:
            return await ctx.send(f"I already have {member} blocked.")
        self.bot.dbinst.exec_safe_query(f"insert into blocked values(%s)", (member.id,))
        await self.update_blocklist()
        await ctx.send(f"Added {member} to the blocklist.")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def unblock(self, ctx, member:typing.Union[discord.Member, discord.User]):
        if member.id not in self.bot.blocklist:
            return await ctx.send(f"{member} isn't blocked.")
        self.bot.dbinst.exec_safe_query(f"delete from blocked where user_id = %s", (member.id,))
        await self.update_blocklist()
        await ctx.send(f"Removed {member} from the blocklist.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.logger.info("joined guild, adding guild id to list of guilds and resetting prefixes")
        await self.bot.prefixinst.update_prefix_cache(guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.logger.info("removed from guild, removing that guild from list of guilds and resetting prefixes")
        await self.bot.prefixinst.update_prefix_cache(guild.id)
    
    async def cog_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send("How did you find these commands? These aren't supposed to be used by anyone but the owner. \nIf you're selfhosting and want to make yourself the owner to prevent this from happening, replace the id after `owner_id=` and before the comma on line 25 of main.py with your user id.")
        else:
            await self.bot.get_user(self.bot.owner_id).send("oh :blobpaiN; here's an error" + traceback.format_exc())


async def setup(bot):
    await bot.add_cog(core(bot, True))

async def teardown(bot):
    await bot.remove_cog(core(bot))
