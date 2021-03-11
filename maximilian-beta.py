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
<<<<<<< HEAD
#create instance of 'Token' class, get token
tokeninst = common.token()
token = tokeninst.get("betatoken.txt")
#set intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
#create Bot instance, setting default prefix, owner id, intents, and status
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="myself start up!"))
#set up logging
logging.basicConfig(level=logging.WARN)
bot.logger = logging.getLogger('maximilian')
#before setting up db instance, look at arguments and check if ip was specified
if len(sys.argv) > 1:
    if "--ip" in sys.argv:
        try:
            bot.dbip = sys.argv[sys.argv.index("--ip")+1]
        except IndexError:
            bot.logger.warning("If you use the --ip argument, which you did, you need to specify what ip address you want to use with the database. Since you didn't specify an IP address, I'll fall back to using localhost.")
            bot.dbip = "localhost"
    else:
        bot.logger.warning("Unrecognized argument. If you're trying to pass arguments to python, put them before the filename. Falling back to localhost.")
        bot.dbip = "localhost"
    if "--enablejsk" in sys.argv:
        bot.load_extension("jishaku")
        print("Loaded Jishaku.")
else:
    bot.logger.warning("No database IP provided. Falling back to localhost.")
    bot.dbip = "localhost"
#initialize variables that'll be needed later
=======
token = common.token().get("betatoken.txt")
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=discord.Intents.all(), activity=discord.Activity(type=discord.ActivityType.playing, name=" with new features! v0.5.2 (beta)"))
init.config_logging(sys.argv)
init.init(bot).parse_arguments(sys.argv)
bot.logger = logging.getLogger('maximilian-beta')
>>>>>>> 16216f1 (restructure main files)
bot.guildlist = []
bot.prefixes = {}
bot.responses = []
bot.dbinst = common.db(bot)
bot.database = "maximilian_test"
#try to connect to database, if it fails warn
print(f"Attempting to connect to database '{bot.database}' on '{bot.dbip}'...")
try:
    bot.dbinst.connect(bot.database)
    print("Connected to database successfully.")
except pymysql.err.OperationalError:
    bot.logger.critical("Couldn't connect to database, most features won't work. Make sure you passed the right IP and that the database is configured properly.")
#load extensions, starting with required ones
print("Loading required extensions...")
try:
    bot.load_extension("core")
    bot.load_extension("errorhandling")
except:
<<<<<<< HEAD
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
        if self.context.guild is not None:
            responseslist = self.context.bot.dbinst.exec_query(self.context.bot.database, "select * from responses where guild_id = {}".format(self.context.guild.id), False, True)
            responsestring = "A list of custom commands for this server. These don't have help entries. \n"
            if responseslist is not None and str(responseslist)!="()":
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} guilds and {len(bot.users)} users!"))
=======
    bot.logger.critical("Failed to load required extensions.")
    traceback.print_exc()
    quit()
>>>>>>> 16216f1 (restructure main files)

print("Loaded required extensions successfully. Loading other cogs...")
init.init(bot).load_extensions()
    
@bot.event
async def on_message(message):
    if await bot.coreinst.prepare(message):
        await bot.process_commands(message)

@bot.before_invoke
async def before_anything(ctx):
    #before any commands are executed, make sure to set commandprefix (will be removed soon)
    try:
        bot.commandprefix = bot.prefixes[str(ctx.guild.id)]
    except (KeyError, AttributeError):
        bot.commandprefix = "!"

<<<<<<< HEAD
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


@commands.is_owner()
@bot.command(hidden=True)
async def change_status(ctx, statustype, newstatus):
    reset_status.stop()
    await ctx.send("Changing status...")
    if statustype.lower() == "streaming":
        await bot.change_presence(activity=discord.Streaming(name=" my development!", url=newstatus))
    elif statustype.lower() == "listening":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=newstatus))
    elif statustype.lower() == "watching":
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=newstatus))
    elif statustype.lower() == "default":
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
            extensionsreloaded=f"Successfully reloaded all extensions."
        else:
            extensionsreloaded = f"Successfully reloaded {str(len(targetextensions))} extensions."
        reloadmessage = await ctx.send("Fetching latest revision...", delete_after=20)
        try:
            repo = git.Repo(os.getcwd())
            o = repo.remotes.origin
            o.pull()
            await reloadmessage.edit(content="Got latest revision. Reloading extensions...")
            targetextensions = list(bot.extensions.keys())
        except:
            await reloadmessage.edit(content="\U000026a0 Failed to get latest revision. Make sure you've set up the proper SSH keys. Reloading local copies of extensions...")
            extensionsreloaded = f"Reloaded {'1 extension' if len(targetextensions) == 1 else ''}{'all extensions' if len(targetextensions) == 0 else ''}{f'{len(targetextensions)} extensions' if len(targetextensions) > 1 else ''}, but no changes were pulled."
            targetextensions = list(bot.extensions.keys())
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

bot.run(token)
=======
bot.run(token)
>>>>>>> 16216f1 (restructure main files)
