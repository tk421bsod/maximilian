#main.py: loads core libraries and everything in the cogs folder, then starts Maximilian
print("Loading libraries...")
import asyncio
import datetime
import functools
import json
import logging
import os
import subprocess
import sys
import time
import traceback

import discord
from discord.ext.commands.errors import NoEntryPointError
import pymysql
from discord.ext import commands
import common
import core
import db
from rich.logging import RichHandler
from rich.traceback import install
install(suppress=[discord,pymysql])

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

def get_latest_commit():
    try:
        commit = ""
        p = subprocess.Popen(['git', 'rev-list', '--count', 'HEAD'],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if out:
            commit = out.decode('utf-8').strip()
        p = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if out:
            commit = out.decode('utf-8').strip()
        return commit
    except Exception:
        pass

def initialize_i18n(bot):
    bot.logger.info('Initializing i18n...')
    if '--language' in sys.argv:
        language = sys.argv[sys.argv.index('--language')+1]
        supported = [i.split('.')[0] for i in os.listdir('languages') if i.endswith('.txt')]
        if language not in supported:
            bot.logger.error(f"That language isn't supported right now. The only supported languages are {supported}")
            os._exit(25)
    else:
        bot.logger.info("No language specified, defaulting to en")
        language = 'en'
    bot.logger.info(f"Set language to {language}")
    with open(f'languages/{language}', 'r') as data:
        bot.i18n = json.load(data)
    bot.logger.info('Initialized i18n, everything after this message will use the language above')


def config_logging(args):
    '''Sets logging level and file to write to'''
    #mapping of argument to logging level and status message
    levelmapping = {"-v":[logging.DEBUG, "Debug logging enabled."], "--debug":[logging.DEBUG, "Debug logging enabled."], "--verbose":[logging.DEBUG, "Debug logging enabled."], "-i":[logging.INFO, "Logging level set to INFO."], "--info":[logging.INFO, "Logging level set to INFO"], "-w":[logging.WARN, "Logging level set to WARN."], "--warn":[logging.WARN, "Logging level set to WARN."], "-e":[logging.ERROR, "Logging level set to ERROR."], "--error":[logging.ERROR, "Logging level set to ERROR."], "-q":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."], "--quiet":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."]}
    _handlers = [RichHandler(rich_tracebacks=True, tracebacks_suppress=[discord, pymysql])]
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
    logging.basicConfig(level=logging.WARN, handlers=_handlers, format="%(message)s", datefmt="[%X]")
    print("No logging level specified, falling back to WARN.")
    logging.getLogger("maximilian.config_logging").warning(f"Logging started at {datetime.datetime.now()}")

def get_release_level():
    '''Determines what file to get the token from, among other stuff, depending on the version passed via arguments'''
    if "--beta" in sys.argv:
        filename = "betatoken.txt"
        sys.argv.pop(sys.argv.index("--beta"))
        database = "maximilian_test"
        ver = 'beta'
    elif "--dev" in sys.argv:
        filename = "devtoken.txt"
        sys.argv.pop(sys.argv.index("--dev"))
        database = "maximilian"
        ver = 'dev'
    else:
        filename = "token.txt"
        database = "maximilian"
        ver = 'stable'
    return filename, database, ver

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
        if "--enablejsk" in args:
            bot.load_extension("jishaku")
            bot.logger.info("Loaded Jishaku.")
        if "--noload" in args:
            bot.noload = [i for i in args[args.index('--noload')+1:] if not i.startswith('-')]
        else:
            bot.noload = []
    else:
        bot.logger.warning("No arguments provided.")
        bot.dbip = "localhost"

async def load_extensions_async(bot):
    '''New non-blocking method for loading extensions. Same functionality as load_extensions but compatible with dpy2.'''
    bot.logger.info("Loading extensions...")
    extensioncount, errorcount = 0, 0
    print("Loading required extensions...")
    try:
        #bot.load_extension("cogs.prefixes")
        await bot.load_extension("core")
        await bot.load_extension("errorhandling")
    except:
        bot.logger.critical("Failed to load required extensions.")
        traceback.print_exc()
        quit()
    print("Loaded required extensions successfully. Loading other extensions...")
    for each in os.listdir("./cogs"):
        #strip file extension out of filename
        cleanname = each[:-3]
        #ignore anything that isn't a python file
        if each.endswith(".py"):
            #check if we're not loading this extension
            if cleanname in bot.noload or f"cogs.{cleanname}" in bot.noload:
                bot.logger.info(f"Not loading cogs.{cleanname}.")
                errorcount += 1
                continue
            #actually load the extension
            try:
                await bot.load_extension(f"cogs.{cleanname}")
                extensioncount += 1
                bot.logger.debug(f"Loaded cogs.{cleanname}.")
            #extensions (besides cogs.prefixes) should never be already loaded when this runs.
            #if this runs again after startup something has gone terribly wrong.
            #catch the error so we can continue anyways
            except commands.ExtensionAlreadyLoaded:
                bot.logger.debug(f"{cleanname} is already loaded, skipping")
            except (commands.ExtensionFailed, commands.errors.NoEntryPointError) as error:
                errorcount += 1
                if not hasattr(error, 'original'):
                    #only NoEntryPointError doesn't have original
                    error.original = commands.errors.NoEntryPointError('')
                bot.logger.error(f"{type(error.original).__name__} while loading '{error.name}'! This extension won't be loaded.")
                if isinstance(error.original, ModuleNotFoundError) or isinstance(error.original, ImportError):
                    bot.logger.error(f"The {error.original.name} module isn't installed. Consider installing the packages in requirements_extra.txt.")
                else:
                    pass#bot.logger.error(traceback.format_exc())
    #get cogs as some extensions refer to each other
    #TODO: get rid of this ugliness
    try:
        bot.coreinst = bot.get_cog('core')
        if not bot.dbdisabled:
            bot.prefixesinst = bot.get_cog('prefixes')
        bot.responsesinst = bot.get_cog('Custom Commands')
        bot.miscinst = bot.get_cog('misc')
        bot.reactionrolesinst = bot.get_cog('reaction roles')
    except:
        bot.logger.error("Failed to get one or more cogs, some stuff might not work.")
    bot.logger.info(f"loaded {extensioncount} extensions successfully ({errorcount} extension{'s' if errorcount != 1 else ''} not loaded), waiting for ready")

