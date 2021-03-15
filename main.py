#import libraries
import discord
from discord.ext import commands 
from discord.ext import tasks
import logging
import sys
import init
import common
import helpcommand
import pymysql
import traceback

print("starting...")
token = common.token().get("token.txt")
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=discord.Intents.all(), activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.5.1 (stable)"))
init.config_logging(sys.argv)
init.init(bot).parse_arguments(sys.argv)
bot.logger = logging.getLogger('maximilian-stable')
bot.guildlist = []
bot.prefixes = {}
bot.responses = []
bot.dbinst = common.db(bot)
bot.database = "maximilian"
#try to connect to database, if it fails warn
print(f"Attempting to connect to database '{bot.database}' on '{bot.dbip}'...")
try:
    bot.dbinst.connect(bot.database)
    print("Connected to database successfully.")
except pymysql.err.OperationalError:
    bot.logger.critical("Couldn't connect to database, most features won't work. Make sure you passed the right IP and that the database is configured properly.")
#load extensions
extensioncount = 0
for roots, dirs, files in os.walk("./cogs"):
    for each in files:
        if each.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{each[:-3]}")
                extensioncount += 1
            except commands.ExtensionFailed as error:
                bot.logger.error(f"{type(error.original).__name__} while loading '{error.name}'. Check the debug logs for more information.")
                if isinstance(error.original, SyntaxError):
                    bot.logger.debug(traceback.format_exc())
                elif isinstance(error.original, ModuleNotFoundError) or isinstance(error.original, ImportError):
                    bot.logger.error(f"The {error.original.name} module isn't installed, '{error.name}' won't be loaded")
#create instances of certain cogs, because we need to call functions within those cogs
try:
    bot.load_extension("core")
    bot.load_extension("errorhandling")
except:
    bot.logger.error("Failed to get one or more cogs, some stuff might not work.")
print(f'loaded {extensioncount} extensions, waiting for ready')

class HelpCommand(commands.HelpCommand):
    color = discord.Colour.blurple()
    def get_ending_note(self):
        return 'Use {0}{1} [command] for more info on a command.'.format(self.clean_prefix, self.invoked_with)

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = '[%s|%s]' % (command.name, aliases)
            if parent:
                fmt = parent + ' ' + fmt
            alias = fmt
        else:
            alias = command.name if not parent else parent + ' ' + command.name

        return '%s%s %s' % (self.clean_prefix, alias, command.signature)

    async def send_bot_help(self, mapping):
        if not self.context.guild.me.guild_permissions.embed_links:
            return await self.get_destination().send("It looks like I don't have permission to send embeds. My developer's working on a different help command that doesn't use them, but for now you'll need to enable the 'Embed Links' permission to be able to use the help command. To enable it, go to Server Settings > Roles > Maximilian, and you should see the Embed Links permission there.")
        embed = discord.Embed(title='Commands', colour=self.color)
        description = self.context.bot.description
        if description:
            embed.description = description

        for cog, commands in mapping.items():
            if cog is not None:
                name = cog.qualified_name
                filtered = await self.filter_commands(commands, sort=True)
                if filtered:
                    value = '\u2002 '.join('`' + c.name + '`' for c in commands if not c.hidden)
                    if cog and cog.description:
                        value = '{0}\n{1}'.format(cog.description, value)

                    embed.add_field(name=name, value=value)
        responseslist = self.context.bot.dbinst.exec_query(self.context.bot.database, "select * from responses where guild_id = {}".format(self.context.guild.id), False, True)
        responsestring = "A list of custom commands for this server. These don't have help entries. \n"
        if responseslist is not None and str(responseslist)!="()":
            for i in responseslist:
                responsestring += f"`{i['response_trigger']}` "
            embed.add_field(name="Custom Commands List", value=responsestring)
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        if not self.context.guild.me.guild_permissions.embed_links:
            return await self.get_destination().send("It looks like I don't have permission to send embeds. My developer's working on a different help command that doesn't use them, but for now you'll need to enable the 'Embed Links' permission to be able to use the help command. To enable it, go to Server Settings > Roles > Maximilian, and you should see the Embed Links permission there.")
        embed = discord.Embed(title='{0.qualified_name} Commands'.format(cog), colour=self.color)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        if not self.context.guild.me.guild_permissions.embed_links:
            return await self.get_destination().send("It looks like I don't have permission to send embeds. My developer's working on a different help command that doesn't use them, but for now you'll need to enable the 'Embed Links' permission to be able to use the help command. To enable it, go to Server Settings > Roles > Maximilian, and you should see the Embed Links permission there.")
        embed = discord.Embed(title=group.qualified_name, colour=self.color)
        if group.help:
            embed.description = group.help

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)
    send_command_help = send_group_help

