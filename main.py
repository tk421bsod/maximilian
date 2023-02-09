#main.py: loads core libraries and everything in the cogs folder, then starts Maximilian
import sys

if __name__ != "__main__":
    print("It looks like you're trying to import main.py as a module.")
    print("Please don't do that. Some code here relies on being ran directly through a command such as python3 main.py.")
    print("Need to access some Maximilian API? Just import the right file. Read HOSTING.md for an overview.")
    print("If you have a legitimate use case for this, I'd like to hear about it -- send me a DM at tk421#2016 on Discord.")
    print("If you decide to remove the following call to quit() and continue, any weird behavior is on you, not me.")
    print("Maximilian will now attempt to exit.")
    quit()

if sys.version_info.major == 3 and sys.version_info.minor < 8:
    print("Hi there. It looks like you're trying to run maximilian with an older version of Python 3.")
    print("Maximilian cannot run on Python versions older than 3.8.")
    print("You'll need to upgrade Python to continue.")
    quit()


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

try:
    import asyncio
    import datetime
    import functools
    import json
    import logging
    import os
    import time
    import traceback
    import subprocess

    import discord
    import pymysql
    from discord.ext import commands
    from discord.ext.commands.errors import NoEntryPointError

    import common
    import core
    import db
    import settings
    import startup
    from updater import update
except ImportError as e:
    print("Maximilian cannot start because a required component failed to load.\nTry running 'pip3 install -U -r requirements.txt' and ensuring Maximilian is using the correct Python installation.\nHere's some more error info:")
    print(e)
    sys.exit(2)

if not "--no-rich" in sys.argv:
    try:
        from rich.logging import RichHandler
        from rich.traceback import install
    except ImportError:
        print("Not enabling rich text - import failed")
else:
    print("Not enabling rich text - user requested")

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
            logging.getLogger("maximilian.config_logging").warning(f"Logging started at {datetime.datetime.now()}")
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
    logging.getLogger("maximilian.config_logging").warning(f"Logging started at {datetime.datetime.now()}")

async def load(bot, file):
    #strip file extension out of filename
    cleanname = file[:-3]
    #ignore anything that isn't a python file
    if file.endswith(".py"):
        #check if we're not loading this extension
        if cleanname in bot.noload or f"cogs.{cleanname}" in bot.noload:
            bot.logger.info(f"Not loading module cogs.{cleanname}.")
            bot.errorcount += 1
            return
        #actually load the extension
        try:
            await bot.load_extension(f"cogs.{cleanname}")
            bot.extensioncount += 1
            bot.logger.debug(f"Loaded module cogs.{cleanname}.")
        except commands.ExtensionAlreadyLoaded:
            bot.logger.debug(f"{cleanname} is already loaded, skipping")
        except (commands.ExtensionFailed, commands.errors.NoEntryPointError) as error:
            bot.errorcount += 1
            if not hasattr(error, 'original'):
                #only NoEntryPointError doesn't have original
                error.original = commands.errors.NoEntryPointError('')
            bot.logger.error(f"{type(error.original).__name__} while loading '{error.name}'! This module won't be loaded.")
            if isinstance(error.original, ModuleNotFoundError) or isinstance(error.original, ImportError):
                bot.logger.error(f"'{error.original.name}' isn't installed. Consider running 'pip3 install -r requirements_extra.txt.'")
            else:
                bot.logger.error(traceback.format_exc())

async def load_jishaku(bot):
    if "--enablejsk" in sys.argv:
        await bot.load_extension("jishaku")
        bot.logger.info("Loaded Jishaku!")
        if not bot.config['jsk_used']:
            bot.logger.warning("Hello! It looks like you've enabled Jishaku for the first time. It's an invaluable tool for debugging and development, but can be quite dangerous in the wrong hands.")
            bot.logger.warning(f"If your account (or the account with the ID {bot.owner_id}) gets compromised, the attacker will have direct access to your computer.")
            bot.logger.warning("Don't want to use Jishaku? Stop Maximilian now with CTRL-C and run main.py WITHOUT --enablejsk.")
            bot.logger.warning("If you keep using Jishaku, I recommend that you enable 2FA and/or run Maximilian in a VM.")
            bot.logger.warning("Startup will continue in 10 seconds.")
            time.sleep(10) # block here so we don't do anything else (e.g login, cache filling) in the meantime

