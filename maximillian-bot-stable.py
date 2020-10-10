import discord
from discord.ext import commands 
from common import db
from common import token
import logging

logging.basicConfig(level=logging.WARN)
tokeninst = token()
dbinst = db()
bot = commands.Bot(command_prefix="!")
decrypted_token = tokeninst.decrypt()
bot.guildlist = []
bot.prefixes = {}

@bot.event
async def on_ready():
    for guild in await bot.fetch_guilds().flatten():
        print("getting prefixes")
        bot.guildlist.append(str(guild.id))
    for each in bot.guildlist:
        print("iterating over guilds")
        if dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False) == "" or dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False) == None:
            bot.prefixes[each] = '!'
        else:
            print("adding prefix to prefixes")
            print(str(dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False)))
            bot.prefixes[each] = (dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False))
    print(str(bot.prefixes))
    
async def reset_prefixes():
    for guild in await bot.fetch_guilds().flatten():
        print("getting prefixes")
        bot.guildlist.append(str(guild.id))
    for each in bot.guildlist:
        print("iterating over guilds")
        if dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False) == "" or dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False) == None:
            bot.prefixes[each] = '!'
        else:
            print("adding prefix to prefixes")
            print(str(dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False)))
            bot.prefixes[each] = (dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False))
    print(str(bot.prefixes))

@bot.event
async def on_message(message):
    if message.author != bot.user:    
        bot.command_prefix = bot.prefixes[str(message.guild.id)]
        print("command prefix is " + bot.command_prefix)
        await bot.process_commands(message)

@bot.command()
async def prefix(ctx, arg):
    await ctx.send("Ok. Changing prefix...")
    if dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(ctx.message.guild.id), False) == "" or dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(ctx.message.guild.id), False) == None:
        bot.prefixes[ctx.guild.id] = arg
        print(str(dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.message.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)))
        await ctx.send("My prefix in this server has been set to `" + str(arg) + "`.")
    

@bot.command()
async def test(ctx):
    print("called test command")
    await ctx.send("Test")
    
print("starting bot")
bot.run(decrypted_token)