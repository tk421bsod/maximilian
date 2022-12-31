#main.py: loads core libraries and everything in the cogs folder, then starts Maximilian

import sys

if "--help" in sys.argv:
    print("main.py usage: python3 main.py [OPTIONS]\n")
    print("main.py handles initializing core components, checking requirements, and launching Maximilian.\n")
    print("You can enable/disable features and modify Maximilian's behavior through the use of the following options.\nYou can use more than one option at a time.\n")
    print("Options:")
    print("--enablejsk - Enables Jishaku, an extension used for debugging and code evaluation.")
    print("--noupdate - Skips update check on startup. Takes precendence over --update.")
    print("--update - Updates Maximilian and exits. Implicitly enables --force-update.")
    print("--force-update - Forces update check on startup regardless of the time since last update.")
    print("--noload <extensions> - Skips loading the specified extensions.")
    print("--no-rich - Disables rich text.")
    print("-q, --quiet, -e, --error, -w, --warn, -i, --info, -v, --debug, --verbose - Sets the logging level.")
    print("--ip <address> - Tries to connect to a database at the specified address instead of localhost.")
    print("--help - Shows this message and exits.")
    print("--alt - Prompts for a token to use. Also adds the latest commit hash to the default status.")
    quit()

print("Loading components...")
import asyncio
import datetime
import functools
import json
import logging
import os
import time
import traceback

import discord
import pymysql
from discord.ext import commands
from discord.ext.commands.errors import NoEntryPointError

import common
import core
import db
import settings
from updater import update

if not "--no-rich" in sys.argv:
    try:
        from rich.logging import RichHandler
        from rich.traceback import install
    except ImportError:
        print("Not enabling rich text - import failed")
else:
    print("Not enabling rich text - user requested")

def parse_version(versionstring):
    version = common.Version()
    version.major, version.minor, version.patch = [int(i) for i in versionstring.replace('a','').split('.')[:3]]
    return version

def check_version():
    if parse_version(discord.__version__).major < 2:
        print("\nMaximilian no longer supports discord.py versions below 2.0.")
        print("Either update discord.py (through 'python3 -m pip install discord.py[voice]') or use a Maximilian version below 1.0.")
        print("If you choose to use an old version of Maximilian, you're on your own - those versions lack support from tk421 and compatibility with discord.py 2. Old versions may also stop working without notice.")
        print("See https://gist.github.com/Rapptz/c4324f17a80c94776832430007ad40e6 for more information about this.")
        quit()

def initialize_i18n(bot):
    bot.logger.info('Initializing i18n...')
    if '--language' in sys.argv:
        language = sys.argv[sys.argv.index('--language')+1]
        supported = [i.split('.')[0] for i in os.listdir('languages') if i.endswith('.txt')]
        if language not in supported:
            bot.logger.error(f"That language isn't supported right now. The only supported languages are {supported}")
            sys.exit(25)
    else:
        bot.logger.info("No language specified, defaulting to en")
        language = 'en'
    bot.logger.info(f"Set language to {language}")
    with open(f'languages/{language}', 'r') as data:
        bot.i18n = json.load(data)
    bot.logger.info('Initialized i18n, everything after this message will use the language above')


def config_logging(args):
    """Sets logging level and file to write to"""
    #mapping of argument to logging level and status message
    levelmapping = {"-v":[logging.DEBUG, "Debug logging enabled."], "--debug":[logging.DEBUG, "Debug logging enabled."], "--verbose":[logging.DEBUG, "Debug logging enabled."], "-i":[logging.INFO, "Logging level set to INFO."], "--info":[logging.INFO, "Logging level set to INFO"], "-w":[logging.WARN, "Logging level set to WARN."], "--warn":[logging.WARN, "Logging level set to WARN."], "-e":[logging.ERROR, "Logging level set to ERROR."], "--error":[logging.ERROR, "Logging level set to ERROR."], "-q":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."], "--quiet":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."]}
    try:
        _handlers = [RichHandler(rich_tracebacks=True, tracebacks_suppress=[discord, pymysql])]
    except NameError: #rich wasn't imported, use stdout instead
        _handlers = [logging.StreamHandler(sys.stdout)]
    if os.path.isdir('logs'):
        _handlers.append(logging.FileHandler(f"logs/maximilian-{datetime.date.today()}.log"))
    else:
        print("The 'logs' directory doesn't exist! Not logging to a file.")
    for key, value in levelmapping.items():
        if key not in args:
            pass
        elif key != "-q" and key != "--quiet":
            logging.basicConfig(level=value[0], handlers=_handlers)
            print(value[1])
            logging.getLogger("maximilian.config_logging").warning(f"\nLogging started at {datetime.datetime.now()}")
            return
        else:
            logging.disable()
            print(value[1])
            return
    try:
        RichHandler()
        logging.basicConfig(level=logging.WARN, handlers=_handlers, format="%(message)s", datefmt="[%X]")
    except NameError: #rich not imported
        logging.basicConfig(level=logging.WARN, handlers=_handlers)
    print("No logging level specified, falling back to WARN.")
    logging.getLogger("maximilian.config_logging").warning(f"\nLogging started at {datetime.datetime.now()}")

