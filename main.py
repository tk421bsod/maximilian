#main.py: loads core libraries and everything in the cogs folder, then starts Maximilian
import sys

#Text formatting things from common.py.
#Reimplemented here to avoid costly imports (discord.py in particular)
class Text:
    NORMAL = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

#Version number. Please don't modify this.
VER = "2.0.0-prerelease"

#Are we using or going to use debug logging?
IS_DEBUG = bool([i for i in sys.argv if i in ['-v', '--verbose', '--debug']])

#Python minor version. Used for some compatibility checks.
PYTHON_MINOR_VERSION = sys.version_info.minor

#Are we being imported?
if __name__ != "__main__":
    print("It looks like you're trying to import main.py.")
    print(f"{Text.BOLD}Please don't do that.{Text.NORMAL} Some code here relies on being ran directly through a command such as python3 main.py.")
    print("Need to access some Maximilian API? Just import the right file. Read HOSTING.md for an overview.")
    print("If you have a legitimate use case for this, I'd like to hear about it -- send me a DM at tk___421 on Discord.")
    print("Maximilian will now exit.")
    quit()

#Are we using an out-of-date Python?
if sys.version_info.major == 3 and PYTHON_MINOR_VERSION < 8:
    print("Hi there. It looks like you're trying to run Maximilian with an old version of Python 3.")
    print(f"{Text.BOLD}Maximilian cannot run on Python versions older than 3.8.{Text.NORMAL}")
    print("You'll need to upgrade Python to continue.")
    quit()

#Are we using a very new Python?
if PYTHON_MINOR_VERSION > 11:
    print("Hi there. It looks like your Python installation is newer than version 3.11.")
    print("You may experience issues as Maximilian has not yet been tested on newer versions of Python.\n")

if "--help" in sys.argv:
    print("main.py usage: python3 main.py [OPTIONS]\n")
    print("main.py handles initializing core components, checking requirements, and launching Maximilian.\n")
    print("You can enable/disable features and modify Maximilian's behavior through the use of the following options.\nYou can use more than one option at a time.\n")
    print("Options:")
    print(f"{Text.BOLD}--enablejsk{Text.NORMAL} - Enables Jishaku, an extension used for debugging and code evaluation.")
    print(f"{Text.BOLD}--version{Text.NORMAL} - Shows version information and exits. New in version 2.0.")
    print(f"{Text.BOLD}--no-update{Text.NORMAL} - Skips update check on startup. Takes precendence over --update. Renamed from --noupdate in version 2.0.")
    print(f"{Text.BOLD}--update{Text.NORMAL} - Updates Maximilian and exits. Implicitly enables --force-update.")
    print(f"{Text.BOLD}--force-update{Text.NORMAL} - Forces update check on startup regardless of the time since last update.")
    print(f"{Text.BOLD}--no-load <extensions>{Text.NORMAL} - Skips loading the specified extensions. Renamed from --noload in version 2.0.")
    print(f"{Text.BOLD}--no-rich{Text.NORMAL} - Disables rich text. May be useful on older systems or smaller screens.")
    print(f"-{Text.BOLD}q, --quiet, -e, --error, -w, --warn, -i, --info, -v, --debug, --verbose{Text.NORMAL} - Sets the logging level. If not specified, defaults to logging.WARN. \nDebug logging (-v, --debug, --verbose) can cause a slight performance decrease and will make log files much larger.")
    print(f"{Text.BOLD}--ip <address>{Text.NORMAL} - Tries to connect to a database at the specified address instead of localhost.")
    print(f"{Text.BOLD}--help{Text.NORMAL} - Shows this message and exits.")
    print(f"{Text.BOLD}--language <language>{Text.NORMAL} - Sets the language to <language>. If not specified, defaults to the language present in 'config', then 'en' if nothing is found. New in version 2.0.")
    print(f"{Text.BOLD}--alt{Text.NORMAL} - Prompts for a token to use. Also adds the latest commit hash to the default status.")
    print(f"{Text.BOLD}--no-file{Text.NORMAL} - Stops Maximilian from saving logs to a file. New in version 2.0.")
    quit()

