import discord
from discord.ext import commands
import pymysql
import traceback
from fuzzywuzzy import fuzz

class errorhandling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        etype = type(error)
        trace = error.__traceback__
        lines = traceback.format_exception(etype, error, trace)
        # format_exception returns a list with line breaks embedded in the lines, so let's just stitch the elements together
        traceback_text = ''.join(lines)
        # it would probably be best to wrap this in a codeblock via e.g. a Paginator
        owner = self.bot.get_user(538193752913608704)
        await owner.send(f"`{traceback_text}`")
        #get the original error so isinstance works
        error = getattr(error, "original", error)
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return
        print("error")
        print(ctx.message.content)
        #prefix should be a string, not a function, so get it from the dict of prefixes (use default prefix if that fails)
        try:
            self.bot.command_prefix = self.bot.prefixes[str(ctx.guild.id)]
        except (KeyError,AttributeError):
            self.bot.command_prefix = "!"
        #check for database errors first, these should almost never happen
        if isinstance(error, pymysql.err.OperationalError) or isinstance(error, pymysql.err.ProgrammingError) or isinstance(error, TypeError):
            print("database error, printing context and error type")
            print(str(error))
            print(str(ctx))
            embed = discord.Embed(title="Fatal Error",description="\U0000274c Something's gone terribly wrong on my end. If you were trying to create a custom command, change my prefix, or modify reaction roles, the changes might not have been saved. Try the command again, and if you encounter this issue again, please contact my developer (tk421#7244), and they'll look into it.", color=discord.Color.blurple())
            if ctx.guild.me.guild_permissions.embed_links:
                await ctx.send(embed=embed)
            else:
                await ctx.send("\U0000274c Something's gone terribly wrong on my end. If you were trying to create a custom command, change my prefix, or modify reaction roles, the changes might not have been saved. Try the command again, and if you encounter this issue again, please contact my developer (tk421#7244), and they'll look into it. Currently, I'm not allowed to send embeds, which will make some responses look worse and prevent `userinfo` from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
        if isinstance(error, commands.BotMissingPermissions) or isinstance(error, discord.errors.Forbidden) or 'discord.errors.Forbidden' in str(error):
            print("I'm missing permissions")
            try:
                embed = discord.Embed(title=f"\U0000274c I don't have the permissions to run this command, try moving my role up in the hierarchy or giving me the `{error.missing_perms[0]}` permission.", color=discord.Color.blurple())
            except AttributeError:
                embed = discord.Embed(title=f"\U0000274c I don't have the permissions to run this command, try moving my role up in the hierarchy.", color=discord.Color.blurple())
            if ctx.guild.me.guild_permissions.embed_links:
                await ctx.send(embed=embed)
            else:
                await ctx.send("\U0000274c I don't have the permissions to run this command, try moving my role up in the hierarchy. I'm also not allowed to send embeds, which will make some responses look worse, and will prevent userinfo from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
            return
        if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.NotOwner):
            print("User doesn't have the correct permissions")
            embed = discord.Embed(title="\U0000274c You don't have the permissions to run this command.", color=discord.Color.blurple())
            embed.add_field(name="Why did this happen? What can I do?", value=f"Some commands require certain permissions; try using `{self.bot.command_prefix}help <commandname>` to get more info on that command, including the required permissions.", inline=False)
            if ctx.guild.me.guild_permissions.embed_links:
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"You don't have the permissions to run this command. Some commands require certain permissions; try using `{self.bot.command_prefix}help <commandname>` to get more info about that command, including the required permissions. I'm also not allowed to send embeds, which will make some responses look worse, and will prevent `userinfo` from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
            return
        if isinstance(error, commands.CommandNotFound):
            print("Can't find a command")
            commandscores = []
            #for each command, check how similar it is to the command the user tried
            for each in self.bot.commandnames:
                await self.bot.loop.run_in_executor(None, lambda: commandscores.append([each, fuzz.token_set_ratio(ctx.invoked_with, each)]))
            print(commandscores)
            #if a command is similar enough, put it in a list of similar commands, then form a string with those commands
            similarcommands = '\n'.join([i for i in [f'`{i[0]}`' for i in commandscores if i[1] > 55]])
            #can't include backslashes in fstring expressions, this is a hacky "fix" for that
            newline = "\n"
            embed = discord.Embed(title=f"\U0000274c I can't find that command. \n{f'Similar commands: {newline}{similarcommands}' if similarcommands != '' else 'No similar commands found.'}\nUse `{self.bot.command_prefix}help` to see a list of commands.", color=discord.Color.blurple())
            if ctx.guild.me.guild_permissions.embed_links:
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"\U0000274c I can't find that command. \n{f'Similar commands: {newline}{similarcommands}' if similarcommands != '' else 'No similar commands found.'}", description="Change my prefix using the `prefix` command if I'm conflicting with another bot. Currently, I'm not allowed to send embeds, which will make some responses look worse and prevent `userinfo` from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            print("command is missing the required argument")
            if ctx.guild.me.guild_permissions.embed_links:
                embed = discord.Embed(title="\U0000274c You didn't provide the required argument `" + error.param.name + "`. See the help entry for `" + ctx.command.name + "` to see what arguments this command takes." )
                await ctx.send(embed=embed)
                return
            else:
                await ctx.send(f"\U0000274c You didn't provide the required argument `{error.param.name}`. See the help entry for `{ctx.command.name}` to see what arguments this command takes. Currently, I'm not allowed to send embeds, which will make some responses look worse and prevent `userinfo` from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
                return
        print("Other error")
        print(str(error))
        await ctx.send("There was an error. Please try again later.")
        await ctx.send(f"`{error}`")

def setup(bot):
    bot.add_cog(errorhandling(bot))

def teardown(bot):
    bot.remove_cog(errorhandling(bot))