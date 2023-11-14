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
    """
    A discord.ext.commands.Converter that converts time values into an amount of seconds.
    You can choose which units of time to accept.

    Example usage:  
        #Create a new TimeConverter with only hours, minutes, and seconds allowed  
        a = TimeConverter(self.bot, ("h", "m", "s"))  
        a.convert(ctx, "5m")  
        #Returns 300  
  
    For help command integration:  
        1. Add `'uses_timeconverter':True` to Command.extras  
        2. Add `'timeconverter_allowed_units':(<allowed_units>)` to Command.extras  
    Use the 'remind' command from cogs/reminders.py as a reference.
    """
    __slots__ = ("TIME_REGEX", "TIME_DICT", "NAN", "INVALID_UNIT", "ADD_REMOVED", "allowed_units")

    def __init__(self, bot, allowed_units):
        """
        Construct a new TimeConverter.
        """
        self.TIME_REGEX = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhdw])")
        self.TIME_DICT = {"w":604800, "d":86400, "h":3600, "m":60, "s":1}
        self.NAN = bot.strings["TIMECONVERTER_NAN"]
        self.INVALID_UNIT = bot.strings["TIMECONVERTER_INVALID_UNIT"]
        self.INVALID_TIME = bot.strings["TIMECONVERTER_INVALID_TIME"]
        self.ADD_REMOVED = bot.strings["TIMECONVERTER_ADD_REMOVED"]
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

async def _new_run_now(*coros):
    """Run 'coros' concurrently without delay. Uses python 3.11 features like asyncio.TaskGroup and ExceptionGroup"""
    try:
        async with asyncio.TaskGroup() as runner:
            for coro in coros:
                runner.create_task(coro)
    except ExceptionGroup as raised: # pyright: ignore[reportUndefinedVariable]
        #TODO: How should we handle exceptions here?
        #Should we just let the caller take care of everything?
        if len(raised.exceptions) == 1:
            raise raised.exceptions[0]
        raise raised

async def run_now(*coros):
    """Run 'coros' concurrently without delay."""
    if sys.version_info.minor >= 11:
        _new_run_now(*coros)
        return
    await asyncio.gather(*coros)

def get_caller_name():
    """Get the name of the caller.
    
    Faster than `inspect.currentframe().f_back.f_code.co_name` and much faster than `inspect.stack()[1].function`.
    Not implementation dependent unlike calls to `sys._getframe`.
    See https://docs.python.org/3/library/inspect.html#types-and-members and https://docs.python.org/3/library/sys.html#sys._getframe
    """
    #Raise an exception to gain access to stack information.
    try:
        raise Exception
    except Exception as exc:
        #We are in our own stack frame, so go back two frames.
        #Exception object -> Traceback object -> Stack frame where traceback occurred -> Previous stack frame (our caller) -> Previous stack frame (Caller's caller)
        #-> Code object attached to that frame -> name pertaining to code object
        return exc.__traceback__.tb_frame.f_back.f_back.f_code.co_name

def load_config():
    '''Loads configuration data from the config file generated by setup.sh.'''
    config = {}
    #Uncomment the following line to suppress KeyErrors that can happen when trying to access config. This may break stuff.
    #import collections; config = collections.defaultdict(lambda: None)
    with open('config') as configfile:
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

def get_value(attr, loc, default=None):
    """Get the value from 'attr' stored at 'loc'. 'attr' must be a list or dict. 'loc' must be an index or a key. Returns 'default' if nothing's found"""
    try:
        return attr[loc]
    except KeyError:
        return default
    except IndexError:
        return default

def consume_all(l, start, end_condition):
    """
    Return a list of items from list 'l' after index 'start' and until an element starts with 'end_condition'.

    Example:

        >>> a = ["main.py", "--enablejsk", "--no-load", "cogs.music", "-v"]
        >>> consume_all(a, a.index("--no-load), "-")
            ["cogs.music"]

    """
    ret = []
    for elem in l[start+1:]:
        if str(elem).startswith(end_condition):
            break
        ret.append(elem)
    return ret

def set_value(dict, key, value, replace=False):
    """Attempt to set the value at dict[key] to 'value'. Does not replace existing values unless 'replace' is True"""
    try:
        dict[key]
        if not replace:
            dict[key] = value
    except KeyError:
        dict[key] = value

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
