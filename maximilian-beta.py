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
import asyncio

class maximilian():
    def __init__(self):
        print("starting...")
        self.token = common.token().get("betatoken.txt")
        init.config_logging(sys.argv)

    async def start(self):
        self.bot = commands.Bot(command_prefix=core.get_prefix, owner_id=538193752913608704, intents=discord.Intents.all(), activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.5.3 (beta)"))
        init.init(self.bot).parse_arguments(sys.argv)
        self.bot.logger = logging.getLogger('maximilian-beta')
        self.bot.logger.warning(f"Logging started at {datetime.datetime.now()}")
        self.bot.guildlist = []
        self.bot.prefixes = {}
        self.bot.responses = []
        self.bot.start_time = time.time()
        self.bot.dbinst = common.db(self.bot)
        self.bot.database = "maximilian_test"
        #try to connect to database, if it fails warn
        print(f"Attempting to connect to database '{self.bot.database}' on '{self.bot.dbip}'...")
        try:
            self.bot.dbinst.connect(self.bot.database)
            print("Connected to database successfully.")
        except pymysql.err.OperationalError:
            self.bot.logger.critical("Couldn't connect to database, most features won't work. Make sure you passed the right IP and that the database is configured properly.")
        #load extensions, starting with required ones
        print("Loading required extensions...")
        try:
            self.bot.load_extension("cogs.prefixes")
            self.bot.load_extension("core")
            self.bot.load_extension("errorhandling")
        except:
            self.bot.logger.critical("Failed to load required extensions.")
            traceback.print_exc()
            quit()
        print("Loaded required extensions successfully. Loading other cogs...")
        init.init(self.bot).load_extensions()
        await self.bot.start(self.token)

    def cleanup(self):
        self.bot.logger.warning("Shutting down...")
        self.bot.dbinst.dbc.close()
        self.bot.logger.info("Closed database connection.")
        self.bot.logger.warning(f"Logging stopped at {datetime.datetime.now()}.")

try:
    maximilian = maximilian()
    asyncio.run(maximilian.start())
except KeyboardInterrupt:
    maximilian.cleanup()