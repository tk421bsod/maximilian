#errorhandling.py: handles most errors. old and needs to be updated

import traceback

import discord
import pymysql
from discord.ext import commands


class errorhandling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        owner = self.bot.get_user(538193752913608704)
        try:
            await owner.send(f"An error occurred in {ctx.guild.name} ({ctx.guild.id}): ")
            await owner.send(f"`{traceback.format_exc()}`")
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
        if isinstance(error, pymysql.err.OperationalError) or isinstance(error, pymysql.err.ProgrammingError):
            embed = discord.Embed(title="Fatal Error",description="\U0000274c You shouldn't see this message. If you do, an unexpected database error has occurred. \nContact my developer (tk421#2016) if you see this again.", color=discord.Color.blurple())
            if ctx.guild.me.guild_permissions.embed_links:
                await ctx.send(embed=embed)
            else:
                await ctx.send("\U0000274c Something's gone terribly wrong on my end. If you were trying to create a custom command, change my prefix, or modify reaction roles, the changes might not have been saved. Try the command again, and if you encounter this issue again, please contact my developer (tk421#7244), and they'll look into it. Currently, I'm not allowed to send embeds, which will make some responses look worse and prevent `userinfo` from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
        if isinstance(error, commands.BotMissingPermissions) or isinstance(error, discord.errors.Forbidden) or 'discord.errors.Forbidden' in str(error):
            try:
                embed = discord.Embed(title=f"\U0000274c I don't have the permissions to run this command, try moving my role up or giving me the `{error.missing_perms[0]}` permission.", color=discord.Color.blurple())
            except AttributeError:
                embed = discord.Embed(title=f"\U0000274c I don't have the permissions to run this command, try moving my role up.", color=discord.Color.blurple())
            if ctx.guild.me.guild_permissions.embed_links:
                await ctx.send(embed=embed)
            else:
                await ctx.send("\U0000274c I don't have the permissions to run this command, try moving my role up. I'm also not allowed to send embeds, which will make some responses look worse, and will prevent certain modules from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
            return
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.NotOwner):
            message = "You don't have the permissions needed to run that command. Try using `{await self.bot.get_prefix(ctx.message)}help <command>` to get more info on that command, including the required permissions."
            await ctx.send(message)
            return
        if isinstance(error, commands.MissingRequiredArgument):
            if ctx.guild.me.guild_permissions.embed_links:
                embed = discord.Embed(title="\U0000274c You didn't provide the required parameter `" + error.param.name + "`. See the help entry for `" + ctx.command.name + "` to see what parameters this command takes." )
                await ctx.send(embed=embed)
                return
            else:
                await ctx.send(f"\U0000274c You didn't provide the required argument `{error.param.name}`. See the help entry for `{ctx.command.name}` to see what arguments this command takes. Currently, I'm not allowed to send embeds, which will make some responses look worse and prevent `userinfo` from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
                return
        if isinstance(error, commands.CommandNotFound):
            return
        await ctx.send("There was an error. Please try again later.")
        if not str(error):
            error = error.__name__
        await ctx.send(f"`{error}`")

async def setup(bot):
    await bot.add_cog(errorhandling(bot))

async def teardown(bot):
    await bot.remove_cog(errorhandling(bot))
