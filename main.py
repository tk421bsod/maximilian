#import libraries
import discord
from discord.ext import commands 
from discord.ext import tasks
import common
import importlib
import logging
import time
import calendar
import os
import sys
import git 
import pymysql

#set up logging
logging.basicConfig(level=logging.WARN)
logger = logging.getLogger('discord')
logger.info("starting...")
#create instance of 'Token' class, decrypt token
tokeninst = common.token()
decrypted_token = tokeninst.decrypt("token.txt")
#set intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
#create Bot instance, setting default prefix, owner id, intents, and status
bot = commands.Bot(commands.when_mentioned_or("!"), owner_id=538193752913608704, intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="myself start up!"))
#initialize variables that'll be needed later
bot.guildlist = []
bot.prefixes = {}
bot.responses = []
bot.dbinst = common.db()
bot.database = "maximilian"
#try to connect to database, if it fails warn
try:
    bot.dbinst.connect(bot.database)
except pymysql.err.OperationalError:
    logger.critical("Couldn't connect to database, most features won't work.")
#load extensions
bot.load_extension('responses')
bot.load_extension('prefixes')
bot.load_extension('misc')
bot.load_extension('reactionroles')
bot.load_extension('userinfo')
bot.load_extension('jishaku')
#create instances of certain cogs, because we need to call functions within those cogs
bot.responsesinst = bot.get_cog('Custom Commands')
bot.prefixesinst = bot.get_cog('prefixes')
bot.miscinst = bot.get_cog('misc')
bot.reactionrolesinst = bot.get_cog('reaction roles')
logger.info('loaded extensions, waiting for on-ready')

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
        if responseslist is not None:
            for i in responseslist:
                responsestring += f"`{i['response_trigger']}` "
            embed.add_field(name="Custom Commands List", value=responsestring)
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title='{0.qualified_name} Commands'.format(cog), colour=self.color)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
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

@reset_status.before_loop
async def before_reset_status():
    await bot.wait_until_ready()

async def startup():
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds and " + str(len(bot.users)) + " users!"))

@bot.event
async def on_ready():
    print("recieved on_ready, finishing startup...")
    await bot.prefixesinst.reset_prefixes()
    await bot.responsesinst.get_responses()
    bot.help_command = HelpCommand()
    bot.loop.create_task(startup())
    reset_status.start()
    print("ready")
    
@bot.event
async def on_message(message):
    ctx = await bot.get_context(message)
    if message.author != bot.user:
        if message.guild is not None:
            try:    
                bot.command_prefix = commands.when_mentioned_or(bot.prefixes[str(message.guild.id)])
            except KeyError:
                print("Couldn't get prefixes for this guild, (am I starting up or resetting prefixes?), using default prefix instead")
                bot.command_prefix = commands.when_mentioned_or("!")
                pass
            for each in range(len(bot.responses)):
                if int(bot.responses[each][0]) == int(message.guild.id):
                    try:
                        if ctx.prefix + bot.responses[each][1].lower() == message.content.lower():
                            await message.channel.send(bot.responses[each][2])
                            return
                    except TypeError:
                        if bot.prefixes[str(message.guild.id)] + bot.responses[each][1].lower() == message.content.lower():
                            await message.channel.send(bot.responses[each][2])
                            return
        await bot.process_commands(message)

#catch errors that occur in commands
@bot.event
async def on_command_error(ctx, error):
    print("error")
    print(ctx.message.content)
    #prefix should be a string, not a function, so get it from the dict of prefixes (use default prefix if that fails)
    try:
        bot.command_prefix = bot.prefixes[str(ctx.guild.id)]
    except KeyError:
        bot.command_prefix = "!"
    #get the original error so isinstance works
    error = getattr(error, "original", error)
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
        embed = discord.Embed(title=f"\U0000274c I don't have the permissions to run this command, try moving my role up in the hierarchy or giving me the `{error.missing_perms[0]}` permission.", color=discord.Color.blurple())
        if ctx.guild.me.guild_permissions.embed_links:
            await ctx.send(embed=embed)
        else:
            await ctx.send("\U0000274c I don't have the permissions to run this command, try moving my role up in the hierarchy. I'm also not allowed to send embeds, which will make some responses look worse, and will prevent userinfo from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
        return
    if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.NotOwner):
        print("User doesn't have the correct permissions")
        embed = discord.Embed(title="\U0000274c You don't have the permissions to run this command.", color=discord.Color.blurple())
        embed.add_field(name="Why did this happen? What can I do?", value=f"Some commands require certain permissions; try using `{bot.command_prefix}help <commandname>` to get more info on that command, including the required permissions.", inline=False)
        if ctx.guild.me.guild_permissions.embed_links:
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"You don't have the permissions to run this command. Some commands require certain permissions; try using `{bot.command_prefix}help <commandname>` to get more info about that command, including the required permissions. I'm also not allowed to send embeds, which will make some responses look worse, and will prevent `userinfo` from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
        return
    if isinstance(error, commands.CommandNotFound):
        print("Can't find a command")
        embed = discord.Embed(title=f"\U0000274c I can't find that command. Use `{bot.command_prefix}help` to see a list of commands.", color=discord.Color.blurple())
        if ctx.guild.me.guild_permissions.embed_links:
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"\U0000274c I can't find that command. Use `{bot.command_prefix}help` to see a list of commands, or change my prefix using the `prefix` command if I'm conflicting with another bot. Currently, I'm not allowed to send embeds, which will make some responses look worse and prevent `userinfo` from functioning. To allow me to send embeds, go to Server Settings > Roles > Maximilian and turn on the 'Embed Links' permission.")
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
    await ctx.send("My prefixes in this server are " + prefixstring + " and <@!620022782016618528>")


