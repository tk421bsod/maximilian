"""The bot base. Performs initialization of key components, loads extensions, and calls Bot.start.

Implements a subclass of discord.ext.commands.Bot with some custom attributes.
main.py creates an instance of this subclass and calls its run() method.

Also implements a subclass of discord.ext.commands.Context to allow for pagination across all messages and perhaps other things in the future.
"""

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
import helpcommand
import settings
import startup

class CustomContext(commands.Context):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def send(self, *args, **kwargs):
        skip_pagination = False
        to_send = common.get_value(args, 0)
        if not to_send:
            to_send = kwargs.get("embed")
        id = self.guild.id if self.guild else 0
        try:
            await self.bot.settings.general.wait_ready()
            ret = self.bot.settings.general.pagination.enabled(id)
            if ret:
                #Get the name of our caller to prevent an infinite loop if we were called from send_paginated.
                caller = common.get_caller_name()
                if caller == "send_paginated" or caller == "send_paginated_embed":
                    skip_pagination = True
        except AttributeError:
            ret = False
        if common.get_value(kwargs, "allowed_mentions"):
            allowed_mentions = kwargs.pop("allowed_mentions")
        else:
            if self.bot.settings.general.mentions.enabled(id):
                allowed_mentions = discord.AllowedMentions(everyone=False)
            else:
                allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False)
        if to_send and ret and not skip_pagination:
            return await self.bot.core.send_paginated(to_send, self, prefix="", suffix="")
        return await super().send(*args, **kwargs, allowed_mentions=allowed_mentions)

class maximilian(commands.Bot):
    __slots__ = ("PYTHON_MINOR_VERSION", "VER", "IS_DEBUG", "blocklist", "config", "common", "commit", "confirmation", "core", "database", "db", "deletion_request", "DeletionRequestAlreadyActive", "init_finished", "language", "logger", "noload", "prefix", "responses", "strings", "start_time", "settings")

    def __init__(self, logger, VER):
        #Now that we've checked basic requirements and ran the updater, we can
        #load our config data...
        logger.debug("Loading config...")
        config = common.load_config()
        logger.debug("Processing config...")
        config = startup.preprocess_config(config)
        token = config['token']
        #check discord.py version...
        #TODO: Consider moving this to main.py next to Python version checks
        logger.debug("Checking discord.py version...")
        startup.check_version()
        #get our Intents...
        intents = self.get_intents()
        #Is this a prerelease version? Add the latest commit to the status.
        if "prerelease" in VER:
            self.commit = common.get_latest_commit()
        if "--alt" in sys.argv:
            token = input("Enter a token to use: \n").strip()
            self.commit = common.get_latest_commit()
        else:
            try:
                self.commit
            except AttributeError:
                self.commit = ""
        #set up some attributes we'll need soon...
        logger.debug("Setting up some stuff")
        super().__init__(allowed_mentions=discord.AllowedMentions(everyone=False), command_prefix=core.get_prefix, owner_id=int(config['owner_id']), intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v{VER}{f'-{self.commit}' if self.commit else ''}"))
        self.VER = VER
        self.init_finished = False
        self.logger = logger
        self.common = common 
        self.config = config
        self.noload = [] #list of modules for load_extensions_async to skip, set by parse_arguments
        self.prefix = {} #map of prefix to server id. cogs/prefixes.py hooks into this to allow for server-specific prefixes
        self.responses = [] #custom commands list. TODO: make this less baked in
        self.start_time = time.time()
        self.help_command = helpcommand.HelpCommand(verify_checks=False)
        self.set_database_name()
        startup.show_2_0_first_run_message(config)
        #parse additional arguments (ip, enablejsk, noload)
        self.logger.debug("Parsing command line arguments...")
        startup.parse_arguments(self, sys.argv)
        logger.debug("Starting the event loop.")

    def set_database_name(self):
        self.database = "maximilian"
        try:
            self.database = self.config["database"]
            self.logger.warning("Sourced database name from config.")
            self.logger.warning(f"Using database '{self.database}'.")
        except:
            self.logger.warning("No database name found in config.")

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

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
                time.sleep(10)  # block here so we don't do anything else (e.g login, cache filling) in the meantime

    async def load_required(self):
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
        #We compare it to our state after load to figure out how many were loaded.
        exts = self.extensions.copy()
        print("Loading other modules...")
        files = [filename for filename in os.listdir("./cogs") if filename.endswith(".py")]
        if "--experimental-concurrency" in sys.argv:
            #Construct a list of coros to run.
            to_run = []
            for file in files:
                to_run.append(self.load(file))
            #Then run them.
            await common.run_now(*to_run)
        else:
            for each in files:
                await self.load(each)
        total = len([i for i in list(self.extensions) if i not in list(exts)])
        diff = (len(files))-total
        self.logger.info(f"Loaded {total} modules successfully. {diff} module{'s' if diff != 1 else ''} not loaded.")
        print("Done loading modules. Finishing startup...")

    #wrap the main on_message event in a function for prettiness
    async def wrap_event(self):
        @self.event
        async def on_message(message):
            if await self.core.prepare(message):
                ctx = await self.get_context(message)
                await self.invoke(ctx)
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
        self.settings.add_category("general", {"debug":"Show additional error info", "pagination":"Experimental pagination features", "mentions":"User/role mentions in messages sent by the bot"}, {"debug":None, "pagination":None, "mentions":None}, {"debug":"manage_guild", "pagination":None, "mentions":"manage_guild"})

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
        self.logger.info(f"Set language to {self.language}")
        self.strings = await startup.load_strings(self.language, self.logger)
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
            #Remove sensitive data from 'config' and 'db'.
            self.logger.debug("Removing sensitive data from global objects.")
            token = self.config['token']
            del self.config['token'], self.config['dbp'], self.db.p, self.db.ip
            self.logger.debug("Done.")
            #TODO: Eliminate potential for race conditions here:
            #Either load_extensions_async or init_general_settings could run before Bot.start runs,
            #which can cause a RuntimeError if an extension's cache fill method starts early.
            #setup_hook may work for this, however it runs after login...
            #extension load is time-consuming and
            #any commands received during that window of time will fail
            asyncio.create_task(self.load_extensions_async())
            self.logger.debug("load_extensions_async has been scheduled.")
            asyncio.create_task(self.init_general_settings()) 
            self.logger.debug("init_general_settings has been scheduled.")
            print("Logging in...")
            await self.start(token)
        else:
            self.logger.warn("Invoked with --nologin, exiting and not calling start()")
            return
        self.logger.warn("start() returned without raising an exception!!")
        self.logger.warn("Please let tk421 know about this.")

if __name__ == "__main__":
    print("Sorry, this file cannot be run directly. Run main.py instead.")
