#import libraries
print("Loading libraries...")
import discord
from discord.ext import commands 
from discord.ext import tasks
import logging
import sys
import init
import common
import helpcommand
import pymysql
import traceback
import datetime
import time
import core
import asyncio

print("starting...")
#get a new event loop before doing anything else
loop = asyncio.new_event_loop()
token = common.token().get("token.txt")
init.config_logging(sys.argv)
intents = discord.Intents.default()
intents.members=True
bot = commands.Bot(command_prefix=core.get_prefix, owner_id=538193752913608704, intents=intents, loop=loop, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.6 (stable)"))
init.init(bot).parse_arguments(sys.argv)
bot.logger = logging.getLogger('maximilian-stable')
bot.logger.warning(f"Maximilian v0.6 ({'Jishaku enabled' if '--enablejsk' in sys.argv else 'Jishaku disabled'}, Python {sys.version}, discord.py {discord.__version__}) ")
bot.guildlist = []
bot.prefixes = {}
bot.responses = []
bot.start_time = time.time()
bot.dbinst = common.db(bot)
bot.database = "maximilian"
#try to connect to database, if it fails warn
print(f"Attempting to connect to database '{bot.database}' on '{bot.dbip}'...")
try:
    bot.dbinst.connect(bot.database)
    print("Connected to database successfully.")
except pymysql.err.OperationalError:
    bot.logger.critical("Couldn't connect to database, most features won't work. Make sure you passed the right IP and that the database is configured properly.")
#load extensions
extensioncount = 0
for roots, dirs, files in os.walk("./cogs"):
    for each in files:
        if each.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{each[:-3]}")
                extensioncount += 1
            except commands.ExtensionFailed as error:
                bot.logger.error(f"{type(error.original).__name__} while loading '{error.name}'. Check the debug logs for more information.")
                if isinstance(error.original, SyntaxError):
                    bot.logger.debug(traceback.format_exc())
                elif isinstance(error.original, ModuleNotFoundError) or isinstance(error.original, ImportError):
                    bot.logger.error(f"The {error.original.name} module isn't installed, '{error.name}' won't be loaded")
#create instances of certain cogs, because we need to call functions within those cogs
try:
    bot.load_extension("cogs.prefixes")
    bot.load_extension("core")
    bot.load_extension("errorhandling")
except:
    bot.logger.critical("Failed to load required extensions.")
    traceback.print_exc()
    quit()
print("Loaded required extensions successfully. Loading other extensions...")
init.init(bot).load_extensions()

@bot.event
async def on_message(message):
    if await bot.coreinst.prepare(message):
        await bot.process_commands(message)

def cancel_tasks(loop):
    tasks = {t for t in asyncio.all_tasks(loop=loop) if not t.done()}
    bot.logger.info(f'Cancelling {len(tasks)} tasks...')
    #don't do anything if there aren't any tasks
    if not tasks:
        return bot.logger.info('No tasks to cancel, skipping this step.')
    #if there are tasks, cancel all of them
    [task.cancel() for task in tasks]
    #then get their results
    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    bot.logger.info('All tasks have been canceled.')
    #if there were any tasks with exceptions, report them
    for task in tasks:
        if task.cancelled():
            continue
        if task.exception() is not None:
            #call the loop's exception handler instead of raising exception
            loop.call_exception_handler({'message': 'Unhandled exception during task shutdown.', 'exception': task.exception(), 'task': task})

def cleanup(loop):
    try:
        #first, cancel background tasks
        cancel_tasks(loop)
        bot.logger.info('Closing async generators...')
        #then close async generators (e.g AsyncIterator objects)
        loop.run_until_complete(loop.shutdown_asyncgens())
        bot.logger.info('Shutting down the executor...')
        # then close the executor (only available in python 3.9+)
        if sys.version_info.minor < 9:
            bot.logger.info("shutdown_default_executor isn't available in this Python version. Skipping this step.")
        else:
            loop.run_until_complete(loop.shutdown_default_executor())
    finally:
        #finally, close the event loop
        bot.logger.info('Closing the event loop.')
        loop.close()

async def start():
    try:
        await bot.start(token)
    finally:
        #while task cleanup is happening, do bot-related cleanup
        if not bot.is_closed():
            bot.logger.info("Disconnecting from voice...")
            #disconnect from all voice channels (if connected to any)
            if not bot.voice_clients:
                bot.logger.info("No voice channels to disconnect from, skipping this step.")
            else:
                [await voice.disconnect() for voice in bot.voice_clients]
                bot.logger.info("Disconnected from all voice channels.")
                #destroy all players too
                bot.get_cog('music').players={}
                bot.logger.info("Destroyed all players.")
            #close the database connection
            bot.dbinst.dbc.close()
            bot.logger.info("Closed database connection.")
            #unload extensions
            [bot.unload_extension(extension) for extension in list(bot.extensions.keys())]
            bot.logger.info("Unloaded all extensions.")
            #then close the connection to Discord
            await bot.close()
            bot.logger.info("Closed connection to Discord.")


def main():
    #run start immediately when the loop starts
    future = asyncio.ensure_future(start(), loop=loop)
    try:
        bot.logger.info("Loop started.")
        #start the loop
        loop.run_forever()
    except KeyboardInterrupt:
        #if there's a keyboardinterrupt, start cleanup
        bot.logger.info("KeyboardInterrupt detected.")
        bot.logger.info("Cleaning up.")
        cleanup(loop)

    if not future.cancelled():
        try:
            return future.result()
        except KeyboardInterrupt:
            pass
try:
    #main blocks until it returns (or an exception is thrown), and it handles shutdown
    main()
    #once all cleanup finishes and the event loop closes, shutdown is finished and main returns.
    bot.logger.info("Shutdown completed successfully.")
except:
    #if there's an error, print it
    bot.logger.error("Unhandled error during shutdown:")
    traceback.print_exc()

#one last message noting the time logging stopped at
bot.logger.warning(f"Logging stopped at {datetime.datetime.now()}. \n")
#shutdown logging
logging.shutdown()
