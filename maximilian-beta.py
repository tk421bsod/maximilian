import discord
from discord.ext import commands 
from common import db
from common import token
import logging
import time

logging.basicConfig(level=logging.WARN)
tokeninst = token()
dbinst = db()
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=intents)
decrypted_token = tokeninst.decrypt("betatoken.txt")
bot.guildlist = []
bot.prefixes = {}

async def reset_prefixes():
    print("resetting prefixes...")
    if not bot.guildlist:    
        for guild in await bot.fetch_guilds().flatten():
            bot.guildlist.append(str(guild.id))
    for each in bot.guildlist:
        prefixindb = dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False)
        if prefixindb == "" or prefixindb == None:
            bot.prefixes[each] = '!'
        else:
            bot.prefixes[each] = prefixindb
    print(str(bot.prefixes))

@bot.event
async def on_ready():
    await reset_prefixes()
    
@bot.event
async def on_message(message):
    if message.author != bot.user:
        try:    
            bot.command_prefix = bot.prefixes[str(message.guild.id)]
        except KeyError:
            print("Couldn't get prefixes, using default prefix instead")
            bot.command_prefix = "!"
            pass
        print("command prefix is " + bot.command_prefix)
        await bot.process_commands(message)

async def exectime(start_time, ctx):
    await ctx.send("took " + str(round(time.time()-start_time, 2)) + " seconds to execute")

@bot.command()
async def prefix(ctx, arg):
    #should probably make this shorter and eliminate a bunch of those if statements
    if ctx.author.guild_permissions.manage_emojis:
        print("changing prefix...")
        changingprefixmessage = await ctx.send("Ok. Changing prefix...")
        start_time = time.time()
        await ctx.trigger_typing()
        prefixsetmessage = "My prefix in this server has been set to `" + str(arg) + "` ."
        duplicateprefixmessage = "My prefix in this server is already `" + str(arg) + "`."
        dbentry = dbinst.retrieve("maximilian_test", "prefixes", "prefix", "guild_id", str(ctx.guild.id), False)
        if dbentry == "" or dbentry == None:
            print("no db entry found")
            bot.prefixes[ctx.guild.id] = arg
            result = dbinst.insert("maximilian_test", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
            if result == "success":
                print("set prefix")
                await reset_prefixes()
                await ctx.send(prefixsetmessage)
                await exectime(start_time, ctx)
                return "changed prefix"
            else:
                print("error")
                await ctx.send("An error occured while setting the prefix. Please try again later.")
                await exectime(start_time, ctx)
                print(result)
                return "error"
        elif dbentry == arg:
            print("tried to change to same prefix")
            await ctx.send(duplicateprefixmessage)
            await exectime(start_time, ctx)
            return "changed prefix"
        elif dbentry != "" and dbentry != arg:
            print("db entry found")
            result = dbinst.insert("maximilian_test", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
            if result == "success":
                print("set prefix")
                await reset_prefixes()
                await changingprefixmessage.edit(content=prefixsetmessage)
                await exectime(start_time, ctx)
                return "changed prefix"
            elif result == "error-duplicate":
                print("there's already an entry for this guild")
                deletionresult = dbinst.delete("maximilian_test", "prefixes", str(ctx.guild.id), "guild_id")
                if deletionresult == "successful":
                    result = dbinst.insert("maximilian_test", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
                    if result == "success":
                        print("set prefix")
                        await reset_prefixes()
                        await changingprefixmessage.edit(content=prefixsetmessage)
                        await exectime(start_time, ctx)
                    else: 
                        print("error")
                        await changingprefixmessage.edit(content="An error occurred when setting the prefix. Please try again later.")
                        print(deletionresult)
                        await exectime(start_time, ctx)
                        return "error"
                else:
                    print("error")
                    await changingprefixmessage.edit(content="An error occurred when setting the prefix. Please try again later.")
                    print(deletionresult)
                    await exectime(start_time, ctx)
                    return "error"
            else:
                await changingprefixmessage.edit(content="An error occurred when setting the prefix. Please try again later.")
                print(result)
                await exectime(start_time, ctx)
                return "error"
    else:
        await ctx.send("You don't have the permissions required to run this command.")

@bot.event
async def on_command_error(ctx, error):
    await ctx.send("There was an error. Please try again later.")
    await ctx.send("`"+str(error)+"`")

@bot.command()
async def test(ctx):
    print("called test command")
    await ctx.send("Test")
    

@bot.command()
async def owner(ctx):
    await ctx.send("My owner is <@!" + str(bot.owner_id) + "> !")
    
@bot.event
async def on_guild_join(guild):
    print("joined guild, adding guild id to list of guilds")
    bot.guildlist.append(str(guild.id))
    reset_prefixes()    

print("starting bot")
bot.run(decrypted_token)