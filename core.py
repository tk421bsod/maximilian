#core.py: deletion/confirmation handlers, event listeners, helpers, owner-only commands

#note that this module is loaded during early startup. the 'core' class defined below is loaded in load_extensions_async.

import asyncio
import inspect
import logging
import os
import time
import traceback
import typing
import discord
from discord.ext import commands

import helpcommand
import startup

try:
    import git
except (ImportError, ModuleNotFoundError):
    pass #we'll deal with it in a bit

def get_prefix(bot, message):
    if not bot.prefixes:
        try:
            bot.loop.create_task(bot.prefixes.update_prefix_cache())
        #fall back if something goes wrong
        except:
            bot.logger.error("Something went wrong while updating the prefix cache. Falling back to '!'.")
            bot.logger.error(traceback.format_exc())
            return "!"
    if not message.guild:
        return "!"
    try:
        return bot.prefix[message.guild.id]
    except KeyError:
        bot.prefix[message.guild.id] = "!"
        return "!"

class DeletionRequestAlreadyActive(BaseException):
    pass

class ConfirmationView(discord.ui.View):
    #TODO: Consider somehow passing the raw Interaction to callbacks instead of having to pass followups.
    #Perhaps we could require consumers to pass an interaction_callback coro when constructing a confirmation.
    #From there we could send it the Interaction and View and let it handle everything.

    __slots__ = ("confirmed", "confirm_followup", "cancel_followup")

    def __init__(self, confirm_followup, cancel_followup):
        super().__init__()
        self.confirmed = None
        self.confirm_followup = confirm_followup
        self.cancel_followup = cancel_followup

    @discord.ui.button(label='\U00002705', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.send_message(self.confirm_followup)
        self.stop()

    @discord.ui.button(label='\U0000274e', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        await interaction.response.send_message(self.cancel_followup)
        self.stop()

class confirmation:
    __slots__ = ("bot")

    def __init__(self, bot, followups, to_send, ctx, callback, *additional_callback_args):
        '''Handles a bit of confirmation logic for you. You\'ll need to provide a callback coroutine that takes at least (message:discord.Message, ctx:discord.ext.commands.Context, confirmed:bool). Obviously it should also take anything else you pass to additional_callback_args.'''
        self.bot = bot
        if not inspect.iscoroutinefunction(callback):
            raise TypeError("Confirmation callback must be a coroutine.")
        #call handle_confirmation to prevent weird syntax like
        #await confirmation()._handle_confirmation()
        asyncio.create_task(self._handle_confirmation(followups, to_send, ctx, callback, *additional_callback_args))

    async def _handle_confirmation(self, followups, to_send, ctx, callback, *additional_callback_args):
        '''Handles a confirmation, transferring control to a callback once ConfirmationView exits'''
        view = ConfirmationView(confirm_followup=followups[0], cancel_followup=followups[1])
        if isinstance(to_send, discord.Embed):
            message = await ctx.send(embed=to_send, view=view)
        else:
            message = await ctx.send(to_send, view=view)
        await view.wait()
        return await callback(message, ctx, view.confirmed, *additional_callback_args)


class deletion_request:
    __slots__ = ("bot", "mainembeds", "clearedembeds")

    def __init__(self, bot):
        '''A class that handles some deletion request logic. Has some similar attributes to `confirmation` but doesn't subclass as `confirmation`'s __init__ calls _handle_confirmation (subclassing may cause naming conflicts too)'''
        #mainembeds and clearedembeds are mappings of type to embed (see https://discord.com/developers/docs/resources/channel#embed-object for information on the format of these embeds)
        self.mainembeds = {"todo":{'fields': [{'inline': True, 'name': bot.strings['CLEAR_EFFECTS_TITLE'], 'value': bot.strings["CLEAR_TODO_LIST_EFFECTS_DESC"]}, {'inline': False, 'name': bot.strings['CONFIRMATION_OPTIONS_TITLE'], 'value': bot.strings['CONFIRMATION_OPTIONS']}], 'color': 7506394, 'type': 'rich', 'description': bot.strings["CLEAR_TODO_LIST_DESC"], 'title': bot.strings['CLEAR_TODO_LIST_TITLE']}, "all":{'fields': [{'inline': True, 'name': bot.strings['CLEAR_EFFECTS_TITLE'], 'value': bot.strings['CLEAR_ALL_EFFECTS_DESC']}, {'inline': False, 'name': bot.strings['CONFIRMATION_OPTIONS_TITLE'], 'value': bot.strings['CONFIRMATION_OPTIONS']}], 'color': 7506394, 'type': 'rich', 'description': bot.strings['CLEAR_ALL_DESC'], 'title': bot.strings['CLEAR_ALL_TITLE']}}
        self.clearedembeds = {"todo":{'color': 7506394, 'type': 'rich', 'title': bot.strings['CLEARED_TODO_LIST']}, "all":{'color': 7506394, 'type': 'rich', 'title': bot.strings['CLEARED_ALL']}}
        self.bot = bot

    async def confirmation_callback(self, message, ctx, confirmed, requesttype, id):
        try:
            if confirmed:
                if requesttype == "todo":
                    await self.bot.db.exec("delete from todo where user_id = %s", (ctx.author.id,))
                    await self.bot.get_cog('reminders').update_todo_cache()
                elif requesttype == "all":
                    await self.delete_all(ctx)
                await self.bot.db.exec("delete from active_requests where id = %s", (id,))
                await ctx.send(embed=discord.Embed.from_dict(self.clearedembeds[requesttype]))
                return True
            if not confirmed:
                await self.bot.db.exec("delete from active_requests where id = %s", (id,))
                return True
        except Exception as e:
            #clean up
            await self.bot.db.exec("delete from active_requests where id = %s", (id,))
            #then re-raise the error
            #this **will** cancel the confirmation
            raise e
        return False

    async def _handle_request(self, id, requesttype, ctx):
        try:
            confirmation(self.bot, [self.bot.strings["DELETION_CONFIRMED"], self.bot.strings["DELETION_DENIED"]], discord.Embed.from_dict(self.mainembeds[requesttype]), ctx, self.confirmation_callback, requesttype, id)
        except asyncio.TimeoutError:
            await self.bot.db.exec("delete from active_requests where id = %s", (id,))
            await ctx.send(self.bot.strings["DELETION_TIMEOUT"])
            return

    async def create_request(self, requesttype, ctx):
        '''Attempts to create a deletion request, raises errors.DeletionRequestAlreadyActive if one's active'''
        id = ctx.guild.id if requesttype == 'all' else ctx.author.id
        result = await self.bot.db.exec("select id from active_requests where id=%s", (id,))
        if not result:
            await self.bot.db.exec("insert into active_requests values(%s)", (id,))
            await self._handle_request(id, requesttype, ctx)
        elif result:
            raise DeletionRequestAlreadyActive()

    async def delete_all(self, ctx):
        #TODO: More elegant solution than whatever the hell this is
        await self.bot.db.exec("delete from roles where guild_id = %s", (ctx.guild.id,))
        await self.bot.db.exec("delete from responses where guild_id = %s", (ctx.guild.id,))
        await self.bot.db.exec("delete from prefixes where guild_id = %s", (ctx.guild.id,))
        responses = self.bot.get_cog("Custom Commands")
        await responses.fill_cache()
        await self.bot.prefixes.update_prefix_cache()

class core(commands.Cog):
    '''Utility commands and a few events. The commands here are only usable by the owner.'''
    __slots__ = ("bot", "waiting", "get_named_logger", "reload_enabled")

    def __init__(self, bot, load=False):
        self.bot = bot
        #we can't easily import this file from files in the cogs folder
        #provide references to other classes in the file to prevent this
        self.bot.confirmation = confirmation
        self.bot.deletion_request = deletion_request
        self.bot.DeletionRequestAlreadyActive = DeletionRequestAlreadyActive
        self.bot.core = self
        self.waiting = []
        self.bot.blocklist = []
        self.logger = logging.getLogger(__name__)
        self.bot.ready = False
        self.reload_enabled = True
        if load:
            asyncio.create_task(self.update_blocklist())
            #disable reload command if gitpython isn't installed
            #this is done in a task to make sure it's done after commands have been registered
            asyncio.create_task(self.check_for_git())

    async def send_debug(self, ctx):
        if self.bot.settings.general.ready: #check if category's ready to prevent potential attributeerrors
            if self.bot.settings.general.debug.enabled(ctx.guild.id):
                await ctx.send(self.bot.strings["DEBUG_INFO"])
                await self.send_traceback(ctx.channel)
                await ctx.send(self.bot.strings["DEBUG_DISABLE_REMINDER"])

    async def send_traceback(self, target=None):
        paginator = commands.Paginator()
        for line in traceback.format_exc().split("\n"):
            paginator.add_line(line)
        if not target:
            target = self.bot.get_user(self.bot.owner_id)
        if not target:
            return
        for page in paginator.pages:
            await target.send(page)

    async def check_for_git(self):
        try:
            import git
        except (ImportError, ModuleNotFoundError):
            self.reload_enabled = False
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
        if not self.reload_enabled:
            return await ctx.send("Sorry, this command is disabled. Install `gitpython` to enable it.")
        await ctx.typing()
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
            self.bot.prefixes = self.bot.get_cog('prefixes')
            self.bot.responses = self.bot.get_cog('Custom Commands')
            self.bot.reactionrolesinst = self.bot.get_cog('reaction roles')
            embed = discord.Embed(title=f"\U00002705 {extensionsreloaded}", color=self.bot.config['theme_color'])
        except:
            embed = discord.Embed(title=f"\U0000274c Error while reloading extensions.")
            embed.add_field(name="Error:", value=traceback.format_exc())
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.ready = True
            self.logger.info(f"on_ready was dispatched {time.time()-self.bot.start_time} seconds after init started")
            self.bot.commandnames = [i.name for i in self.bot.commands if not i.hidden and i.name != "jishaku"]
            self.bot.help_command = helpcommand.HelpCommand(verify_checks=False)
            await self.bot.tree.sync()
            print("Ready")

    async def prepare(self, message):
        if message.author != self.bot.user:
            if message.author.id in self.bot.blocklist:
                return False
            if message.guild is not None:
                if self.bot.responses:
                    try:
                        for each in range(len(self.bot.responses)):
                            if int(self.bot.responses[each][0]) == int(message.guild.id):
                                if await self.bot.get_prefix(message) + self.bot.responses[each][1].lower() == message.content.lower().strip():
                                    await message.channel.send(self.bot.responses[each][2])
                                    return False
                    except:
                        return True
            return True
        else:
            return False

    @commands.is_owner()
    @utils.command(hidden=True)
    async def reload_strings(self, ctx):
        try:
            reloading = await ctx.send("Reloading strings...")
            self.bot.strings = await startup.load_strings(self.bot.logger, self.bot.config, exit=False)
            await ctx.send("Done.")
        except:
            await reloading.add_reaction("\U00002757")
            return await ctx.send(f"{traceback.format_exc()}")


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
            result = await self.bot.db.exec(query, ())
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
            newblocklist = [i['user_id'] for i in await self.bot.db.exec("select * from blocked", ())]
            self.bot.blocklist = newblocklist
        except TypeError:
            return self.logger.info("Failed to update blocklist, is there anything in the database?")
        self.logger.info("Updated blocklist!")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def block(self, ctx, member:typing.Union[discord.Member, discord.User]):
        if member.id in self.bot.blocklist:
            return await ctx.send(f"I already have {member} blocked.")
        await self.bot.db.exec(f"insert into blocked values(%s)", (member.id,))
        await self.update_blocklist()
        await ctx.send(f"Added {member} to the blocklist.")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def unblock(self, ctx, member:typing.Union[discord.Member, discord.User]):
        if member.id not in self.bot.blocklist:
            return await ctx.send(f"{member} isn't blocked.")
        await self.bot.db.exec(f"delete from blocked where user_id = %s", (member.id,))
        await self.update_blocklist()
        await ctx.send(f"Removed {member} from the blocklist.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.bot.prefixes.update_prefix_cache(guild.id)
        for name in self.bot.settings.categorynames:
            while not getattr(self.bot.settings, name).ready:
                await asyncio.sleep(0.01)
            await getattr(self.bot.settings, name).fill_cache()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.prefixes.update_prefix_cache(guild.id)

    async def cog_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(self.bot.strings["NOT_OWNER"])
        else:
            await self.bot.get_user(self.bot.owner_id).send("oh :blobpaiN; here's an error" + traceback.format_exc())


async def setup(bot):
    await bot.add_cog(core(bot, True))

async def teardown(bot):
    await bot.remove_cog(core(bot))

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