if "--version" in sys.argv:
    print(f"You are using version {VER}.")
    quit()

#Did the user use any old arguments?
for old_arg, new_arg in {"--noupdate":"--no-update", "--noload":"--no-load"}.items():
    if old_arg not in sys.argv:
        continue
    print(f"You're using the old '{old_arg}' option.\nThis option was changed to '{new_arg}' in 2.0.\nUse the new option instead.")
    quit()

print("Loading components...")

#Ignore unused imports here.
#We import all our dependencies here to provide the user with useful feedback if something is missing.
try:
    import asyncio
    import datetime
    import logging
    import os
    import traceback
    import time
except (ImportError, NameError, SyntaxError) as e:
    print("It looks like your Python installation is missing some features.\nIf you built it from source, you may need to install additional dependencies and reinstall.")
    print(e)
    sys.exit(2)

try:
    import discord
    import aiomysql
    from discord.ext import commands
    from discord.ext.commands.errors import NoEntryPointError
except (ImportError, NameError, SyntaxError) as e:
    print(f"{Text.BOLD}Maximilian cannot start because an external dependency failed to load.{Text.NORMAL}\nTry running 'pip3 install -U -r requirements.txt' and ensuring Maximilian is using the correct Python installation.\nHere's some more error info:")
    print(e)
    if IS_DEBUG:
        traceback.print_exc()
    sys.exit(2)

try:
    from db_utils import async_db
except ImportError as e:
    print(f"{Text.BOLD}Maximilian cannot start because its database API failed to load.{Text.NORMAL}\nConsider running 'git submodule init' followed by 'git submodule update'.")
    sys.exit(2)

try:
    from base import maximilian
    import updater
except (ImportError, NameError, SyntaxError) as e:
    print(f"{Text.BOLD}Maximilian cannot start because an internal module failed to load.{Text.NORMAL}\nIf you made changes, please review them. You may want to use `git restore <file>` to revert your changes.\nIf you just updated to a new Maximilian version, let tk___421 know and consider publicly shaming them as this should never have gotten through testing in the first place.")
    print(e)
    if IS_DEBUG:
        traceback.print_exc()
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
    if os.path.isdir('logs') and "--no-file" not in sys.argv:
        _handlers.append(logging.FileHandler(f"logs/maximilian-{datetime.date.today()}.log"))
    elif "--no-file" in sys.argv:
        print("main.py was invoked with --no-file, not logging to a file")
    else:
        print("The 'logs' directory doesn't exist! Not logging to a file.")
    for key, value in levelmapping.items():
        if key not in args:
            pass
        elif key != "-q" and key != "--quiet":
            logging.basicConfig(level=value[0], handlers=_handlers)
            print("\n"+value[1])
            if value[0] == logging.DEBUG:
                print("This may cause a small performance decrease for some operations.")
                print("It can also result in very large log files.")
                print("Debug logging is not recommended for production use.")
                time.sleep(2)
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
        if "--no-update" not in sys.argv:
            updater.update()
        else:
            print("main.py invoked with '--no-update', skipping update check")
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
    #initialize stuff needed before we enter an async context
    bot = maximilian(outer_logger, VER)
    bot.IS_DEBUG = IS_DEBUG
    bot.PYTHON_MINOR_VERSION = PYTHON_MINOR_VERSION
    #hand things over to base.maximilian.run
    asyncio.run(bot.run())
except KeyboardInterrupt:
    print("\nKeyboardInterrupt detected. Exiting.")
except KeyError:
    outer_logger.error("The configuration file is missing something. Try pulling changes and re-running setup.sh.")
    outer_logger.info(traceback.format_exc())
except FileNotFoundError:
    outer_logger.error("No configuration file found. Run setup.sh.")
except SystemExit: #raised on quit()
    print("Exiting.")
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
