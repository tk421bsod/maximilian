import discord
from discord.ext import commands

class config(commands.Cog):
    '''Change Maximilian\'s settings (changes only apply to you or your server)'''
    def __init__(self, bot):
        self.bot = bot
        self.bot.timezones = {}
    
    @commands.command(help="Set or change your time zone.")
    async def tzsetup():
        raise NotImplemented

def setup(bot):
    bot.add_cog(config(bot))

def teardown(bot):
    bot.remove_cog(config(bot))