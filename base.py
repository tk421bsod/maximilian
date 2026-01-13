"""The bot base. Performs initialization of key components, loads extensions, and calls Bot.start.

Implements a subclass of discord.ext.commands.Bot with some custom attributes.
main.py creates an instance of this subclass and calls its run() method.

Also implements a subclass of discord.ext.commands.Context to allow for pagination across all messages, allowed mentions, and perhaps other things in the future.
"""

import asyncio
import importlib
import os
import sys
import time
import traceback

import aiohttp
import aiomysql
import discord
from discord.ext import commands

import common
import core
from constants import GlobalConstants
import helpcommand
import logging
import settings
import startup
import versioning

class CustomContext(commands.Context):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def _get_pagination_state(self, caller):
        try:
            id = self.guild.id if self.guild else 0
            await self.bot.settings.general.wait_ready()
            ret = self.bot.settings.general.pagination.enabled(id)
            if ret:
                if caller == "send_paginated" or caller == "send_paginated_embed":
                    #Just return False to skip pagination.
                    logging.getLogger(self.bot.constants.ROOT_LOGGER_NAME).debug("Skipping CustomContext pagination.")
                    return False
            return ret
        except AttributeError: #Category/Setting doesn't exist for some reason? Use the usual default behavior (disabled)
            return False

    async def _get_allowed_mentions_state(self, **kwargs):
        #allowed_mentions passed to send() always overrides the setting.
        if common.get_value(kwargs, "allowed_mentions"):
            return kwargs.pop("allowed_mentions")
        else:
            try:
                id = self.guild.id if self.guild else 0
                await self.bot.settings.general.wait_ready()
                if self.bot.settings.general.mentions.enabled(id):
                    return discord.AllowedMentions(everyone=False)
                else:
                    return discord.AllowedMentions(everyone=False, users=False, roles=False)
            except AttributeError:
                pass
        #If we haven't returned yet, just assume the setting is disabled.
        return discord.AllowedMentions(everyone=False, users=False, roles=False)

    async def send(self, *args, **kwargs):
        to_send = common.get_value(args, 0)
        if not to_send:
            to_send = kwargs.get("embed")
        #Get the name of our caller to prevent an infinite loop if we were called from send_paginated.
        caller = common.get_caller_name()
        logging.getLogger(self.bot.constants.ROOT_LOGGER_NAME).debug(f"CustomContext.send called from '{caller}'")
        pagination_enabled = await self._get_pagination_state(caller)
        #Don't try to paginate if we don't have anything to paginate.
        if to_send and pagination_enabled:
            #Remove the embed kwarg so we can pass everything else to send_paginated.
            #This lets files, views, etc work properly.
            if isinstance(to_send, discord.Embed):
                kwargs.pop("embed")
            return await self.bot.core.send_paginated(to_send, self, prefix="", suffix="", **kwargs)
        allowed_mentions = await self._get_allowed_mentions_state(**kwargs)
        return await super().send(*args, **kwargs, allowed_mentions=allowed_mentions)

