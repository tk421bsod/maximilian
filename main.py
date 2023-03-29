#main.py: loads core libraries and everything in the cogs folder, then starts Maximilian
import sys

if __name__ != "__main__":
    print("It looks like you're trying to import main.py as a module.")
    print("Please don't do that. Some code here relies on being ran directly through a command such as python3 main.py.")
    print("Need to access some Maximilian API? Just import the right file. Read HOSTING.md for an overview.")
    print("If you have a legitimate use case for this, I'd like to hear about it -- send me a DM at tk421#2016 on Discord.")
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
    print("--language <language> - Sets the language to <language>. If not specified, defaults to 'en'.")
    print("--alt - Prompts for a token to use. Also adds the latest commit hash to the default status.")
    quit()

print("Loading components...")

try:
    import asyncio
    import datetime
    import logging
    import os
    import traceback
    import time

    import discord
    from discord.ext import commands
    from discord.ext.commands.errors import NoEntryPointError

    from base import maximilian
    from updater import update
except (ImportError, NameError, SyntaxError) as e:
    print("Maximilian cannot start because a required component failed to load.\nTry running 'pip3 install -U -r requirements.txt' and ensuring Maximilian is using the correct Python installation.\nHere's some more error info:")
    print(e)
    sys.exit(2)

if not "--no-rich" in sys.argv:
    try:
        from rich.logging import RichHandler
    except ImportError:
        print("Not enabling rich text - import failed")
else:
    print("Not enabling rich text - user requested")

def config_logging(args):
    """Sets logging level and file to write to"""
    #mapping of argument to logging level and status message
    levelmapping = {"-v":[logging.DEBUG, "Debug logging enabled."], "--debug":[logging.DEBUG, "Debug logging enabled."], "--verbose":[logging.DEBUG, "Debug logging enabled."], "-i":[logging.INFO, "Logging level set to INFO."], "--info":[logging.INFO, "Logging level set to INFO"], "-w":[logging.WARN, "Logging level set to WARN."], "--warn":[logging.WARN, "Logging level set to WARN."], "-e":[logging.ERROR, "Logging level set to ERROR."], "--error":[logging.ERROR, "Logging level set to ERROR."], "-q":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."], "--quiet":["disable", "Logging disabled. Tracebacks will still be shown in the console, along with a few status messages."]}
    try:
        _handlers = [RichHandler(rich_tracebacks=True)]
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

print("Starting Maximilian...\nPress Ctrl-C at any time to quit.\n")
print("setting up logging...")
# set a logging level
config_logging(sys.argv)
logging.getLogger('discord').setLevel(logging.INFO)
outer_logger = logging.getLogger(f'maximilian') #different name than inside run for readability
try:
    #run updater
    outer_logger.info("Running updater")
    try:
        if "--noupdate" not in sys.argv:
            update()
        else:
            print("main.py invoked with '--noupdate', skipping update check")
        if "--update" in sys.argv:
            print("Updater exited and main.py was invoked with '--update'. Exiting.")
            quit()
    except KeyboardInterrupt:
        if "--update" in sys.argv:
            print("Updater interrupted. Exiting.")
            quit()
        print("Updater interrupted. Maximilian will start in a moment.")
        time.sleep(1)
    outer_logger.debug("Preparing to start the event loop...")
    #then start the event loop
    bot = maximilian(outer_logger)
    asyncio.run(bot.run())
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
    try:
        outer_logger.error("Unhandled exception! Exiting.")
        outer_logger.error(traceback.format_exc())
        outer_logger.error("Need more information on Maximilian's state at the time of the error? Run main.py with -i or even -v.")
    except:
        print("Unhandled exception while handling unhandled exception!! This should never happen")
        pass

outer_logger.warning("Logging stopped at " + str(datetime.datetime.now()) + ".\n")
logging.shutdown()
