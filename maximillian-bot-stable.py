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
    print("getting prefixes...")
    for guild in await bot.fetch_guilds().flatten():
        bot.guildlist.append(str(guild.id))
    for each in bot.guildlist:
        if dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False) == "" or dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False) == None:
            bot.prefixes[each] = '!'
        else:
            bot.prefixes[each] = (dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False))
    print(str(bot.prefixes))
    
async def reset_prefixes():
    print("resetting prefixes...")
    for guild in await bot.fetch_guilds().flatten():
        bot.guildlist.append(str(guild.id))
    for each in bot.guildlist:
        if dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False) == "" or dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False) == None:
            bot.prefixes[each] = '!'
        else:
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
    if dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(ctx.guild.id), False) == "" or dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(ctx.guild.id), False) == None:
        bot.prefixes[ctx.guild.id] = arg
        result = dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
        if result == "success":
            await reset_prefixes()
            await ctx.send("My prefix in this server has been set to `" + str(arg) + "`.")
            return "changed prefix"
        else:
            await ctx.send("An error occured while setting the prefix. Please try again later.")
            print(result)
            return "error"
    elif dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(ctx.guild.id), False) == arg:
        await reset_prefixes()
        await ctx.send("My prefix in this server is already " + str(arg) + ".")
        return "changed prefix"
    elif dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(ctx.guild.id), False) != "" and dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(ctx.guild.id), False) != arg:
        result = dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
        if result == "success":
            await reset_prefixes()
            await ctx.send("My prefix in this server has been set to `" + str(arg) + "` .")
            return "changed prefix"
        elif result == "error-duplicate":
            deletionresult = dbinst.delete("maximilian", "prefixes", str(ctx.guild.id), "guild_id")
            if deletionresult == "successful":
                result = dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
                if result == "success":
                    await reset_prefixes()
                    await ctx.send("My prefix in this server has been set to `" + str(arg) + "` .")
                else: 
                    await ctx.send("An error occurred when setting the prefix. Please try again later.")
                    print(result)
                    return "error"
            else:
                await ctx.send("An error occurred when setting the prefix. Please try again later.")
                print(deletionresult)
                return "error"
        else:
            await ctx.send("An error occurred when setting the prefix. Please try again later.")
            print(result)
            return "error"

@bot.command()
async def test(ctx):
    print("called test command")
    await ctx.send("Test")

print("starting bot")
bot.run(decrypted_token)