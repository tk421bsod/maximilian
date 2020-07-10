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

@bot.command()
async def test(ctx):
    await ctx.send("Test")

bot.run(decrypted_token)