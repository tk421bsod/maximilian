import asyncio
import typing
import traceback

import discord
from discord.ext import commands

class settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def config(self, ctx, category:str=None, *, setting:str=None):
        '''Change Maximilian\'s settings'''
        #reading the source code? this cog is just a wrapper for the config method(s) in settings.py.
        await self.bot.settings.config(ctx, category, setting=setting)


async def setup(bot):
    await bot.add_cog(settings(bot))
