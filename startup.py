import json
import os
import subprocess
import sys
import time
import traceback

import discord
from aiomysql import OperationalError

import common
import db


def preprocess_config(config):
    #convert hex color to int
    config['theme_color'] = int(config['theme_color'], 16)
    try:
        config['jsk_used']
        config['jsk_used'] = True
    except:
        config['jsk_used'] = False
        if "--enablejsk" in sys.argv:
            subprocess.run("echo \"jsk_used:1\" >> config", shell=True)
    return config

def parse_version(versionstring):
    version = common.Version()
    version.major, version.minor, version.micro = [int(i) for i in versionstring.replace('a','').split('.')[:3]]
    return version

def check_version():
    version = parse_version(discord.__version__)
    if version.major < 2:
        print("\nHi there. It looks like you're running an old version of discord.py.")
        print("As of 1.0 (released on January 4, 2023), Maximilian no longer supports discord.py versions below 2.0.")
        print("Either update discord.py (through something like 'pip3 install -U -r requirements.txt') or use a Maximilian version below 1.0.")
        print("If you choose to use an old version of Maximilian, you're on your own - those versions lack support from tk421 and compatibility with discord.py 2. Old versions may stop working without notice.")
        print("See https://gist.github.com/Rapptz/c4324f17a80c94776832430007ad40e6 for more information about this.")
        quit()
    elif version.minor < 2:
        print("\nHi there. It looks like you're running a discord.py version that's slightly out-of-date.")
        print("You may experience some bugs as new code is only tested with the latest version.")
        print("Some functions may not work at all.")
        print("I recommend updating as soon as you can, through something like 'pip3 install -U -r requirements.txt'.")
        print("Startup will continue in 5 seconds.")
        time.sleep(5) #TODO: consider moving this outside of main.run() as keeping it there may cause some scary "Heartbeat blocked" warnings!

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

async def initialize_db(bot, config):
    inst = db.db(bot, config['dbp'])
    try:
        await inst.connect()
    except OperationalError:
        bot.logger.error("Couldn't connect to database. Trying to start it...")
        os.system("bash setup.sh start")
        try:
            await inst.connect()
        except OperationalError:
            bot.logger.debug(traceback.format_exc())
            bot.logger.critical(f"Couldn't connect to database! \nTry running 'bash setup.sh fix'.")
            sys.exit(96)
    bot.logger.info("Connected to database.")
    return inst

async def load_strings(logger, config, exit=True):
    logger.debug('Loading strings from file...')
    #try to get language from config
    language = common.get_value(config, 'language')
    #do we have anything that overrides our default language?
    if '--language' in sys.argv or language:
        #is it from config or args
        if '--language' in sys.argv:
            #did we override config?
            if language and sys.argv[sys.argv.index('--language')+1] != language:
                logger.warning("The language you specified in 'config' has been overridden by the '--language' option!")
            logger.debug("Sourced language from args :)")
            #language to use is the element after this one
            language = sys.argv[sys.argv.index('--language')+1]
        else:
            logger.warning("Using the language specified in 'config'.")
        #list of supported language names
        supported = [i.split('.')[0] for i in os.listdir('languages') if not i.endswith('md') and not i.endswith("-original") and not i.startswith("generate") and not i == "TEMPLATE"]
        if language not in supported:
            logger.error(f"Sorry, that language isn't supported right now. The only supported languages are {supported}")
            if exit:
                sys.exit(25)
    else:
        logger.info("No language specified, defaulting to en")
        language = 'en'
    logger.info(f"Set language to {language}")
    try:
        with open(f'languages/{language}', 'r') as data:
            logger.debug("Loading data...")
            strings = json.load(data)
    except FileNotFoundError:
        raise RuntimeError(f"Couldn't find the file containing strings for language '{language}'.")
    except json.JSONDecodeError as e:
        logger.critical(f"The file containing strings for language '{language}' is invalid. Try passing it through generate.py.")
        logger.critical("Maximilian will now exit with some additional error info.")
        raise e
    logger.info('Strings loaded successfully.')
    return strings

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
