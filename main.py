#import libraries
print("Loading libraries...")
import asyncio
import datetime
import logging
import os
import sys
import time
import traceback

import discord
import pymysql
from discord.ext import commands

import common
import core
import helpcommand


def config_logging(args):
    levelmapping = {"-v":[logging.DEBUG, "Debug logging enabled."], "--debug":[logging.DEBUG, "Debug logging enabled."], "--verbose":[logging.DEBUG, "Debug logging enabled."], "-i":[logging.INFO, "Logging level set to INFO."], "--info":[logging.INFO, "Logging level set to INFO"], "-w":[logging.WARN, "Logging level set to WARN."], "--warn":[logging.WARN, "Logging level set to WARN."], "-e":[logging.ERROR, "Logging level set to ERROR."], "--error":[logging.ERROR, "Logging level set to ERROR."], "-q":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."], "--quiet":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."]}
    _handlers = [logging.FileHandler(f"logs/maximilian-{datetime.date.today()}.log"), logging.StreamHandler(sys.stdout)]
    for key, value in levelmapping.items():
        if key not in args:
            pass
        elif key in args and key != "-q" and key != "--quiet":
            logging.basicConfig(level=value[0], handlers=_handlers)
            logging.getLogger("maximilian.config_logging").warning(f"Logging started at {datetime.datetime.now()}")
            print(value[1])
            return
        else:
            logging.disable()
            print(value[1])
            return
    logging.basicConfig(level=logging.WARN, handlers=_handlers)
    print("No logging level specified, falling back to WARN.")
    logging.getLogger("maximilian.config_logging").warning(f"Logging started at {datetime.datetime.now()}")

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
        bot.logger.warning("No database IP address provided. Falling back to localhost.")
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
        cleanname = each[:-3]
        if each.endswith(".py"):
            if cleanname in bot.noload or f"cogs.{cleanname}" in bot.noload:
                bot.logger.info(f"Not loading cogs.{cleanname}.")
                continue
            try:
                bot.load_extension(f"cogs.{cleanname}")
                extensioncount += 1
                bot.logger.info(f"Loaded cogs.{cleanname}.")
            except commands.ExtensionAlreadyLoaded:
                bot.logger.info(f"{cleanname} is already loaded, skipping")
            except commands.ExtensionFailed as error:
                errorcount += 1
                bot.logger.error(f"{type(error.original).__name__} while loading '{error.name}'! This extension won't be loaded.")
                if isinstance(error.original, ModuleNotFoundError) or isinstance(error.original, ImportError):
                    bot.logger.error(f"The {error.original.name} module isn't installed.")
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

#wrap everything in a function to prevent conflicting event loops
async def run():
    print("starting...")
    config_logging(sys.argv)
    intents = discord.Intents.default()
    intents.members=True
    bot = commands.Bot(command_prefix=core.get_prefix, owner_id=538193752913608704, intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.6 (stable)"))
    if "--beta" in sys.argv:
        filename = "betatoken.txt"
        sys.argv.pop(sys.argv.index("--beta"))
        bot.database = "maximilian_test"
        ver = 'beta'
    elif "--dev" in sys.argv:
        filename = "devtoken.txt"
        sys.argv.pop(sys.argv.index("--dev"))
        bot.database = "maximilian_test"
        ver = 'dev'
    else:
        filename = "token.txt"
        bot.database = "maximilian"
        ver = 'stable'
    token = common.token().get(filename)
    bot.logger = logging.getLogger(f'maximilian')
    bot.logger.info(f"Logging in as maximilian-{ver}")
    parse_arguments(bot, sys.argv)
    #maybe include latest commit hash here?
    bot.logger.warning(f" Starting maximilian-{ver} v0.6.1 ({'Jishaku enabled' if '--enablejsk' in sys.argv else 'Jishaku disabled'}, Python {sys.version}, discord.py {discord.__version__}) ")
    bot.guildlist = []
    bot.prefixes = {}
    bot.responses = []
    bot.start_time = time.time()
    bot.dbinst = common.db(bot)
    #try to connect to database, if it fails warn
    print(f"Attempting to connect to database '{bot.database}' on '{bot.dbip}'...")
    try:
        bot.dbinst.connect(bot.database)
        print("Connected to database successfully.")
    except pymysql.err.OperationalError:
        bot.logger.critical("Couldn't connect to database, most features won't work. Make sure you passed the right IP address through --ip. \nIf you're able to connect to the server, create a user with the name 'maximilianbot' and a database named either 'maximilian' (for stable) or 'maximilian_test' (for beta/dev).")
    bot.dbinst.ensure_tables()
    load_extensions(bot)

    @bot.event
    async def on_message(message):
        if await bot.coreinst.prepare(message):
            await bot.process_commands(message)
    
    await bot.start(token)

asyncio.run(run())