async def load_required(bot):
    #we use a catch-all as we don't want anything going wrong with this
    # noinspection PyBroadException
    try:
        await bot.load_extension("core")
        await bot.load_extension("errorhandling")
    except:
        bot.logger.critical("Failed to load required modules.")
        traceback.print_exc()
        quit()

async def load_extensions_async(bot):
    """New non-blocking method for loading extensions. Same functionality as load_extensions but compatible with dpy2."""
    await load_jishaku(bot)
    bot.logger.info("Loading modules...")
    bot.extensioncount, bot.errorcount = 0, 0
    print("Loading required modules...")
    await load_required(bot)
    print("Loading other modules...")
    for each in os.listdir("./cogs"):
        await load(bot, each)
    bot.logger.info(f"Loaded {bot.extensioncount} modules successfully. {bot.errorcount} module{'s' if bot.errorcount != 1 else ''} not loaded.")
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
    config = startup.check_config(config)
    token = config['token']
    logger.debug("Checking discord.py version...")
    startup.check_version()
    intents = discord.Intents.default()
    intents.members=True
    intents.message_content = True
    logger.debug("Getting version information...")
    if "--alt" in sys.argv:
        token = input("Enter a token to use: \n").strip()
        logger.debug("Getting latest commit hash...")
        commit = common.get_latest_commit()[0]
        logger.debug("Done getting latest commit hash.")
    else:
        commit = ""
    logger.debug("Setting up some stuff")
    bot = commands.Bot(command_prefix=core.get_prefix, owner_id=int(config['owner_id']), intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v1.0.5{f'-{commit}' if commit else ''}"))
    #set up some important stuff
    bot.database = "maximilian" #TODO: remove this
    #TODO: remove unused attrs
    bot.logger = logger
    bot.common = common
    bot.config = config
    await wrap_event(bot)
    #show version information
    bot.logger.warning(f"Starting Maximilian v1.0.5{f'-{commit}' if commit else ''}{' with Jishaku enabled ' if '--enablejsk' in sys.argv else ' '}(running on Python {sys.version_info.major}.{sys.version_info.minor} and discord.py {discord.__version__}) ")
    #parse additional arguments (ip, enablejsk, noload)
    bot.noload = []
    bot.logger.debug("Parsing command line arguments...")
    startup.parse_arguments(bot, sys.argv)
    bot.guildlist = []
    bot.prefix = {}
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
    #TODO: choose your fighter: subclass or context manager
    #if "--with-setup-hook" in sys.argv:
    asyncio.create_task(load_extensions_async(bot))
    print("Logging in...")
    if not "--nologin" in sys.argv:
        await bot.start(token)

print("Starting Maximilian...\nPress Ctrl-C at any time to quit.\n")
print("setting up logging...")
# set a logging level
config_logging(sys.argv)
logging.getLogger('discord').setLevel(logging.INFO)
outer_logger = logging.getLogger(f'maximilian') #different name than inside run for readability
# noinspection PyBroadException
try:
    #run updater
    outer_logger.info("Running updater")
    try:
        if "--noupdate" not in sys.argv:
            update()
        if "--update" in sys.argv:
            print("Updater exited and main.py was invoked with '--update'. Exiting.")
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
        print("Unhandled exception while handling unhandled exception!! This should never happen")
        pass

outer_logger.warning("Logging stopped at " + str(datetime.datetime.now()) + ".\n")
logging.shutdown()
