print("Loading libraries...")
import asyncio
import datetime
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
                    bot.logger.error(f"The {error.original.name} module isn't installed.")
                else:
                    bot.logger.error(traceback.format_exc())
    #create instances of certain cogs
    try:
        bot.coreinst = bot.get_cog('core')
        bot.prefixinst = bot.get_cog('prefixes')
        bot.responsesinst = bot.get_cog('Custom Commands')
        bot.miscinst = bot.get_cog('misc')
        bot.reactionrolesinst = bot.get_cog('reaction roles')
    except:
        bot.logger.error("Failed to get one or more cogs, some stuff might not work.")
    bot.logger.info(f"loaded {extensioncount} extensions successfully ({errorcount} extension{'s' if errorcount != 1 else ''} not loaded), waiting for ready")

async def wrap_event(bot):
    @bot.event
    async def on_message(message):
        if await bot.coreinst.prepare(message):
            await bot.process_commands(message)
    pass

#wrap everything in a function to prevent conflicting event loops
async def run(logger):
    intents = discord.Intents.default()
    intents.members=True
    #figure out what we're logging in as
    tokenfilename, database, ver = get_release_level()
    #show commit hash if not logging in as stable
    if ver != 'stable':
        logger.debug("Getting latest commit hash...")
        commit = get_latest_commit()
        logger.debug("Done getting latest commit hash.")
    else:
        commit = ''
    bot = commands.Bot(command_prefix=core.get_prefix, owner_id=538193752913608704, intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.6.2{f'-{commit}' if commit else ''} ({ver})"))
    #set up some important stuff
    bot.database = database
    bot.logger = logger
    #on_message is wrapped so it looks better
    await wrap_event(bot)
    #show version information
    bot.logger.warning(f" Starting maximilian-{ver} v0.6.2{f'-{commit}' if commit else ''}{' with Jishaku enabled ' if '--enablejsk' in sys.argv else ' '}(running on Python {sys.version_info.major}.{sys.version_info.minor} and discord.py {discord.__version__}) ")
    #this will exit if no token is found (also logs to INFO with filename)
    token = common.token().get(tokenfilename)
    #parse additional arguments (ip, enablejsk, noload)
    bot.noload = []
    bot.logger.debug("Parsing command line arguments...")
    parse_arguments(bot, sys.argv)
    bot.logger.debug("Done parsing command line arguments.")
    #this really shouldn't be here
    bot.guildlist = []
    bot.prefixes = {}
    bot.responses = []
    bot.start_time = time.time()
    bot.dbinst = common.db(bot)
    bot.logger.debug("Done setting up database.")
    #try to connect to database, exit if it fails
    bot.logger.info(f"Attempting to connect to database '{bot.database}' on '{bot.dbip}'...")
    try:
        bot.dbinst.connect(bot.database)
        bot.logger.info("Connected to database successfully.")
        bot.dbdisabled = False
    except pymysql.err.OperationalError:
        bot.logger.critical(f"Couldn't connect to database! Make sure you passed the right IP address through --ip. \nIf you're able to connect to the server, create a user with the name 'maximilianbot' and a database named '{'maximilian' if ver == 'stable' else 'maximilian_test'}'.")
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
    await bot.start(token)

print("starting...")
if "--verbose" in sys.argv or "--debug" in sys.argv or "-v" in sys.argv:
    print("DEBUG:maximilian:Setting up logging...")
#set a logging level
config_logging(sys.argv)
logger = logging.getLogger(f'maximilian')
try:
    asyncio.run(run(logger))
except KeyboardInterrupt:
    logger.error("KeyboardInterrupt detected. Exiting.")
except:
    logger.error("Uncaught exception!")
    logger.error(traceback.format_exc())

