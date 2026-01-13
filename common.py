import asyncio
import datetime
import logging
import os
import re
import subprocess
import sys
from typing import Optional

def get_current_frame():
    """Get the current stack frame.

    See docstring for `common.get_caller_name` for implementation notes.
    """
    #Raise an exception to gain access to stack information.
    try:
        raise Exception
    except Exception as exc:
        #We are in our own stack frame, so go back a frame.
        #Exception object -> Traceback object -> Stack frame where traceback occurred -> Previous stack frame (our caller)
        return exc.__traceback__.tb_frame.f_back

try:
    #Hack to omit imports of external modules if loaded from setup.py
    #We have to go back a bunch of stack frames to get the correct frame.
    IMPORTER_PATH = get_current_frame().f_back.f_back.f_back.f_back.f_back.f_back.f_code.co_filename
except AttributeError:
    IMPORTER_PATH = ""

if not "setup" in IMPORTER_PATH:
    from discord.ext import commands

class Version:
    """Represents a software version."""
    __slots__ = ("major", "minor", "micro")

    def __init__(self):
        self.major = 0
        self.minor = 0
        self.micro = 0

class Text:
    """Console text formatting utilities."""

    NORMAL = '\033[0m'
    BOLD = '\033[1m'

if not "setup" in IMPORTER_PATH:
    #Pre 2.0, TimeConverter in cogs/reminders.py
    class RelativeTimeConverter():
        """Converts relative time values into an amount of seconds.

        A discord.ext.commands.Converter that converts time values into an amount of seconds.
        You can choose which units of time to accept.

        Example usage:  
            #Create a new RelativeTimeConverter with only hours, minutes, and seconds allowed  
            a = RelativeTimeConverter(self.bot, ["h", "m", "s"])  
            a.convert(ctx, "5m")  
            #Returns 300  
      
        For help command integration:  
            1. Add `'uses_relativetimeconverter':True` to Command.extras  
            2. Add `'relativetimeconverter_allowed_units':(<allowed_units>)` to Command.extras  
        Use the 'remind' command from cogs/reminders.py as a reference.
        """
        __slots__ = ("TIME_REGEX", "TIME_DICT", "NAN", "INVALID_UNIT", "ADD_REMOVED", "INVALID_TIME", "allowed_units")

        def __init__(self, bot:commands.Bot, allowed_units:Optional[list]=['w', 'd', 'h', 'm', 's']):
            """
            Construct a new RelativeTimeConverter.

            allowed_units must be a list of strings, each one representing the first letter of a unit of time.
            To only allow hours, minutes, and seconds, something like `allowed_units=["h", "m", "s"]` will work.
            If not specified, allowed_units defaults to ['w', 'd', 'h', 'm', 's'].

            See class documentation for example usage and help command integration.
            """
            self.TIME_REGEX = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhdw])")
            self.TIME_DICT = {"w":604800, "d":86400, "h":3600, "m":60, "s":1}
            self.NAN = bot.strings["RELATIVETIMECONVERTER_NAN"]
            self.INVALID_UNIT = bot.strings["RELATIVETIMECONVERTER_INVALID_UNIT"]
            self.INVALID_TIME = bot.strings["RELATIVETIMECONVERTER_INVALID_TIME"]
            self.ADD_REMOVED = bot.strings["RELATIVETIMECONVERTER_ADD_REMOVED"]
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
                           
