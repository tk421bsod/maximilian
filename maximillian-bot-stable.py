import discord
from discord.ext import commands 
from common import db
from common import token

tokeninst = token()
dbinst = db()
client = discord.Client()
bot = discord.ext.commands()
decrypted_token = tokeninst.decrypt()

client.run(decrypted_token.decode())