#errorhandling.py: handles most errors. old and needs to be updated

import aiomysql
import discord
from discord.ext import commands

class errorhandling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        owner = self.bot.get_user(self.bot.config['owner_id'])
        try:
            await owner.send(f"An error occurred in {ctx.guild.name} ({ctx.guild.id}): ")
            await self.bot.core.send_traceback(owner, error)
        except:
            pass
        #get the original error so isinstance works
        error = getattr(error, "original", error)
        cog = ctx.cog
        if cog:
            #ignore errors handled in cog_command_error
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return
        #check for database errors first, these should almost never happen
        if isinstance(error, aiomysql.OperationalError) or isinstance(error, aiomysql.ProgrammingError):
            embed = self.bot.core.ThemedEmbed(title=self.bot.strings["GENERIC_FATAL_ERROR_TITLE"],description=self.bot.strings["GENERIC_FATAL_ERROR"])
            if ctx.guild.me.guild_permissions.embed_links:
                await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions) or isinstance(error, discord.errors.Forbidden) or 'discord.errors.Forbidden' in str(error):
            try:
                embed = self.bot.core.ThemedEmbed(title=self.bot.strings["ERROR_MISSING_PERMISSIONS_SPECIFIC"].format(error.missing_perms[0]))
            except AttributeError:
                embed = self.bot.core.ThemedEmbed(title=self.bot.strings["ERROR_MISSING_PERMISSIONS_GENERAL"])
            if ctx.guild.me.guild_permissions.embed_links:
                await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions) or isinstance(error, commands.NotOwner):
            message = self.bot.strings["ERROR_USER_MISSING_PERMISSIONS"].format(await self.bot.get_prefix(ctx.message))
            await ctx.send(message)
        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(embed=self.bot.core.ThemedEmbed(title=self.bot.strings["ERROR_COMMAND_DISABLED"]))
        elif isinstance(error, commands.MissingRequiredArgument):
            if ctx.guild.me.guild_permissions.embed_links:
                embed = self.bot.core.ThemedEmbed(title=self.bot.strings["ERROR_MISSING_ARGUMENT"].format(error.param.name, ctx.command.name))
                await ctx.send(embed=embed)
        elif isinstance(error, commands.CommandNotFound):
            return
        else:
            await ctx.send(embed=self.bot.core.ThemedEmbed(title=self.bot.strings["GENERIC_ERROR_TITLE"], description=self.bot.strings["GENERIC_ERROR"]))
            if not str(error):
                error = error.__name__
            await ctx.send(f"`{error}`")
        await self.bot.core.send_debug(ctx)

async def setup(bot):
    await bot.add_cog(errorhandling(bot))

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
