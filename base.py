import asyncio
import os
import sys
import time
import discord
from discord.ext import commands
import common
import startup
import core
import db
import settings

class maximilian(commands.Bot):
    __slots__ = ("commit", "errorcount", "logger", "noload", "extensioncount", "core", "config", "common", "database", "strings", "prefix", "responses", "start_time", "settings", "db")

    def __init__(self, logger):
        logger.debug("Loading config...")
        config = common.load_config()
        logger.debug("Processing config...")
        config = startup.preprocess_config(config)
        token = config['token']
        logger.debug("Checking discord.py version...")
        startup.check_version()
        intents = self.get_intents()
        logger.debug("Getting version information...")
        if "--alt" in sys.argv:
            token = input("Enter a token to use: \n").strip()
            logger.debug("Getting latest commit hash...")
            self.commit = common.get_latest_commit()[0]
            logger.debug("Done getting latest commit hash.")
        else:
            self.commit = ""
        logger.debug("Setting up some stuff")
        super().__init__(command_prefix=core.get_prefix, owner_id=int(config['owner_id']), intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v1.2.0{f'-{self.commit}' if self.commit else ''}"))
        self.database = "maximilian"
        #attempt to pull database name from config!
        try:
            self.database = config["database"]
        except:
            pass
        self.logger = logger
        self.common = common
        self.config = config
        self.noload = []
        self.prefix = {}
        self.responses = []
        self.start_time = time.time()
        logger.debug("Starting the event loop.")

    async def load(self, file):
        #strip file extension out of filename
        cleanname = file[:-3]
        #ignore anything that isn't a python file
        if file.endswith(".py"):
            #check if we're not loading this extension
            if cleanname in self.noload or f"cogs.{cleanname}" in self.noload:
                self.logger.info(f"Not loading module cogs.{cleanname}.")
                self.errorcount += 1
                return
            #actually load the extension
            try:
                await self.load_extension(f"cogs.{cleanname}")
                self.extensioncount += 1
                self.logger.debug(f"Loaded module cogs.{cleanname}!")
            except commands.ExtensionAlreadyLoaded:
                self.logger.debug(f"{cleanname} is already loaded, skipping")
            except (commands.ExtensionFailed, commands.errors.NoEntryPointError) as error:
                self.errorcount += 1
                if not hasattr(error, 'original'):
                    #only NoEntryPointError doesn't have original
                    error.original = commands.errors.NoEntryPointError('')
                self.logger.error(f"{type(error.original).__name__} while loading '{error.name}'! This module won't be loaded.")
                if isinstance(error.original, ModuleNotFoundError) or isinstance(error.original, ImportError):
                    self.logger.error(f"'{error.original.name}' isn't installed. Consider running 'pip3 install -r requirements_extra.txt.'")
                else:
                    self.logger.error(traceback.format_exc())

    async def load_jishaku(self):
        if "--enablejsk" in sys.argv:
            await self.load_extension("jishaku")
            self.logger.info("Loaded Jishaku!")
            if not self.config['jsk_used']:
                self.logger.warning("Hello! It looks like you've enabled Jishaku for the first time. It's an invaluable tool for debugging and development, but can be quite dangerous in the wrong hands.")
                self.logger.warning(f"If your account (or the account with the ID {self.owner_id}) gets compromised, the attacker will have direct access to your computer.")
                self.logger.warning("Don't want to use Jishaku? Stop Maximilian now with CTRL-C and run main.py WITHOUT --enablejsk.")
                self.logger.warning("If you keep using Jishaku, I recommend that you enable 2FA and/or run Maximilian in a VM.")
                self.logger.warning("Startup will continue in 10 seconds.")
                time.sleep(10) # block here so we don't do anything else (e.g login, cache filling) in the meantime

    async def load_required(self):
        #we use a catch-all as we don't want anything going wrong with this
        # noinspection PyBroadException
        try:
            await self.load_extension("core")
            await self.load_extension("errorhandling")
        except:
            self.logger.critical("Failed to load required modules.")
            traceback.print_exc()
            quit()

    async def load_extensions_async(self):
        """Loads modules during startup."""
        self.logger.info("Loading modules...")
        await self.load_jishaku()
        self.extensioncount, self.errorcount = 0, 0
        print("Loading required modules...")
        await self.load_required()
        print("Loading other modules...")
        for each in os.listdir("./cogs"):
            await self.load(each)
        self.logger.info(f"Loaded {self.extensioncount} modules successfully. {self.errorcount} module{'s' if self.errorcount != 1 else ''} not loaded.")
        print("Done loading modules. Finishing startup...")

    #wrap the main on_message event in a function for prettiness
    async def wrap_event(self):
        @self.event
        async def on_message(message):
            if await self.core.prepare(message):
                await self.process_commands(message)
        pass

    def get_intents(self):
        intents = discord.Intents.none()
        intents.reactions = True; intents.members = True; intents.guilds = True; intents.message_content = True; intents.messages = True; intents.voice_states = True;
        return intents

    def setup_db(self):
        #try to connect to database, exit if it fails
        self.db = startup.initialize_db(self, self.config)
        #make sure all tables exist
        try:
            self.db.ensure_tables()
        except pymysql.OperationalError:
            self.logger.debug(traceback.format_exc())
            self.logger.error("Unable to create one or more tables! Does `maximilianbot` not have the CREATE permission?")

    #wrap everything in a function to prevent conflicting event loops
    async def run(self):
        self.logger.debug("Async context entered.")
        self.strings = await startup.load_strings(self.logger)
        await self.wrap_event()
        #show version information
        self.logger.warning(f"Starting Maximilian v1.2.0{f'-{self.commit}' if self.commit else ''}{' with Jishaku enabled ' if '--enablejsk' in sys.argv else ' '}(running on Python {sys.version_info.major}.{sys.version_info.minor} and discord.py {discord.__version__}) ")
        #parse additional arguments (ip, enablejsk, noload)
        self.logger.debug("Parsing command line arguments...")
        startup.parse_arguments(self, sys.argv)
        self.setup_db()
        #initialize settings api
        self.settings = settings.settings(self)
        self.settings.add_category("general", {"debug":"Show additional error info"}, {"debug":None}, {"debug":"manage_guild"})
        print("Logging in...")
        if not "--nologin" in sys.argv:
            asyncio.create_task(self.load_extensions_async())
            self.logger.debug("load_extensions_async has been scheduled.")
            await self.start(self.config["token"])

if __name__ == "__main__":
    print("Sorry, this file cannot be run directly. Run main.py instead.")
