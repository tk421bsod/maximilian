#import libraries
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
token = common.token().get("betatoken.txt")
init.config_logging(sys.argv)
intents = discord.Intents.default()
intents.members=True
bot = commands.Bot(command_prefix=core.get_prefix, owner_id=538193752913608704, intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.5.3 (beta)"))
init.init(bot).parse_arguments(sys.argv)
bot.logger = logging.getLogger('maximilian-beta')
bot.logger.warning(f"Logging started at {datetime.datetime.now()}")
bot.guildlist = []
bot.prefixes = {}
bot.responses = []
bot.start_time = time.time()
bot.dbinst = common.db(bot)
bot.database = "maximilian_test"
#try to connect to database, if it fails warn
print(f"Attempting to connect to database '{bot.database}' on '{bot.dbip}'...")
try:
    bot.dbinst.connect(bot.database)
    print("Connected to database successfully.")
except pymysql.err.OperationalError:
    bot.logger.critical("Couldn't connect to database, most features won't work. Make sure you passed the right IP and that the database is configured properly.")
#load extensions, starting with required ones
print("Loading required extensions...")
try:
    bot.load_extension("cogs.prefixes")
    bot.load_extension("core")
    bot.load_extension("errorhandling")
except:
    bot.logger.critical("Failed to load required extensions.")
    traceback.print_exc()
    quit()
print("Loaded required extensions successfully. Loading other cogs...")
init.init(bot).load_extensions()
loop = asyncio.get_event_loop()

def cancel_tasks(loop):
    tasks = {t for t in asyncio.all_tasks(loop=loop) if not t.done()}
    if not tasks:
        return
    bot.logger.info('Cancelling tasks...')
    [task.cancel() for task in tasks]
    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    bot.logger.info('All tasks have been canceled.')

    for task in tasks:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({'message': 'Unhandled exception during task shutdown.', 'exception': task.exception(), 'task': task})

def cleanup(loop):
    try:
        cancel_tasks(loop)
        bot.logger.info('Closing async generators...')
        loop.run_until_complete(loop.shutdown_asyncgens())
        bot.logger.info('Shutting down the executor...')
        if sys.version_info.minor < 9:
            bot.logger.info("shutdown_default_executor isn't available in this Python version. Skipping this step.")
        else:
            loop.run_until_complete(loop.shutdown_default_executor())
    finally:
        bot.logger.info('Closing the event loop.')
        loop.close()

async def start():
    try:
        await bot.start(token)
    finally:
        if not bot.is_closed():
            bot.logger.info("Disconnecting from voice...")
            if not bot.voice_clients:
                bot.logger.info("No voice channels to disconnect from, skipping this step.")
            else:
                [await voice.disconnect() for voice in bot.voice_clients]
                bot.logger.info("Disconnected from all voice channels.")
            bot.dbinst.dbc.close()
            bot.logger.info("Closed database connection.")
            await bot.close()
            bot.logger.info("Closed connection to Discord.")


def main():
    def stop_loop(arg):
        loop.stop()
    future = asyncio.ensure_future(start(), loop=loop)
    future.add_done_callback(stop_loop)
    try:
        bot.logger.info("Loop started.")
        loop.run_forever()
    except KeyboardInterrupt:
        future.remove_done_callback(stop_loop)
        bot.logger.info("KeyboardInterrupt detected.")
        bot.logger.info("Cleaning up.")
        cleanup(loop)

    if not future.cancelled():
        try:
            return future.result()
        except KeyboardInterrupt:
            pass
try:
    main()
    bot.logger.info("Shutdown completed successfully.")
except:
    bot.logger.error("Unhandled error during shutdown:")
    traceback.print_exc()

bot.logger.warning(f"Logging stopped at {datetime.datetime.now()}. \n")