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
import datetime
import time
import core

print("starting...")
token = common.token().get("betatoken.txt")
bot = commands.Bot(command_prefix=core.get_prefix, owner_id=538193752913608704, intents=discord.Intents.all(), activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.5.3 (beta)"))
init.config_logging(sys.argv)
init.init(bot).parse_arguments(sys.argv)
bot.logger = logging.getLogger('maximilian-beta')
bot.logger.warning(f"Logging started at {datetime.datetime.now()}")
bot.guildlist = []
bot.prefixes = {}
bot.responses = []
bot.start_time = time.time()
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
    bot.load_extension("cogs.prefixes")
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