#wrap the main on_message event in a function for prettiness
async def wrap_event(bot):
    @bot.event
    async def on_message(message):
        if await bot.coreinst.prepare(message):
            await bot.process_commands(message)
    pass

#wrap everything in a function to prevent conflicting event loops

async def run(logger):
    logger.debug("Loading settings from file...")
    config = common.load_config()
    logger.debug("Loaded settings from file!")
    token = config['token']
    check_version()
    intents = discord.Intents.default()
    intents.members=True
    intents.message_content = True
    logger.debug("Getting version information...")
    #figure out what we're logging in as
    tokenfilename, database, ver = get_release_level()
    logger.debug(f"Logging in as '{ver}'")
    if ver == 'stable':
        if config['owner_id'] == "538193752913608704" and (os.path.exists('devtoken.txt') or os.path.exists('betatoken.txt')) and not "--nologin" in sys.argv:
            print("You're attempting to start the production version of Maximilian when you have other versions available.\nAre you sure you want to do this? \nIf you're certain this won't break anything, enter 'Yes, do as I say!' below.\n")
            if input() == "Yes, do as I say!":
                print("\nOk, starting Maximilian.\n")
                await asyncio.sleep(1)
            else:
                print("You need to type 'Yes, do as I say!' exactly as shown.")
                os._exit(5)
        commit = ''
    else:
        token = common.token().get(tokenfilename)
        logger.debug("Getting latest commit hash...")
        commit = get_latest_commit()
        logger.debug("Done getting latest commit hash.")
    logger.debug("Setting up some stuff")
    bot = commands.Bot(command_prefix=core.get_prefix, owner_id=int(config['owner_id']), intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v1.0.0{f'-{commit}' if commit else ''} ({ver})"))
    #set up some important stuff
    bot.database = database
    bot.logger = logger
    check_version()
    try:
        bot.USE_CUSTOM_EMOJI = config['custom_emoji']
    except KeyError:
        bot.USE_CUSTOM_EMOJI = False
    try:
        #experimental i18n, not used at the moment
        #initialize_i18n(bot)
        pass
    except:
        if '--i18n-errors' in sys.argv:
            traceback.print_exc()
        logger.critical('i18n initialization failed! Does the translation file exist?')
        os._exit(53)
    await wrap_event(bot)
    #show version information
    bot.logger.warning(f"Starting maximilian-{ver} v1.0.0{f'-{commit}' if commit else ''}{' with Jishaku enabled ' if '--enablejsk' in sys.argv else ' '}(running on Python {sys.version_info.major}.{sys.version_info.minor} and discord.py {discord.__version__}) ")
    #parse additional arguments (ip, enablejsk, noload)
    bot.noload = []
    bot.logger.debug("Parsing command line arguments...")
    parse_arguments(bot, sys.argv)
    bot.logger.debug("Done parsing command line arguments.")
    bot.guildlist = []
    bot.prefixes = {}
    bot.responses = []
    bot.start_time = time.time()
    bot.logger.debug("Done setting up stuff.")
    #try to connect to database, exit if it fails
    try:
        #constructing an instance of db calls db.db.attempt_connection
        bot.dbinst = db.db(bot, config['dbp'])
    except pymysql.err.OperationalError:
        bot.logger.error("Couldn't connect to database. Trying to start it...")
        #TODO: figure out a better way to do this as some linux systems use different commands
        os.system("sudo service mysql start")
        try:
            bot.dbinst = db.db(bot, config['dbp'])
        except pymysql.err.OperationalError:
            bot.logger.debug(traceback.format_exc())
            bot.logger.critical(f"Couldn't connect to database! \nTry running 'bash setup.sh fix'.")
            os._exit(96)
    #make sure all tables exist
    try:
        bot.dbinst.ensure_tables()
    except pymysql.OperationalError:
        bot.logger.error("Unable to create one or more tables! Does `maximilianbot` not have the CREATE permission?")
    #monkeypatch setup_hook
    #TODO: choose your fighter: subclass or context manager
    bot.setup_hook = functools.partial(load_extensions_async, bot)
    #and log in
    print("Logging in...")
    if not "--nologin" in sys.argv:
        await bot.start(token)

print("starting... \n")
print("setting up logging...")
#set a logging level
config_logging(sys.argv)
logger = logging.getLogger(f'maximilian')
try:
    asyncio.run(run(logger))
except KeyboardInterrupt:
    logger.error("KeyboardInterrupt detected. Exiting.")
except KeyError:
    logger.error("The configuration file is missing something. Try pulling changes and re-running setup.sh.")
    logger.info(traceback.format_exc())
except FileNotFoundError:
    logger.error("No configuration file found. Run setup.sh.")
except SystemExit:
    pass
except:
    logger.error("Uncaught exception! Exiting.")
    logger.error(traceback.format_exc())