@bot.event
async def on_guild_join(guild):
    print("joined guild, adding guild id to list of guilds and resetting prefixes")
    bot.guildlist.append(str(guild.id))
    await bot.prefixesinst.reset_prefixes()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds and " + str(len(bot.users)) + " users!"))

@bot.event
async def on_guild_remove(guild):
    print("removed from guild, removing that guild from list of guilds and resetting prefixes")
    bot.guildlist.remove(str(guild.id))
    await bot.prefixesinst.reset_prefixes()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds and " + str(len(bot.users)) + " users!"))

@bot.event
async def on_command_completion(ctx):
    print(ctx.command.name)
    print(ctx.message.content)
    print("sent in " + ctx.guild.name)

@commands.is_owner()
@bot.command(hidden=True)
async def change_status(ctx, type, newstatus):
    reset_status.stop()
    await ctx.send("Changing status...")
    if type.lower() == "streaming":
        await bot.change_presence(activity=discord.Streaming(name=" my development!", url=newstatus))
    elif type.lower() == "listening":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=newstatus))
    elif type.lower() == "watching":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=newstatus))
    elif type.lower() == "default":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds and " + str(len(bot.users)) + " users!"))
        reset_status.start()
    else:
        await ctx.send("That's an invalid status type!")
        return
    await ctx.send("Changed status!")

@commands.is_owner()
@bot.command(hidden=True)
async def reload(ctx, *targetextensions):
    await ctx.trigger_typing()
    try:
        if len(targetextensions) == 1:
            extensionsreloaded = "Successfully reloaded 1 extension."
        elif len(targetextensions) == 0:
            embed = discord.Embed(title="\U0000274e You need to specify at least 1 extension to reload.", color=discord.Color.blurple())
            await ctx.send(embed=embed)
            return
        else:
            extensionsreloaded = f"Successfully reloaded {str(len(targetextensions))} extensions."
        reloadmessage = await ctx.send("Fetching latest revision...", delete_after=20)
        repo = git.Repo(os.getcwd())
        o = repo.remotes.origin
        o.pull()
        await reloadmessage.edit(content="Got latest revision. Reloading extensions...")
        for each in targetextensions:
            bot.reload_extension(each)
        bot.responsesinst = bot.get_cog('Custom Commands')
        bot.prefixesinst = bot.get_cog('prefixes')
        bot.miscinst = bot.get_cog('misc')
        bot.reactionrolesinst = bot.get_cog('reaction roles')
        await bot.prefixesinst.reset_prefixes()
        await bot.responsesinst.get_responses()
        embed = discord.Embed(title=f"\U00002705 {extensionsreloaded}", color=discord.Color.blurple())
    except Exception as e:
        print(e)
        if len(list(str(e))) >= 200:
            embed = discord.Embed(title=f"\U0000274c Error while reloading extensions.")
            embed.add_field(name="Error:", value=str(e))
        else:
            embed = discord.Embed(title=f"\U0000274c Error while reloading extensions: {str(e)}.")
        embed.add_field(name="What might have happened:", value="You might have mistyped the extension name; the extensions are `misc`, `reactionroles`, `prefixes`, `responses`, and `userinfo`. If you created a new extension, make sure that it has a setup function, and you're calling `Bot.load_extension(name)` somewhere in main.py.")
    await ctx.send(embed=embed) 

bot.run(decrypted_token)
