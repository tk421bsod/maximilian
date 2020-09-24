import discord
from discord.ext import commands 
from common import db
from common import token
import logging

logging.basicConfig(level=logging.DEBUG)
tokeninst = token()
dbinst = db()
bot = commands.Bot(command_prefix='!')
decrypted_token = tokeninst.decrypt()
bot.guildlist = []

@bot.event
async def on_ready():
    try:
        async for guild in bot.fetch_guilds():
            bot.guildlist.append(str(guild.id))
    except Exception as e:
        print(e)
        bot.prefix = '!'

@bot.command()
async def test(ctx):
    await ctx.send("Test")

bot.run(decrypted_token)