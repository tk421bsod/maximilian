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
#create instance of 'Token' class, decrypt token
tokeninst = common.token()
token = tokeninst.get("token.txt")
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
    if "--enablejsk" in sys.argv:
        bot.load_extension("jishaku")
        print("Loaded Jishaku.")
    if "--ip" not in sys.argv and "--enablejsk" not in sys.argv:
        bot.logger.warning("Unrecognized argument. If you're trying to pass arguments to python, put them before the filename. Falling back to localhost.")
        bot.dbip = "localhost"
else:
    bot.logger.warning("No arguments provided. Falling back to database on localhost, with Jishaku disabled.")
    bot.dbip = "localhost"
#init important stuff that's used pretty much everywhere
=======
token = common.token().get("token.txt")
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=discord.Intents.all(), activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.5.1 (stable)"))
init.config_logging(sys.argv)
init.init(bot).parse_arguments(sys.argv)
bot.logger = logging.getLogger('maximilian-stable')
>>>>>>> 16216f1 (restructure main files)
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
#load extensions, starting with required ones
print("Loading required extensions...")
try:
    bot.load_extension("core")
    bot.load_extension("errorhandling")
except:
    bot.logger.critical("Failed to load required extensions.")
    traceback.print_exc()
    quit()
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

bot.run(token)