@tasks.loop(seconds=60)
async def reset_status():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds and " + str(len(bot.users)) + " users!"))

print("Loaded required extensions successfully. Loading other cogs...")
init.init(bot).load_extensions()
    
@bot.event
async def on_message(message):
    if await bot.coreinst.prepare(message):
        await bot.process_commands(message)

#catch errors that occur in commands
@bot.event
async def on_command_error(ctx, error):
    etype = type(error)
    trace = error.__traceback__
    lines = traceback.format_exception(etype, error, trace)
    # format_exception returns a list with line breaks embedded in the lines, so let's just stitch the elements together
    traceback_text = ''.join(lines)
    # now we can send it to the user
    # it would probably be best to wrap this in a codeblock via e.g. a Paginator
    owner = bot.get_user(538193752913608704)
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
        bot.command_prefix = bot.prefixes[str(ctx.guild.id)]
    except KeyError:
        bot.command_prefix = "!"
    if isinstance(error, discord.errors.Forbidden) or isinstance(error, discord.Forbidden):
        try:
            if not ctx.guild.me.guild_permissions.embed_links and cog.qualified_name == "music":
                await ctx.send("I need the 'Embed Links' permission to play songs. (or run any music related commands)")
                try:
                    bot.musicinst.channels_playing_audio.remove(ctx.voice_client.channel.id)
                except:
                    pass
                return
        except:
            pass
    if isinstance(error, KeyError) and cog.qualified_name == "music":
        await ctx.send(f"There was an error. Try making me leave the voice channel using `{bot.command_prefix}leave`, then try repeating what you were doing. My developer has been made aware of this.")
        return
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
        embed.add_field(name="Why did this happen? What can I do?", value=f"Some commands require certain permissions; try using `{bot.command_prefix}help {ctx.command.name}` to get more info on that command, including the required permissions.", inline=False)
        if ctx.guild.me.guild_permissions.embed_links:
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"You don't have the permissions to run this command. Some commands require certain permissions; try using `{bot.command_prefix}help {ctx.command.name}` to get more info about that command, including the required permissions. I'm also not allowed to send embeds, which will make some responses look worse, and will prevent `userinfo` from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
        return
    if isinstance(error, commands.CommandNotFound):
        print("Can't find a command")
        commandscores = []
        #for each command, check how similar it is to the command the user tried
        for each in bot.commandnames:
            await bot.loop.run_in_executor(None, lambda: commandscores.append([each, fuzz.token_set_ratio(ctx.invoked_with, each)]))
        print(commandscores)
        #if a command is similar enough, put it in a list of similar commands, then form a string with those commands
        similarcommands = '\n'.join([i for i in [f'`{i[0]}`' for i in commandscores if i[1] > 55]])
        #can't include backslashes in fstring expressions, this is a hacky "fix" for that
        newline = "\n"
        embed = discord.Embed(title=f"\U0000274c I can't find that command. \n{f'Similar commands: {newline}{similarcommands}' if similarcommands != '' else 'No similar commands found.'}\nUse `{bot.command_prefix}help` to see a list of commands.", color=discord.Color.blurple())
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

@bot.command(help="Get a new list of custom responses after adding a new response", aliases=['fetchresponses', 'getresponses'])
async def fetch_responses(ctx):
    gettingresponsesmessage = await ctx.send("Getting a new list of responses...")
    await bot.responsesinst.get_responses()
    await gettingresponsesmessage.edit(content="Got a new list of responses!")

@bot.command(help="List all prefixes")
async def listprefixes(ctx):
    prefixstring = ""
    for key in bot.prefixes.keys():
        if key == str(ctx.message.guild.id):
            prefixstring = prefixstring + "`" + bot.prefixes[key] + "`"
    await ctx.send(f"My prefixes in this server are {prefixstring} and {ctx.guild.me.mention}")

@bot.before_invoke
async def before_anything(ctx):
    #before any commands are executed, make sure to set commandprefix (will be removed soon)
    try:
        bot.commandprefix = bot.prefixes[str(ctx.guild.id)]
    except (KeyError, AttributeError):
        bot.commandprefix = "!"

bot.run(token)