def parse_arguments(bot, args):
    if len(args) > 1:
        if "--ip" in args:
            try:
                bot.dbip = args[args.index("--ip")+1]
                bot.logger.info(f"Set database IP address to {bot.dbip}.")
            except ValueError:
                bot.logger.warning("You need to specify what ip address you want to use with the database. Since you didn't specify an IP address, I'll fall back to using localhost.")
                bot.dbip = "localhost"
        else:
            bot.logger.warning("No database IP address provided. Falling back to localhost.")
            bot.dbip = "localhost"
        if "--noload" in args:
            bot.noload = [i for i in args[args.index('--noload')+1:] if not i.startswith('-')]
        else:
            bot.noload = []
    else:
        bot.logger.warning("No arguments provided.")
        bot.dbip = "localhost"

async def load_extensions_async(bot):
    """New non-blocking method for loading extensions. Same functionality as load_extensions but compatible with dpy2."""
    if "--enablejsk" in sys.argv:
        asyncio.create_task(bot.load_extension("jishaku"))
        bot.logger.info("Loaded Jishaku.")
    bot.logger.info("Loading modules...")
    extensioncount, errorcount = 0, 0
    print("Loading required modules...")
    #we use a catch-all as we don't want anything going wrong with this
    # noinspection PyBroadException
    try:
        #bot.load_extension("cogs.prefixes")
        await bot.load_extension("core")
        await bot.load_extension("errorhandling")
    except:
        bot.logger.critical("Failed to load required modules.")
        traceback.print_exc()
        quit()
    print("Loading other modules...")
    for each in os.listdir("./cogs"):
        #strip file extension out of filename
        cleanname = each[:-3]
        #ignore anything that isn't a python file
        if each.endswith(".py"):
            #check if we're not loading this extension
            if cleanname in bot.noload or f"cogs.{cleanname}" in bot.noload:
                bot.logger.info(f"Not loading module cogs.{cleanname}.")
                errorcount += 1
                continue
            #actually load the extension
            try:
                await bot.load_extension(f"cogs.{cleanname}")
                extensioncount += 1
                bot.logger.debug(f"Loaded module cogs.{cleanname}.")
            except commands.ExtensionAlreadyLoaded:
                bot.logger.debug(f"{cleanname} is already loaded, skipping")
            except (commands.ExtensionFailed, commands.errors.NoEntryPointError) as error:
                errorcount += 1
                if not hasattr(error, 'original'):
                    #only NoEntryPointError doesn't have original
                    error.original = commands.errors.NoEntryPointError('')
                bot.logger.error(f"{type(error.original).__name__} while loading '{error.name}'! This module won't be loaded.")
                if isinstance(error.original, ModuleNotFoundError) or isinstance(error.original, ImportError):
                    bot.logger.error(f"'{error.original.name}' isn't installed. Consider running 'pip3 install -r requirements_extra.txt.'")
                else:
                    bot.logger.error(traceback.format_exc())
    try:
        bot.prefixes = bot.get_cog('prefixes')
        bot.responses = bot.get_cog('Custom Commands')
        bot.miscinst = bot.get_cog('misc')
        bot.reactionrolesinst = bot.get_cog('reaction roles')
    except: #TODO: pls delet i hate this
        bot.logger.error("Failed to get one or more cogs, some stuff might not work.")
    bot.logger.info(f"loaded {extensioncount} extensions successfully ({errorcount} extension{'s' if errorcount != 1 else ''} not loaded), waiting for ready")
    print("Done loading modules. Finishing startup...")

#wrap the main on_message event in a function for prettiness
async def wrap_event(bot):
    @bot.event
    async def on_message(message):
        if await bot.core.prepare(message):
            await bot.process_commands(message)
    pass

