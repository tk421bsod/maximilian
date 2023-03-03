import discord
import common
import logging
import os
import sys
import datetime
import subprocess

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

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
