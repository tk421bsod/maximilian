import discord
from discord.ext import commands 
from common import db
from common import token
import logging

logging.basicConfig(level=logging.INFO)
tokeninst = token()
dbinst = db()
client = discord.Client()
bot = discord.ext.commands()
decrypted_token = tokeninst.decrypt()


client.run(decrypted_token.decode())