#wrap everything in a function to prevent conflicting event loops
async def run(logger):
    logger.debug("Loading config...")
    config = common.load_config()
    #convert hex color to int
    config['theme_color'] = int(config['theme_color'], 16)
    token = config['token']
    logger.debug("Checking discord.py version...")
    check_version()
    intents = discord.Intents.default()
    intents.members=True
    intents.message_content = True
    logger.debug("Getting version information...")
    if "--alt" in sys.argv:
        token = input("Enter a token to use: \n").strip()
        logger.debug("Getting latest commit hash...")
        commit = common.get_latest_commit()
        logger.debug("Done getting latest commit hash.")
    else:
        commit = ""
    logger.debug("Setting up some stuff")
    bot = commands.Bot(command_prefix=core.get_prefix, owner_id=int(config['owner_id']), intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v1.0.0{f'-{commit}' if commit else ''}"))
    #set up some important stuff
    bot.database = "maximilian" #TODO: remove this
    bot.logger = logger
    bot.common = common
    bot.config = config
    await wrap_event(bot)
    #show version information
    bot.logger.warning(f"Starting maximilian v1.0.0{f'-{commit}' if commit else ''}{' with Jishaku enabled ' if '--enablejsk' in sys.argv else ' '}(running on Python {sys.version_info.major}.{sys.version_info.minor} and discord.py {discord.__version__}) ")
    #parse additional arguments (ip, enablejsk, noload)
    bot.noload = []
    bot.logger.debug("Parsing command line arguments...")
    parse_arguments(bot, sys.argv)
    bot.guildlist = []
    bot.prefixes = {}
    bot.responses = []
    bot.start_time = time.time()
    bot.settings = settings.settings(bot)
    bot.logger.debug("Setting up the database...")
    #try to connect to database, exit if it fails
    try:
        #constructing an instance of db calls db.db.attempt_connection
        bot.db = db.db(bot, config['dbp'])
    except pymysql.err.OperationalError:
        bot.logger.error("Couldn't connect to database. Trying to start it...")
        os.system("bash setup.sh start")
        try:
            bot.db = db.db(bot, config['dbp'])
        except pymysql.err.OperationalError:
            bot.logger.debug(traceback.format_exc())
            bot.logger.critical(f"Couldn't connect to database! \nTry running 'bash setup.sh fix'.")
            sys.exit(96)
    #make sure all tables exist
    try:
        bot.db.ensure_tables()
    except pymysql.OperationalError:
        bot.logger.debug(traceback.format_exc())
        bot.logger.error("Unable to create one or more tables! Does `maximilianbot` not have the CREATE permission?")
    bot.settings.add_category("general", {"debug":"Show additional error info"}, {"debug":None}, {"debug":"manage_guild"})
    #monkeypatch setup_hook
    #TODO: choose your fighter: subclass or context manager
    #if "--with-setup-hook" in sys.argv:
    bot.setup_hook = functools.partial(load_extensions_async, bot)
    print("Logging in...")
    if not "--nologin" in sys.argv:
        await bot.start(token)

print("Starting Maximilian...\nPress Ctrl-C at any time to quit.\n")
print("setting up logging...")
# set a logging level
config_logging(sys.argv)
outer_logger = logging.getLogger(f'maximilian') #different name than inside run for readability
# noinspection PyBroadException
try:
    #run updater
    try:
        if "--noupdate" not in sys.argv:
            update()
        if "--update" in sys.argv:
            print("Updater exited. Exiting.")
            quit()
    except KeyboardInterrupt:
        if "--update" in sys.argv:
            print("Updater interrupted. Exiting.")
            quit()
        print("Updater interrupted. Maximilian will start in a moment.")
        time.sleep(1)
    try:
        #set up rich tracebacks if applicable
        install(suppress=[discord,pymysql])
    except NameError:
        pass
    #then start the event loop
    asyncio.run(run(outer_logger))
except KeyboardInterrupt:
    print("\nKeyboardInterrupt detected. Exiting.")
except KeyError:
    outer_logger.error("The configuration file is missing something. Try pulling changes and re-running setup.sh.")
    outer_logger.info(traceback.format_exc())
except FileNotFoundError:
    outer_logger.error("No configuration file found. Run setup.sh.")
except SystemExit: #raised on quit()
    pass
except:
    #Unsure why this exists, maybe some errors get re-raised here??
    #still appease pycharm
    # noinspection PyBroadException
    try:
        outer_logger.error("Unhandled exception! Exiting.")
        outer_logger.error(traceback.format_exc())
        outer_logger.error("Need more information on Maximilian's state at the time of the error? Run main.py with -i or even -v.")
    except:
        print("Unhandled exception while handling unhandled exception")
        pass

outer_logger.warning("Logging stopped at " + str(datetime.datetime.now()) + ".")
logging.shutdown()
