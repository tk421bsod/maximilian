import json
import os
import sys
import time
import traceback

import discord
from aiomysql import OperationalError

import common
from common import Text
from db_utils import async_db as db

def set_bit(config : dict, name : str, write:bool=True):
    """Sets a bit at 'name' if it doesn't exist. Otherwise, keeps the value the same. Used for one-time things, e.g warnings on first startup. The write argument specifies whether to write the bit to persistent storage."""
    try:
        config[name]
        config[name] = True
    except:
        config[name] = False
        if write:
            common.run_command(f'echo \"{name}:1\" >> config')
    return config

def preprocess_config(config : dict):
    """Processes configuration data and sets flags if needed. Returns the processed data."""
    #convert hex color to int
    config['theme_color'] = int(config['theme_color'], 16)
    config = set_bit(config, "jsk_used", "--enablejsk" in sys.argv)
    #config = set_bit(config, "2.0_first_run_message")
    default_cmdline = common.get_value(config, "default_cmdline")
    if default_cmdline:
        print("It looks like you've set some default command line options through the 'default_cmdline' field in 'config'.")
        print(f"They are: {default_cmdline}")
        print("Options passed at runtime may take priority.\n")
        time.sleep(0.5)
        for arg in default_cmdline.split(" "):
            arg = arg.strip()
            sys.argv.append(arg)
    return config

def show_2_0_first_run_message(config : dict):
    """Shows the Maximilian 2.0 first run message."""
    if common.get_value(config, "2.0_first_run_message") == False:
        lines = []
        lines.append(f"\n----\n{Text.BOLD}Update finished.")
        lines.append(f"Welcome to Maximilian 2.0.{Text.NORMAL}")
        lines.append("This release includes hybrid commands, new components, performance improvements, API changes, new runtime options, a translation subsystem, and so much more.")
        lines.append("\nPlease take into account the following breaking API changes:")
        lines.append("- Confirmations now handle sending messages. They require two follow-up messages (one for each state, contained in a list) and a prompt to send.")
        lines.append("- db.exec() is now a coroutine, and only returns either an iterable or None.")
        lines.append("- Most core modules do not allow for dynamic attribute creation. Your custom code must be self-contained and additions to a module's attributes require corresponding additions to __slots__.")
        lines.append("- Custom code can now request required Intents or database tables through a 'requirements' method located outside the main Cog.")
        lines.append("- Most strings sent by the bot are managed by the new translation subsystem.")
        lines.append("See docs/API.md for an overview of the current API.")
        lines.append("\n'Hybrid commands' are commands that work both as standard prefix commands and slash commands.")
        lines.append(f"{Text.BOLD}TO ENABLE SLASH COMMAND FUNCTIONALITY, YOU MUST RUN `utils sync` AFTER LOGGING IN.{Text.NORMAL}")
        lines.append("This sends Discord data used to provide slash commands on the client side.")
        lines.append("Any changes to slash commands, including additions, removals, and changes to function signatures, will only take effect after running 'utils sync'.")
        lines.append("\nNew components:")
        lines.append("ThemedEmbed - A discord.Embed that automatically applies the theme_color attribute introduced in 1.0.")
        lines.append("TimeConverter - A discord.ext.commands.Converter that converts an amount of time into seconds. Takes a list of allowed units and supports HelpCommand integration through a couple Command.extras flags.")
        for line in lines:
            print(line)

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
    elif version.minor < 3:
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
        if "--no-load" in args:
            bot.noload = common.consume_all(args, args.index("--no-load"), "-")
        else:
            bot.noload = []
    else:
        bot.logger.warning("No arguments provided.")
        bot.dbip = "localhost"

async def initialize_db(bot, config):
    inst = db.async_db("maximilianbot", config['dbp'], bot.dbip, bot.database, bot.tables)
    try:
        await inst.connect()
    except OperationalError:
        bot.logger.error("Couldn't connect to database. Trying to start it...")
        os.system("bash setup.sh start")
        bot.logger.error("Waiting 5 seconds for database to settle...")
        time.sleep(5)
        try:
            await inst.connect()
        except OperationalError:
            bot.logger.debug(traceback.format_exc())
            bot.logger.critical(f"Couldn't connect to database! \nTry running 'bash setup.sh fix'.")
            sys.exit(96)
    bot.logger.info("Connected to database.")
    return inst

async def get_language(logger, config, exit):
    """Gets the language to use (as a string)"""
    #try to get language from config
    language = common.get_value(config, 'language')
    #do we have anything that overrides our default language?
    if '--language' in sys.argv or language:
        if '--language' in sys.argv:
            #did we override config?
            try:
                if language and sys.argv[sys.argv.index('--language')+1] != language:
                    logger.warning("The language you specified in 'config' has been overridden by the '--language' option!")
                logger.debug("Sourced language from args.")
                #language to use is the element after this one
                language = sys.argv[sys.argv.index('--language')+1]
            except IndexError:
                logger.warning("No language specified after `--language`!")
        else:
            logger.warning("Using the language specified in 'config'.")
        #list of supported language names
        supported = [i.split('.')[0] for i in os.listdir('languages') if not i.endswith('md') and not i.endswith('_') and not i.endswith("-original") and not i.startswith("generate") and not i == "TEMPLATE"]
        if language not in supported and language != "en":
            logger.error(f"Sorry, that language isn't supported right now. The only supported languages are {supported}")
            if exit:
                sys.exit(25)
        return language
    logger.warning("No language specified. Defaulting to 'en'.")
    logger.warning("If you wish to set a default language, add `language:<language>` to config.")
    return 'en'

def missing_string(name):
    return f"[{name}]"

class StringDefaultDict(dict):
    """A collections.defaultdict - like class that replaces missing strings with their identifiers."""

    __slots__ = ("factory", "_fill_in_missing")
    def __init__(self):
        self.factory = missing_string
        self._fill_in_missing = False

    def __missing__(self, key):
        if not self._fill_in_missing:
            raise KeyError(key)
        self[key] = self.factory(key)
        return self[key]

async def load_strings(language, logger):
    logger.debug('Loading strings from file...')
    strings = StringDefaultDict()
    try:
        with open(f'languages/{language}') as data:
            logger.debug("Loading data...")
            strings.update(json.load(data))
            logger.debug("Loaded data.")
    except FileNotFoundError:
        raise RuntimeError(f"Couldn't find the file containing strings for language '{language}'!")
    except json.JSONDecodeError as e:
        logger.critical(f"The file containing strings for language '{language}' is invalid. Try passing it through generate.py.")
        logger.critical("Maximilian will now exit with some additional error info.")
        raise e
    errors_found = False
    if language != 'en':
        logger.info('Validating strings...')
        with open('languages/en') as data:
            reference = json.load(data)
            for identifier in list(reference):
                try:
                    strings[identifier]
                except KeyError:
                    logger.warn(f"The language file '{language}' is missing the string '{identifier}'!")
                    errors_found = True
    if errors_found:
        logger.warn("This language file is missing some strings found in 'en'. Some text may not display correctly.")
    strings._fill_in_missing = True
    logger.info('Strings loaded successfully.')
    return strings

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