class AbsoluteTimeConverter:

    """Convert an absolute date & time to a datetime."""

    FORMAT_STRINGS = {"NUMERIC_MONTH_DAY_YEAR":"%m/%d/%Y,%H:%M:%S", "NUMERIC_DAY_MONTH_YEAR":"%d/%m/%Y,%H:%M:%S", "ABBREVIATED_MONTH_DAY_YEAR":"%b,%d,%Y,%H:%M:%S", "ABBREVIATED_DAY_MONTH_YEAR":"%d,%b,%Y,%H:%M:%S", "FULL_MONTH_DAY_YEAR":"%B,%d,%Y,%H:%M:%S", "FULL_DAY_MONTH_YEAR":"%d,%B,%Y,%H:%M:%S"}

    @staticmethod
    def _preprocess(t):
        logger = logging.getLogger("common")
        t = t.strip()
        #Replace all spaces with commas w/o putting 2 commas next to each other
        t = t.replace(', ', ',').replace(' ', ',')
        #Remove punctuation from abbreviations and remove date suffixes (3rd, 4th, 1st, etc)
        for item in ['.', 'st', 'nd', 'rd', 'th']:
            t_replaced = t.replace(item, '')
            if t_replaced != t:
                logger.debug(f"Removed '{item}'")
            t = t_replaced
        #If there's no time, append a default time
        if ":" not in t:
            logger.debug("No time provided, assuming noon")
            t += ",12:00:00"
        #Pad time value with seconds if needed
        if len(t.split(":")) == 2:
            logger.debug("Adding seconds to time")
            parts = t.split(":")
            #Is this 12 hour time?
            if ',' in parts[1]:
                m, p = parts[1].split(",")
                parts[1] = f':{m}:00,{p}'
            else:
                parts[1] = f':{parts[1]}:00'
            t = parts[0] + parts[1]
        return t

    @staticmethod
    def convert(t):
        logger = logging.getLogger("common")
        logger.debug(f"Trying to convert provided absolute time {t}")
        #Get the time value into a format we can apply our format strings to
        t = AbsoluteTimeConverter._preprocess(t)
        logger.debug(f"Time string after preprocessing: {t}")
        for format_type, format_string in AbsoluteTimeConverter.FORMAT_STRINGS.items():
            logger.debug(f"Trying format {format_type}")
            try:
                ret = datetime.datetime.strptime(t, format_string)
            except ValueError:
                logger.debug("Trying 12 hour time")
                try:
                    format_string_12hr = format_string.replace("%H", "%I") + ",%p"
                    ret = datetime.datetime.strptime(t, format_string_12hr)
                except ValueError:
                    continue
            logger.debug("Converted time string to datetime.")
            return ret 
        logger.debug("Couldn't convert the provided time.")
        return None
                
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
    #Once we've obtained a stack frame of our caller, we need to go back another frame.
    #Caller's stack frame -> Previous stack frame (Caller's caller) -> Code object attached to that frame -> name pertaining to code object
    return get_current_frame().f_back.f_back.f_code.co_name

def load_config(path='config'):
    '''Loads configuration data from the config file generated by setup.sh.'''
    config = {}
    #Uncomment the following line to suppress KeyErrors that can happen when trying to access config. This may break stuff.
    #import collections; config = collections.defaultdict(lambda: None)
    with open(path) as configfile:
        for i in configfile.readlines():
            i = i.strip()
            if not i.startswith('#') and i:
                i = i.split(':',1)
                if i[1] == "0":
                    i[1] == 0
                config[i[0]] = i[1]
    return config

def run_command(cmd, use_subprocess=True):
    """Run `cmd` and return its output + exit code in a dict.
    """
    if logging.root.level == logging.DEBUG:
        logging.getLogger('common').debug(f"Running command \"{cmd}\"")
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
    logging.getLogger("common").debug(f"Getting value from `{attr if not 'token' in attr else '[config]'}` at location {loc}")
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

def convert_config(config_dict):
    "Convert configuration data from a dict to a string to write."
    config_string = ""
    for k, v in config_dict.items():
        config_string += f"{k}:{v}\n"
    return config_string

def write_config(config_dict, path="config"):
    """Write configuration data from convert_config to a file at 'path'. Overwrites config file contents."""
    config = convert_config(config_dict)
    with open(path, "w") as configfile:
        configfile.write(config)

def write_to_config(key, value):
    """Save 'key':'value' to config on disk. Does not update the currently loaded config."""
    current = load_config()
    current[key] = value
    write_config()

def show_not_executable():
    print(f"Sorry, {sys.argv[0]} cannot be run on its own.\nThis module provides functionality used by other modules and does not contain anything useful to an end user.\nMaximilian can be launched through main.py.")

if __name__ == "__main__":
    show_not_executable()
