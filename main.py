import discord
from discord.ext import commands 
import common
import importlib
import logging
import time
import calendar
import os

logging.basicConfig(level=logging.WARN)
print("starting...")
tokeninst = common.token()
decrypted_token = tokeninst.decrypt("token.txt")
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="myself start up!"))
bot.guildlist = []
bot.prefixes = {}
bot.responses = []
bot.dbinst = common.db()
bot.load_extension('responses')
bot.load_extension('prefixes')
bot.load_extension('misc')
bot.load_extension('reactionroles')
bot.responsesinst = bot.get_cog('responses')
bot.prefixesinst = bot.get_cog('prefixes')
bot.miscinst = bot.get_cog('misc')
bot.reactionrolesinst = bot.get_cog('reactionroles')
print('loaded extensions')

async def startup():
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds!"))

@bot.event
async def on_ready():
    await bot.prefixesinst.reset_prefixes()
    await bot.responsesinst.get_responses()
    bot.loop.create_task(startup())
    print("ready")
    
@bot.event
async def on_message(message):
    if message.author != bot.user:
        if message.content.startswith('<@!620022782016618528> '):
            bot.command_prefix = '<@!620022782016618528> '
        else:
            if message.guild is not None:
                try:    
                    bot.command_prefix = bot.prefixes[str(message.guild.id)]
                except KeyError:
                    print("Couldn't get prefixes, using default prefix instead")
                    bot.command_prefix = "!"
                    pass
                for each in range(len(bot.responses)):
                    if int(bot.responses[each][0]) == int(message.guild.id):
                        if bot.responses[each][1] == message.content.replace(bot.command_prefix, ""):
                            await message.channel.send(bot.responses[each][2])
                            return
        await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    await ctx.send("There was an error. Please try again later.")
    await ctx.send(f"`{error}`")

@bot.command(help="Get a new list of custom responses after adding a new response", aliases=['fetchresponses', 'getresponses'])
async def fetch_responses(ctx):
    gettingresponsesmessage = await ctx.send("Getting a new list of responses...")
    await bot.responsesinst.get_responses()
    await gettingresponsesmessage.edit(content="Got a new list of responses!")

@bot.command(help="List all prefixes")
async def listprefixes(ctx):
    prefixstring = ""
    for key in bot.prefixes.keys():
        if key == str(ctx.message.guild.id):
            prefixstring = prefixstring + "`" + bot.prefixes[key] + "`"
    await ctx.send("My prefixes in this server are " + prefixstring + " and <@!620022782016618528>")


@bot.event
async def on_guild_join(guild):
    print("joined guild, adding guild id to list of guilds and resetting prefixes")
    bot.guildlist.append(str(guild.id))
    await bot.prefixesinst.reset_prefixes()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds!"))


@commands.is_owner()
@bot.command(hidden=True)
async def reloadall(ctx):
    reloadmessage = await ctx.send("Reloading extensions...")
    await ctx.trigger_typing()
    start_time = time.time()
    os.system("git pull")
    commoninst=importlib.reload(common)
    bot.dbinst = commoninst.db()
    bot.reload_extension('responses')
    bot.reload_extension('prefixes')
    bot.reload_extension('misc')
    bot.reload_extension('reactionroles')
    bot.responsesinst = bot.get_cog('responses')
    bot.prefixesinst = bot.get_cog('prefixes')
    bot.miscinst = bot.get_cog('misc')
    bot.reactionrolesinst = bot.get_cog('reactionroles')
    await reloadmessage.edit(content="Reloaded extensions!")
    await bot.miscinst.exectime(start_time, ctx)

@commands.is_owner()
@bot.command(hidden=True)
async def reload(ctx, *targetextensions):
    reloadmessage = await ctx.send("Fetching latest revision...")
    await ctx.trigger_typing()
    os.system("git pull")
    await reloadmessage.edit(content="Fetched latest revision! Reloading extensions...")
    try:
        for each in targetextensions:
            bot.reload_extension(each)
        bot.responsesinst = bot.get_cog('responses')
        bot.prefixesinst = bot.get_cog('prefixes')
        bot.miscinst = bot.get_cog('misc')
        bot.reactionrolesinst = bot.get_cog('reactionroles')
    except Exception as e:
        embed = discord.Embed(title=f"\U0000274e Error while reloading extensions: {str(e)}")
    embed = discord.Embed(title=f"\U00002705 Successfully reloaded {str(len(targetextensions))} extensions.", color=discord.Color.blurple())
    await ctx.send(embed=embed) 

bot.run(decrypted_token)
