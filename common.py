#common.py: a shared library containing a bunch of useful stuff
import subprocess
import logging

class Version:
    __slots__ = ("major", "minor", "micro")

    def __init__(self):
        self.major = 0
        self.minor = 0
        self.micro = 0

def load_config():
    '''Loads configuration data from the config file generated by setup.sh.'''
    config = {}
    #Uncomment the following line to suppress KeyErrors that can happen when trying to access config. This may break stuff.
    #import collections; config = collections.defaultdict(lambda: None)
    with open('config', 'r') as configfile:
        for i in configfile.readlines():
            if not i.strip().startswith('#') and i.strip():
                i = i.strip().split(':',1)
                config[i[0]] = i[1]
    return config

def run_command(args):
    if logging.root.level == logging.DEBUG:
        logging.getLogger('common').debug(f"Calling run_command with {args}")
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return {"output":out.decode('utf-8').strip().split("\n"), "returncode":p.returncode}

def get_latest_commit():
    try:
        return run_command(['git', 'rev-parse', '--short', 'HEAD'])['output']
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
