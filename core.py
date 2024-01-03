#core.py: deletion/confirmation handlers, event listeners, helpers, owner-only commands

#note that this module is loaded during early startup. the 'core' class defined below is loaded in load_extensions_async.

import asyncio
import logging
import time
import traceback
import typing
import discord
from discord.ext import commands

import common
import components
import startup

def get_prefix(bot, message):
    if not getattr(bot, "prefixes", None):
        try:
            asyncio.run_coroutine_threadsafe(bot.prefixes.update_prefix_cache())
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

class core(commands.Cog):
    '''Utility commands and a few events. The commands here are only usable by the owner.'''
    __slots__ = ("bot")

    def __init__(self, bot, load=False):
        self.bot = bot
        self.bot.init_finished = False
        #Provide references to various components to avoid import shenanigans in other dirs
        #TODO: Maybe move this somewhere else? Now that these classes don't exist here it doesn't make much sense
        self.bot.confirmation = components.confirmation
        self.bot.deletion_request = components.deletion_request
        self.bot.DeletionRequestAlreadyActive = components.DeletionRequestAlreadyActive
        self.bot.core = self
        self.bot.blocklist = []
        self.logger = logging.getLogger(__name__)
        if load:
            asyncio.create_task(self.update_blocklist())
 
    def ThemedEmbed(self, *args, **kwargs):
        """A discord.Embed that uses the theme color"""
        return components._ThemedEmbed(self.bot.config['theme_color'], *args, **kwargs)

    async def getch_channel(self, channel_id):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            channel = await self.bot.fetch_channel(channel_id)
        return channel

    async def send_paginated_embed(self, paginator, to_send, target):
        if to_send.description:
            self.logger.debug("Sourcing paginated embed content from description")
            #TODO: On some special embeds e.g todo lists this can break groups of text in half.
            #Consider adding text groups on the same "line" on the paginator and only moving on once reaching a blank line.
            for line in to_send.description.split("\n"):
                paginator.add_line(line)
        if to_send.fields:
            self.logger.debug("Sourcing paginated embed content from fields")
            for field in to_send.fields:
                paginator.add_line(f"\n**{field.name}**")
                for line in field.value.split("\n"):
                    paginator.add_line(line)
        #Edge case where the embed only has a title.
        #Used in some status messages.
        if not paginator.pages:
            return await target.send(embed=to_send)
        for count, page in enumerate(paginator.pages):
            title = to_send.title
            if len(paginator.pages) > 1:
                title += self.bot.strings["PAGINATOR_ADDITIONAL_PAGES"].format(count+1)
            #TODO: This can break some embed layouts as we may be converting from separate fields to a description.
            embed = self.ThemedEmbed(title=title, description=page)
            self.logger.debug(f"page {count+1} of {len(paginator.pages)}")
            if count+1 == len(paginator.pages) and to_send.footer:
                embed.set_footer(text=to_send.footer.text)
            await target.send(embed=embed)

    #TODO: View-based paginator
    async def send_paginated(self, to_send, target, prefix="```", suffix="```"):
        self.logger.debug(f"send_paginated called with ({type(to_send)}, {target}, {prefix}, {suffix})")
        paginator = commands.Paginator(prefix=prefix, suffix=suffix)
        if isinstance(to_send, discord.Embed):
            await self.send_paginated_embed(paginator, to_send, target)
        else:
            for line in to_send.split("\n"):
                paginator.add_line(line)
            for page in paginator.pages:
                await target.send(page)

    async def send_debug(self, ctx):
        try:
            self.bot.settings.general
        except:
            return
        if self.bot.settings.general.ready: #check if category's ready to prevent potential attributeerrors
            if self.bot.settings.general.debug.enabled(ctx.guild.id):
                await ctx.send(self.bot.strings["DEBUG_INFO"])
                await self.send_traceback(ctx.channel)
                await ctx.send(self.bot.strings["DEBUG_DISABLE_REMINDER"])

    async def send_traceback(self, target=None, error=None):
        if not target:
            target = self.bot.get_user(self.bot.owner_id)
        if not target:
            return
        if error:
            text = traceback.format_exception(type(error), error, error.__traceback__)
        else:
            text = traceback.format_exc()
        await self.send_paginated("".join(text), target)

    @commands.group(invoke_without_command=False, hidden=True)
    async def utils(self, ctx):
        pass

    @commands.is_owner()
    @utils.command(hidden=True)
    async def sync(self, ctx):
        """Sync slash commands."""
        await ctx.send("Syncing the command tree...")
        await self.bot.tree.sync()
        await ctx.send("Done.")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def blocklist(self, ctx):
        """Show a list of blocked users."""
        await ctx.send("Fetching blocklist...")
        users = "\n".join([str(self.bot.get_user(i)) for i in self.bot.blocklist]) 
        await ctx.send(f"I have {len(self.bot.blocklist)} users blocked. They are: \n{users}")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def loaded(self, ctx):
        """Display a list of all loaded modules."""
        current = [f"{ext}" for ext in list(self.bot.extensions)]
        desc = "\n".join(current)
        embed = self.ThemedEmbed(title="Modules loaded:", description=desc)
        await self.bot.core.send_paginated(embed, ctx)

    @commands.is_owner()
    @utils.command(hidden=True)
    async def load(self, ctx, *targets):
        """Attempt to load all modules specified in `targets`. `targets` must be a list of one or more module names.

        Key:
            \u2705 - Module loaded successfully.
            \u26a0\ufe0f - Module was already loaded.
            \u274e - Module failed to load. See tracebacks for more details.
        """
        await ctx.typing()
        ret = []
        tracebacks = []
        if not targets:
            return await ctx.send("You must provide a list of modules to load.")
        for ext in targets:
            try:
                await self.bot.load_extension(ext)
                ret.append(f"\u2705 {ext}")
            except commands.ExtensionAlreadyLoaded:
                ret.append(f"\u26a0\ufe0f {ext}")
            except:
                ret.append(f"\u274e {ext}")
                tracebacks.append(traceback.format_exc())
        ret.append(f"Use `{await self.bot.get_prefix(ctx.message)}help utils load` for an explanation of these symbols.")
        await ctx.send("\n".join(ret))
        if tracebacks:
            await self.bot.core.send_paginated("\n".join(tracebacks), ctx, prefix="```py")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def unload(self, ctx, *targets):
        """Attempt to unload all modules specified in `targets`. `targets` must be a list of one or more module names.

        Key:
            \u2705 - Module was unloaded successfully.
            \u26a0\ufe0f - Module was not loaded.
        """
        await ctx.typing()
        ret = []
        if not targets:
            return await ctx.send("You must provide a list of modules to unload.")
        for ext in targets:
            try:
                await self.bot.unload_extension(ext)
                ret.append(f"\u2705 {ext}")
            except commands.ExtensionNotLoaded:
                ret.append(f"\u26a0\ufe0f {ext}")
        ret.append(f"Use `{await self.bot.get_prefix(ctx.message)}help utils unload` for an explanation of these symbols.")
        await ctx.send("\n".join(ret))

    @commands.is_owner()
    @utils.command(hidden=True)
    async def reload(self, ctx, *targetextensions):
        """Reload <targetextensions>"""
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
                targetextensions = list(self.bot.extensions)
            else:
                extensionsreloaded = f"Successfully reloaded {str(len(targetextensions))} extensions."
            if nofetch:
                await ctx.send("Ok, I won't fetch the latest revision. Reloading extensions...")
            else:
                reloadmessage = await ctx.send("Fetching latest revision...")
                ret = await self.bot.loop.run_in_executor(None, common.run_command, "git pull")
                if ret['returncode']:
                    await ctx.send(traceback.print_exc())
                    await ctx.send("\U000026a0 Failed to get latest revision. Reloading local copies of extensions...")
                    extensionsreloaded = f"Reloaded {'1 extension' if len(targetextensions) == 1 else ''}{'all extensions' if len(targetextensions) == 0 else ''}{f'{len(targetextensions)} extensions' if len(targetextensions) > 1 else ''}, but no changes were pulled."
                else:
                    if self.bot.settings.general.ready: #check if category's ready to prevent potential attributeerrors
                        if self.bot.settings.general.debug.enabled(ctx.guild.id):
                            await self.send_paginated("\n".join(ret['output']), ctx)
                    await reloadmessage.edit(content=f"Reloading extensions...")
            for each in targetextensions:
                await self.bot.reload_extension(each)
            self.bot.prefixes = self.bot.get_cog('prefixes')
            self.bot.responses = self.bot.get_cog('Custom Commands')
            self.bot.reactionrolesinst = self.bot.get_cog('reaction roles')
            embed = self.ThemedEmbed(title=f"\U00002705 {extensionsreloaded}")
        except:
            embed = self.ThemedEmbed(title=f"\U0000274c Error while reloading extensions.")
            embed.add_field(name="Error:", value=traceback.format_exc())
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.init_finished:
            self.bot.init_finished = True
            self.logger.info(f"on_ready was dispatched {time.time()-self.bot.start_time} seconds after init started")
            self.bot.commandnames = [i.name for i in self.bot.commands if not i.hidden and i.name != "jishaku"]
            print("Ready")

    async def prepare(self, message):
        if message.author != self.bot.user:
            if message.author.id in self.bot.blocklist or message.author.bot:
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
        """Reload language files without restarting."""
        try:
            reloading = await ctx.send("Reloading strings...")
            self.bot.strings = await startup.load_strings(self.bot.language, self.bot.logger)
            await ctx.send("Done.")
        except:
            await reloading.add_reaction("\U00002757")
            return await self.send_traceback()

    @commands.is_owner()
    @utils.command(hidden=True)
    async def disable(self, ctx, *, command):
        """Disable <command>."""
        command = self.bot.get_command(command)
        if not command:
            return await ctx.send("Sorry, that command couldn't be found.")
        if not command.enabled:
            return await ctx.send("That command is already disabled.")
        command.enabled = False
        await ctx.send(embed=self.ThemedEmbed(title="✅ Command disabled."))

    @commands.is_owner()
    @utils.command(hidden=True)
    async def enable(self, ctx, *, command):
        """Enable <command>."""
        command = self.bot.get_command(command)
        if not command:
            return await ctx.send("Sorry, that command couldn't be found.")
        if command.enabled:
            return await ctx.send("That command is already enabled.")
        command.enabled = True
        await ctx.send(embed=self.ThemedEmbed(title="✅ Command enabled."))

    @commands.is_owner()
    @utils.command(hidden=True)
    async def change_status(self, ctx, type, newstatus=None):
        """Change the status that the bot displays. Defaults to the current version."""
        await ctx.send("Changing status...")
        if type.lower() == "listening":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=newstatus))
        elif type.lower() == "watching":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=newstatus))
        elif type.lower() == "playing":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=newstatus))
        elif type.lower() == "default":
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f" v{self.bot.VER}"))
        else:
            return await ctx.send("Sorry, that's an invalid status type.\nYou can choose from one of the following:\n`listening`\n`watching`\n`playing\n`default`")
        await ctx.send("Changed status!")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def sql(self, ctx, *, query):
        """Run a SQL query."""
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
                await self.send_paginated(result, ctx)

    async def update_blocklist(self):
        self.logger.info("Updating blocklist...")
        newblocklist = []
        try:
            newblocklist = [i['user_id'] for i in await self.bot.db.exec("select * from blocked", ())]
            self.bot.blocklist = newblocklist
        except TypeError:
            self.logger.debug(traceback.format_exc())
            return self.logger.info("Failed to update blocklist, is there anything in the database?")
        self.logger.info("Updated blocklist!")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def block(self, ctx, member:typing.Union[discord.Member, discord.User]):
        """Block someone from using the bot."""
        if member.id in self.bot.blocklist:
            return await ctx.send(f"I already have {member} blocked.")
        await self.bot.db.exec(f"insert into blocked values(%s)", (member.id,))
        await self.update_blocklist()
        await ctx.send(f"Added {member} to the blocklist.")

    @commands.is_owner()
    @utils.command(hidden=True)
    async def unblock(self, ctx, member:typing.Union[discord.Member, discord.User]):
        """Unblock someone."""
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
            await self.send_traceback()

async def setup(bot):
    await bot.add_cog(core(bot, True))

async def teardown(bot):
    await bot.remove_cog(core(bot))

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
