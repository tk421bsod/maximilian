print("Loading libraries...")
import asyncio
import datetime
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
import errors

class Version:
    def __init__(self):
        self.major = 0
        self.minor = 0
        self.patch = 0

def parse_version(versionstring):
    version = Version()
    version.major, version.minor, version.patch = [int(i) for i in versionstring.replace('a','').split('.')]
    return version

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

def load_config():
    config = {}
    #Uncomment the following line to suppress KeyErrors. This may break stuff.
    #import collections; config = collections.defaultdict(lambda: None)
    with open('config', 'r') as configfile:
        for i in configfile.readlines():
            if not i.strip().startswith('#'):
                i = i.strip().split(':',1)
                config[i[0]] = i[1]
    return config

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
    #mapping of argument to logging level and status message
    levelmapping = {"-v":[logging.DEBUG, "Debug logging enabled."], "--debug":[logging.DEBUG, "Debug logging enabled."], "--verbose":[logging.DEBUG, "Debug logging enabled."], "-i":[logging.INFO, "Logging level set to INFO."], "--info":[logging.INFO, "Logging level set to INFO"], "-w":[logging.WARN, "Logging level set to WARN."], "--warn":[logging.WARN, "Logging level set to WARN."], "-e ":[logging.ERROR, "Logging level set to ERROR."], "--error":[logging.ERROR, "Logging level set to ERROR."], "-q":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."], "--quiet":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."]}
    _handlers = [logging.FileHandler(f"logs/maximilian-{datetime.date.today()}.log"), logging.StreamHandler(sys.stdout)]
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
    logging.basicConfig(level=logging.WARN, handlers=_handlers)
    print("No logging level specified, falling back to WARN.")
    logging.getLogger("maximilian.config_logging").warning(f"Logging started at {datetime.datetime.now()}")

def get_release_level():
    if "--beta" in sys.argv:
        filename = "betatoken.txt"
        sys.argv.pop(sys.argv.index("--beta"))
        database = "maximilian_test"
        ver = 'beta'
    elif "--dev" in sys.argv:
        filename = "devtoken.txt"
        sys.argv.pop(sys.argv.index("--dev"))
        database = "maximilian_test"
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

def load_extensions(bot):
    bot.logger.info("Loading extensions...")
    extensioncount, errorcount = 0, 0
    print("Loading required extensions...")
    try:
        bot.load_extension("cogs.prefixes")
        bot.load_extension("core")
        bot.load_extension("errorhandling")
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
                bot.load_extension(f"cogs.{cleanname}")
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
                    bot.logger.error(traceback.format_exc())
    #create instances of certain cogs
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
    config = load_config()
    logger.debug("Loaded settings from file!")
    token = config['token']
    intents = discord.Intents.default()
    intents.members=True
    logger.debug("Getting version information...")
    if parse_version(discord.__version__).major < 2:
        bot.logger.debug("using dpy 1.x")
        bot.IS_DPY_2 = False
    else:
        bot.IS_DPY_2 = True
        bot.logger.debug("using dpy 2.x")
        bot.logger.warning("It looks like Maximilian is using discord.py 2.x. Use of dpy2 is not recommended for now due to some serious bugs.")
    #figure out what we're logging in as
    tokenfilename, database, ver = get_release_level()
    logger.debug(f"Logging in as '{ver}'")
    #show commit hash and get token from file if not logging in as stable
    if ver != 'stable':
        token = common.token().get(tokenfilename)
        logger.debug("Getting latest commit hash...")
        commit = get_latest_commit()
        logger.debug("Done getting latest commit hash.")
    else:
        commit = ''
    logger.debug("Setting up some stuff")
    bot = commands.Bot(command_prefix=core.get_prefix, owner_id=int(config['owner_id']), intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.6.2{f'-{commit}' if commit else ''} ({ver})"))
    #set up some important stuff
    bot.database = database
    bot.logger = logger
    try:
        #experimental i18n, not used at the moment
        #initialize_i18n(bot)
        pass
    except:
        if '--i18n-errors' in sys.argv:
            traceback.print_exc()
        logger.critical('i18n initialization failed! Does the translation file exist?')
        os._exit(53)
    #see the comment in core.py at around line 137 for an explanation of this
    bot.errors = errors
    await wrap_event(bot)
    #show version information
    bot.logger.warning(f"Starting maximilian-{ver} v0.6.2{f'-{commit}' if commit else ''}{' with Jishaku enabled ' if '--enablejsk' in sys.argv else ' '}(running on Python {sys.version_info.major}.{sys.version_info.minor} and discord.py {discord.__version__}) ")
    #parse additional arguments (ip, enablejsk, noload)
    bot.noload = []
    bot.logger.debug("Parsing command line arguments...")
    parse_arguments(bot, sys.argv)
    bot.logger.debug("Done parsing command line arguments.")
    bot.guildlist = []
    bot.prefixes = {}
    bot.responses = []
    bot.start_time = time.time()
    bot.dbinst = common.db(bot, config['dbp'])
    bot.logger.debug("Done setting up stuff.")
    #try to connect to database, exit if it fails
    bot.logger.info(f"Attempting to connect to database '{bot.database}' on '{bot.dbip}'...")
    try:
        bot.dbinst.connect(bot.database)
        bot.logger.info("Connected to database successfully.")
        bot.dbdisabled = False
    except pymysql.err.OperationalError:
        bot.logger.critical(f"Couldn't connect to database! \nMaybe try running setup.sh again?")
        os._exit(96)
    #make sure all tables exist
    try:
        bot.dbinst.ensure_tables()
    except pymysql.OperationalError:
        bot.logger.error("Unable to create one or more tables! Does `maximilianbot` not have the CREATE permission?")
    #now that we've got most stuff set up, load extensions
    load_extensions(bot)
    #and log in
    print("Logging in...")
    if not "--nologin" in sys.argv:
        await bot.start(token)

print("starting...")
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
except:
    logger.error("Uncaught exception! Exiting.")
    logger.error(traceback.format_exc())

