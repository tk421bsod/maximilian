import asyncio
import os
import sys
import time
import traceback

import aiomysql
import aiohttp
import discord
from discord.ext import commands

import common
import core
import settings
import startup


class maximilian(commands.Bot):
    __slots__ = ("PYTHON_MINOR_VERSION", "VER", "IS_DEBUG", "blocklist", "config", "common", "commit", "confirmation", "core", "database", "db", "deletion_request", "DeletionRequestAlreadyActive", "language", "logger", "noload", "prefix", "responses", "strings", "start_time", "settings")

    def __init__(self, logger, VER):
        #Now that we've checked basic requirements and ran the updater, we can
        #load our config data...
        logger.debug("Loading config...")
        config = common.load_config()
        logger.debug("Processing config...")
        config = startup.preprocess_config(config)
        if not config['dependency_change_warning']:
            print("\n")
            logger.warning("Hi there.")
            logger.warning("Some dependencies have changed since you last started Maximilian.")
            logger.warning("Run 'pip3 install -U -r requirements.txt' to update them.")
            os._exit(10)
        token = config['token']
        #check discord.py version...
        #TODO: Consider moving this to main.py next to Python version checks
        logger.debug("Checking discord.py version...")
        startup.check_version()
        #get our Intents...
        intents = self.get_intents()
        if "--alt" in sys.argv:
            token = input("Enter a token to use: \n").strip()
            logger.debug("Getting latest commit hash...")
            self.commit = common.get_latest_commit()[0]
            logger.debug("Done getting latest commit hash.")
        else:
            self.commit = ""
        #set up some attributes we'll need soon...
        logger.debug("Setting up some stuff")
        super().__init__(command_prefix=core.get_prefix, owner_id=int(config['owner_id']), intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v{VER}{f'-{self.commit}' if self.commit else ''}"))
        self.VER = VER
        self.database = "maximilian"
        try:
            self.database = config["database"]
            logger.warning("Sourced database name from config.")
            logger.warning(f"Using database '{self.database}'.")
        except:
            logger.warning("No database name found in config.")
        self.logger = logger
        self.common = common 
        self.config = config 
        self.noload = [] #list of modules for load_extensions_async to skip, set by parse_arguments
        self.prefix = {} #map of prefix to server id. cogs/prefixes.py hooks into this to allow for server-specific prefixes
        self.responses = [] #custom commands list. TODO: make this less baked in
        self.start_time = time.time()
        #parse additional arguments (ip, enablejsk, noload)
        self.logger.debug("Parsing command line arguments...")
        startup.parse_arguments(self, sys.argv)
        logger.debug("Starting the event loop.")

    async def load(self, file):
        #strip file extension out of filename
        cleanname = file[:-3]
        #ignore anything that isn't a python file
        #check if we're not loading this extension
        if cleanname in self.noload or f"cogs.{cleanname}" in self.noload:
            self.logger.info(f"Not loading module cogs.{cleanname}.")
            return
        #actually load the extension
        try:
            await self.load_extension(f"cogs.{cleanname}")
            self.logger.info(f"Loaded module cogs.{cleanname}!")
        except commands.ExtensionAlreadyLoaded:
            self.logger.info(f"{cleanname} is already loaded, skipping")
        except (commands.ExtensionFailed, commands.errors.NoEntryPointError) as error:
            if not hasattr(error, 'original'):
                #only NoEntryPointError doesn't have original
                error.original = commands.errors.NoEntryPointError('')
            self.logger.error(f"{type(error.original).__name__} while loading '{error.name}'! This module won't be loaded.")
            if isinstance(error.original, ModuleNotFoundError) or isinstance(error.original, ImportError):
                self.logger.error(f"'{error.original.name}' isn't installed. Consider running 'pip3 install -U -r requirements.txt.'")
            else:
                self.logger.error(traceback.format_exc())
                await self.try_exit()
        except Exception as e:
            traceback.print_exc()
            await self.try_exit()

    async def try_exit(self):
        if not common.get_value(self.config, 'exit_on_error', False):
            return
        self.logger.warning("Extension error occurred, exiting")
        await sys.exit(4)

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
        print("Loading required modules...")
        await self.load_required()
        #Get a snapshot of our current extension state.
        #We'll compare it to our state after load to figure out how many were loaded.
        exts = self.extensions.copy()
        print("Loading other modules...")
        files = [filename for filename in os.listdir("./cogs") if filename.endswith(".py")]
        if "--experimental-concurrency" in sys.argv:
            await common.run_now(*[self.load(file) for file in files])
        else:
            for each in files:
                await self.load(each)
        total = len([f"{i}" for i in list(self.extensions.keys()) if i not in list(exts.keys())])
        diff = (len(files))-total
        self.logger.info(f"Loaded {total} modules successfully. {diff} module{'s' if diff != 1 else ''} not loaded.")
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

    async def setup_db(self):
        #try to connect to database, exit if it fails
        self.db = await startup.initialize_db(self, self.config)
        #make sure all tables exist
        try:
            await self.db.ensure_tables()
        except aiomysql.OperationalError:
            self.logger.debug(traceback.format_exc())
            self.logger.error("Unable to create one or more tables! Does `maximilianbot` not have the CREATE permission?")
    
    async def init_general_settings(self):
        #maybe we could make add_category itself a coro?
        self.settings.add_category("general", {"debug":"Show additional error info"}, {"debug":None}, {"debug":"manage_guild"})

    async def start(self, *args, **kwargs):
        #Create our own ClientSession to prevent "Unclosed session" warnings at shutdown
        async with aiohttp.ClientSession() as self.session:
            await super().start(*args, **kwargs)

    async def run(self):
        self.logger.debug("Async context entered.")
        if "--experimental-concurrency" in sys.argv:
            self.logger.warning("Experimental concurrency features enabled.")
        #now that we're in an async context, we can show version information...
        self.logger.warning(f"Starting Maximilian v{self.VER}{f'-{self.commit}' if self.commit else ''}{' with Jishaku enabled ' if '--enablejsk' in sys.argv else ' '}(running on Python {sys.version_info.major}.{self.PYTHON_MINOR_VERSION} and discord.py {discord.__version__}) ")
        #initialize our translation layer...
        self.language = await startup.get_language(self.logger, self.config, exit = True)
        self.strings = await startup.load_strings(self.language, self.logger, self.config)
        #register our on_message event...
        #TODO: Consider moving this to core
        await self.wrap_event()
        #initialize the database...
        await self.setup_db()
        #and initialize the settings api
        self.settings = settings.settings(self)
        #If we're actually logging in, schedule some tasks for after login starts...
        #TODO: Fix RuntimeErrors if exiting before Bot.start runs, e.g "Exception ignored in: <function Connection.__del__ at 0x7ddc7b348220>"
        if not "--no-login" in sys.argv:
            #TODO: Eliminate potential for race conditions here:
            #Either load_extensions_async or init_general_settings could run before Bot.start runs,
            #which can cause a RuntimeError if an extension's cache fill method starts early.
            #setup_hook may work for this, however it runs after login...
            #extension load is time-consuming and any commands received during that window of time will fail
            asyncio.create_task(self.load_extensions_async())
            self.logger.debug("load_extensions_async has been scheduled.")
            asyncio.create_task(self.init_general_settings()) 
            self.logger.debug("init_general_settings has been scheduled.")
            print("Logging in...")
            await self.start(self.config["token"])
        else:
            self.logger.warn("Invoked with --nologin, exiting and not calling start()")
            return
        self.logger.warn("start() returned without raising an exception!!")
        self.logger.warn("Please let tk421 know about this.")

if __name__ == "__main__":
    print("Sorry, this file cannot be run directly. Run main.py instead.")
