#import libraries
print("Loading libraries...")
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
import asyncio

#wrap everything in a function to prevent conflicting event loops
async def run():
    print("starting...")
    if "--beta" in sys.argv:
        filename = "betatoken.txt"
        sys.argv.pop(sys.argv.index("--beta"))
    elif "--dev" in sys.argv:
        filename = "devtoken.txt"
        sys.argv.pop(sys.argv.index("--dev"))
    else:
        filename = "token.txt"
    token = common.token().get(filename)
    init.config_logging(sys.argv)
    intents = discord.Intents.default()
    intents.members=True
    bot = commands.Bot(command_prefix=core.get_prefix, owner_id=538193752913608704, intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.6 (stable)"))
    init.init(bot).parse_arguments(sys.argv)
    bot.logger = logging.getLogger('maximilian-stable')
    bot.logger.warning(f"Maximilian v0.6 ({'Jishaku enabled' if '--enablejsk' in sys.argv else 'Jishaku disabled'}, Python {sys.version}, discord.py {discord.__version__}) ")
    bot.guildlist = []
    bot.prefixes = {}
    bot.responses = []
    bot.start_time = time.time()
    bot.dbinst = common.db(bot)
    bot.database = "maximilian"
    #try to connect to database, if it fails warn
    print(f"Attempting to connect to database '{bot.database}' on '{bot.dbip}'...")
    try:
        bot.dbinst.connect(bot.database)
        print("Connected to database successfully.")
        bot.dbdisabled = False
    except pymysql.err.OperationalError:
        bot.logger.critical("Couldn't connect to database, most features won't work. Make sure you passed the right IP and that the database is configured properly.")
        bot.dbdisabled = True
    #load extensions, starting with required ones
    print("Loading required extensions...")
    try:
        if not bot.dbdisabled:
            bot.load_extension("cogs.prefixes")
        bot.load_extension("core")
        bot.load_extension("errorhandling")
    except:
        bot.logger.critical("Failed to load required extensions.")
        traceback.print_exc()
        quit()
    print("Loaded required extensions successfully. Loading other extensions...")
    init.init(bot).load_extensions()

    @bot.event
    async def on_message(message):
        if await bot.coreinst.prepare(message):
            await bot.process_commands(message)
    
    await bot.start(token)

asyncio.run(run())
