#common.py: a shared library containing a bunch of useful stuff
import asyncio
import logging
import re
import subprocess
import sys

from discord.ext import commands

class Version:
    __slots__ = ("major", "minor", "micro")

    def __init__(self):
        self.major = 0
        self.minor = 0
        self.micro = 0

#TimeConverter originally from cogs/reminders.py
class TimeConverter(commands.Converter):
    __slots__ = ("TIME_REGEX", "TIME_DICT", "NAN", "INVALID_UNIT", "ADD_REMOVED", "allowed_units")
    def __init__(self, strings, allowed_units):
        self.TIME_REGEX = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhdw])")
        self.TIME_DICT = {"w":604800, "d":86400, "h":3600, "m":60, "s":1}
        self.NAN = strings["TIMECONVERTER_NAN"]
        self.INVALID_UNIT = strings["TIMECONVERTER_INVALID_UNIT"]
        self.INVALID_TIME = strings["TIMECONVERTER_INVALID_TIME"]
        self.ADD_REMOVED = strings["TIMECONVERTER_ADD_REMOVED"]
        self.allowed_units = allowed_units
        time_dict_copy = self.TIME_DICT.copy() 
        self.TIME_DICT = {}
        #Only include allowed units in TIME_DICT.
        for unit in self.allowed_units:
            self.TIME_DICT[unit] = time_dict_copy[unit]

    async def convert(self, ctx, argument):
        matches = self.TIME_REGEX.findall(argument.lower())
        time = 0
        if argument == "add":
            await ctx.send(self.ADD_REMOVED)
        for v, k in matches:
            try:
                time += self.TIME_DICT[k]*float(v)
            except KeyError:
                raise commands.BadArgument(self.INVALID_UNIT.format(k, '/'.join(self.allowed_units)))
            except ValueError:
                raise commands.BadArgument(self.NAN)
        if time == 0:
            raise commands.BadArgument(self.INVALID_TIME)
        return time

async def run_now(*coros):
    """Run 'coros' concurrently without delay."""
    if sys.version_info.minor >= 11:
        try:
            async with asyncio.TaskGroup() as runner:
                for coro in coros:
                    runner.create_task(coro)
        except ExceptionGroup as raised:
            #TODO: How should we handle exceptions here?
            #Should we just let the caller take care of everything?
            if len(raised.exceptions) == 1:
                raise raised.exceptions[0]
            raise raised
        return
    await asyncio.gather(*coros)

def load_config():
    '''Loads configuration data from the config file generated by setup.sh.'''
    config = {}
    #Uncomment the following line to suppress KeyErrors that can happen when trying to access config. This may break stuff.
    #import collections; config = collections.defaultdict(lambda: None)
    with open('config', 'r') as configfile:
        for i in configfile.readlines():
            i = i.strip()
            if not i.startswith('#') and i:
                i = i.split(':',1)
                config[i[0]] = i[1]
    return config

def run_command(cmd):
    #why have this check?
    #getting a new Logger on every run_command call could add some performance overhead.
    #(and I don't want to wrap this in a class just so I can add that as an attr)
    if logging.root.level == logging.DEBUG:
        logging.getLogger('common').debug(f"Calling run_command with \"{cmd}\"")
    p = subprocess.run(cmd, shell=True, capture_output=True, encoding="utf-8")
    if logging.root.level == logging.DEBUG:
        logging.getLogger('common').debug({"output":p.stdout.strip().split("\n"), "returncode":p.returncode})
    return {"output":p.stdout.strip().split("\n"), "returncode":p.returncode}

#TODO: Is this needed? This is just a wrapper for a single run_command call.
def get_latest_commit():
    try:
        return run_command("git rev-parse --short HEAD")['output'][0]
    except Exception:
        pass

def get_value(dict, key, default=None):
    try:
        return dict[key]
    except KeyError:
        return default

def set_value(dict, key, value, unique=False):
    try:
        dict[key]
        if not unique:
            dict[key] = value
    except KeyError:
        dict[key] = value

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