class maximilian(commands.Bot):
    __slots__ = ("blocklist", "config", "constants", "common", "commit", "confirmation", "core", "database", "db", "deletion_request", "DeletionRequestAlreadyActive", "init_finished", "required_intents", "language", "logger", "noload", "prefix", "responses", "strings", "start_time", "settings", "tables")

    def __init__(self, config):
        self.constants = GlobalConstants
        self.common = common
        self.config = config
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        #Now that we've checked basic requirements and ran the updater, we can
        token = self.config['token']
        #check discord.py version...
        #TODO: Consider moving this to main.py next to Python version checks
        logger.debug("Checking discord.py version...")
        startup.check_version()
        #Is this a prerelease version? Add the latest commit to the status.
        if "prerelease" in self.constants.VERSION:
            self.commit = common.get_latest_commit()
        if "--alt" in sys.argv:
            token = input("Enter a token to use: \n").strip()
            self.commit = common.get_latest_commit()
        else:
            try:
                self.commit
            except AttributeError:
                self.commit = ""
        #Set our global logger.
        #TODO: Move away from doing this, it is discouraged. Calling getLogger('maximilian') is the recommended usage.
        self.logger = logger
        self.noload = [] #list of modules for load_extensions_async to skip. Set by parse_arguments
        self.dbip = None
        self.get_database_ip()
        logger.debug("Parsing command line arguments...")
        startup.parse_arguments(self, sys.argv)
        self.tables = {'mute_roles':'guild_id bigint, role_id bigint', 'reminders':'user_id bigint, channel_id bigint, reminder_time datetime, now datetime, reminder_text text, uuid text', 'prefixes':'guild_id bigint, prefix text', 'responses':'guild_id bigint, response_trigger varchar(255), response_text text, constraint pk_responses primary key (guild_id, response_trigger)', 'config':'guild_id bigint, category varchar(255), setting varchar(255), enabled tinyint, constraint pk_config primary key (guild_id, setting, category)', 'blocked':'user_id bigint', 'roles':'guild_id bigint, role_id bigint, message_id bigint, emoji text', 'todo':'user_id bigint, entry text, timestamp datetime', 'active_requests':'id bigint', 'version':'num tinyint not null, rollback_commands text'}
        self.required_intents = {"reactions":True, "members":True, "guilds":True, "message_content":True, "messages":True}
        logger.info("Checking module requirements...")
        self.get_extension_requirements()
        #get our Intents...
        intents = self.get_intents()
        #Now that we're mostly set up, we can fully initialize.
        #TODO: Change default allowed_mentions policy to reflect default behavior declared in CustomContext...
        #We may be able to then remove defaults from CustomContext.
        super().__init__(allowed_mentions=discord.AllowedMentions(everyone=False), command_prefix=core.get_prefix, owner_id=int(config['owner_id']), intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v{self.constants.VERSION}{f'-{self.commit}' if self.commit else ''}"))
        #Initialize some needed attributes.
        self._initialize_attrs()
        startup.show_2_0_first_run_message(config)
        logger.debug("Starting the event loop.")

    def get_database_ip(self):
        #Pull our database IP address from config.
        dbip = common.get_value(self.config, "dbip")
        if dbip:
            logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
            logger.debug("Sourcing database IP address from config.")
            logger.debug(f"Setting database IP address to {dbip}")
            self.dbip = dbip

    def _initialize_attrs(self):
        self.help_command = helpcommand.HelpCommand(verify_checks=False)
        self.init_finished = False
        self.prefix = {} #map of prefix to server id. cogs/prefixes.py hooks into this to allow for server-specific prefixes
        self.responses = [] #custom commands list. TODO: make this less baked in
        self.start_time = time.time()

    def set_database_name(self):
        self.database = "maximilian"
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        try:
            self.database = self.config["database"]
            logger.warning("Sourced database name from config.")
            logger.warning(f"Using database '{self.database}'.")
        except:
            logger.warning("No database name found in config.")

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    def extension_requires_intents(self, extension, intents):
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        for intent in intents:
            logger.debug(f"Module '{extension}' requires Intent '{intent}'")
            self.required_intents[intent] = True
            if intent in ["members", "message_content", "presences"]:
                logger.warning(f"Module '{extension}' is requesting privileged Intent '{intent}'!")
                logger.warning("If these are not enabled in the Developer Portal, startup will fail.")

    def extension_requires_tables(self, extension, tables):
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        if not isinstance(tables, dict):
            logger.warning("Modules must provide table schemas as a dict!")
        for table, schema in tables.items():
            if table not in list(self.tables.keys()):
                logger.debug(f"Module '{extension}' requires table '{table}'. Schema is '{schema}'")
                self.tables[table] = schema

    def parse_extension_requirements(self, extension, data):
        """Interpret requirements for an extension and change stuff as needed."""
        if not data:
            return
        #Data contains values that we add to our Bot instance.
        for data_type, value in data.items():
            if data_type == "intents":
                self.extension_requires_intents(extension, value)
            elif data_type == "tables":
                self.extension_requires_tables(extension, value)

    def get_extension_requirements(self):
        """Obtain and process extension requirements."""
        files = [f"cogs.{filename}" for filename in os.listdir("./cogs") if filename.endswith(".py")]
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        #We have a couple extensions in this dir, add those too.
        files.append("core.py"); files.append("errorhandling.py");
        for file in files:
            try:
                cleanname = file[:-3]
                if cleanname in self.noload or f"{cleanname}" in self.noload:
                    continue
                ext = importlib.import_module(cleanname)
                ret = ext.requirements()
                if not ret:
                    logger.info(f"{cleanname}.requirements() returned nothing!")
                    continue
                logger.debug(f"{cleanname}.requirements() returned '{ret}'")
                self.parse_extension_requirements(cleanname, ret)
            except ImportError:
                pass
            except AttributeError:
                logger.info(f"Module '{cleanname}' does not have a 'requirements' method!")

    async def load(self, file):
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        #strip file extension out of filename
        cleanname = file[:-3]
        #check if we're not loading this extension
        if cleanname in self.noload or f"cogs.{cleanname}" in self.noload:
            logger.info(f"Not loading module cogs.{cleanname}.")
            return
        #actually load the extension
        try:
            await self.load_extension(f"cogs.{cleanname}")
            logger.info(f"Loaded module cogs.{cleanname}!")
        except commands.ExtensionAlreadyLoaded:
            logger.info(f"{cleanname} is already loaded, skipping")
        except (commands.ExtensionFailed, commands.errors.NoEntryPointError) as error:
            if not hasattr(error, 'original'):
                #only NoEntryPointError doesn't have original
                error.original = commands.errors.NoEntryPointError('')
            logger.error(f"{type(error.original).__name__} while loading '{error.name}'! This module won't be loaded.")
            if isinstance(error.original, ModuleNotFoundError) or isinstance(error.original, ImportError):
                logger.error(f"'{error.original.name}' isn't installed. Consider running 'pip3 install -U -r requirements.txt.'")
            else:
                logger.error(traceback.format_exc())
                await self.try_exit()
        except Exception as e:
            traceback.print_exc()
            await self.try_exit()

    async def try_exit(self):
        if not common.get_value(self.config, 'exit_on_error', False):
            return
        logging.getLogger(self.constants.ROOT_LOGGER_NAME).warning("Extension error occurred, exiting")
        await sys.exit(4)

    async def load_jishaku(self):
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        if "--enablejsk" in sys.argv:
            await self.load_extension("jishaku")
            self.logger.info("Loaded Jishaku!")
            if not self.config['jsk_used']:
                logger.warning("Hello! It looks like you've enabled Jishaku for the first time. It's an invaluable tool for debugging and development but can be quite dangerous in the wrong hands.")
                logger.warning(f"If your Discord account (or the account with the ID {self.owner_id}) gets compromised, the attacker will have direct access to your computer through Jishaku.")
                logger.warning("If you haven't already, consider enabling 2FA or other account security measures.")
                logger.warning("Startup will continue in 10 seconds.")
                time.sleep(10)  # block here so we don't do anything else (e.g login, cache filling) in the meantime

    async def load_required(self):
        try:
            for module in self.constants.REQUIRED_MODULES:
                await self.load_extension(module)
        except:
            logging.getLogger(self.constants.ROOT_LOGGER_NAME).critical("Failed to load required modules.")
            traceback.print_exc()
            quit()

    async def load_extensions_async(self):
        """Loads modules during startup."""
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        logger.info("Loading modules...")
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
        logger.info(f"Loaded {total} modules successfully. {diff} module{'s' if diff != 1 else ''} not loaded.")
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
        #Unpack our dict of Intents into kwargs, and construct a discord.Intents containing the flags we want with it.
        intents = discord.Intents(**self.required_intents)
        return intents

    async def setup_db(self):
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        #Initialize the database.
        self.db = await startup.initialize_db(self, self.config)
        #Then make sure all tables exist
        try:
            await self.db.ensure_tables()
        except aiomysql.OperationalError:
            logger.debug(traceback.format_exc())
            logger.error("Unable to create one or more tables! Does `maximilianbot` not have the CREATE permission?")
        #And check the database version
        if not "--skip-versioning" in sys.argv:
            await versioning.eval_db_version(self.db)
        else:
            logger.warning("Skipping database version check.")

    async def init_general_settings(self):
        #maybe we could make add_category itself a coro?
        self.settings.add_category("general", {"debug":"Show additional error info", "pagination":"Experimental pagination features", "mentions":"User/role mentions in messages sent by the bot"}, {"debug":None, "pagination":None, "mentions":None}, {"debug":"manage_guild", "pagination":None, "mentions":"manage_guild"})

    async def start(self, *args, **kwargs):
        #Create our own ClientSession to prevent "Unclosed session" warnings at shutdown
        async with aiohttp.ClientSession() as self.session:
            await super().start(*args, **kwargs)

    async def run(self):
        logger = logging.getLogger(self.constants.ROOT_LOGGER_NAME)
        logger.debug("Async context entered.")
        if "--experimental-concurrency" in sys.argv:
            logger.warning("Experimental concurrency features enabled.")
        #now that we're in an async context, we can show version information...
        logger.warning(f"Starting Maximilian v{self.constants.VERSION}{f'-{self.commit}' if self.commit else ''}{' with Jishaku enabled ' if '--enablejsk' in sys.argv else ' '}(running on Python {sys.version_info.major}.{self.PYTHON_MINOR_VERSION} and discord.py {discord.__version__}) ")
        #initialize the translation system...
        self.language = await startup.get_language(self.config, exit=True)
        logger.info(f"Set language to {self.language}")
        self.strings = await startup.load_strings(self.language)
        #register our on_message event...
        #TODO: Consider moving this to core
        await self.wrap_event()
        #prepare for database initialization...
        self.set_database_name()
        #initialize the database...
        await self.setup_db()
        #and initialize settings
        self.settings = settings.settings(self)
        #If we're actually logging in, schedule some tasks for after login starts...
        #TODO: Fix RuntimeErrors if exiting before Bot.start runs, e.g "Exception ignored in: <function Connection.__del__ at 0x7ddc7b348220>"
        if not "--no-login" in sys.argv:
            #Remove sensitive data from 'config' and 'db'.
            logger.debug("Removing sensitive data from global objects.")
            token = self.config['token']
            del self.config['token'], self.config['dbp'], self.db.p, self.db.ip
            logger.debug("Done.")
            #TODO: Eliminate potential for race conditions here:
            #Either load_extensions_async or init_general_settings could run before Bot.start runs,
            #which can cause a RuntimeError if an extension's cache fill method starts early.
            asyncio.create_task(self.load_extensions_async())
            asyncio.create_task(self.init_general_settings()) 
            print("Logging in...")
            await self.start(token)
        else:
            logger.warning("Invoked with --nologin, exiting and not calling start()")
            return
        logger.warning("start() returned without raising an exception!!")
        logger.warning("Please let tk421 know about this.")

if __name__ == "__main__":
    common.show_not_executable()
