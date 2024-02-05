import asyncio
import logging
import time

import discord
from discord.ext import commands


class prefixes(commands.Cog):
    '''Change Maximilian's prefix'''
    __slots__ = ("bot", "logger")

    def __init__(self, bot, load=False):
        bot.prefix = {}
        bot.prefixes = self
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        if load:
            asyncio.create_task(self.update_prefix_cache())

    def _is_prefix_same(self, guild, prefix):
        return self.bot.common.get_value(self.bot.prefix, guild.id, "!") == prefix

    async def update_prefix_cache(self, guild_id=None):
        '''Builds/updates cache of prefixes'''
        await self.bot.wait_until_ready()
        self.logger.info("updating prefix cache...")
        prefixes = await self.bot.db.exec("select * from prefixes", ())
        for prefix in prefixes:
            self.bot.prefix[prefix['guild_id']] = prefix['prefix']
        for guild in self.bot.guilds:
            if self.bot.common.get_value(self.bot.prefix, guild.id) is None:
                self.bot.prefix[guild.id] = "!"
        self.logger.info("cache has been updated!")

    @commands.has_permissions(manage_guild=True)
    @commands.command(help="Set Maximilian's prefix, only works if you have the Manage Server permission. ", aliases=['prefixes'])
    async def prefix(self, ctx, new_prefix):
        if not ctx.guild:
            return await ctx.send(self.bot.strings["ERROR_DM"])
        if self._is_prefix_same(ctx.guild, new_prefix):
            return await ctx.send(self.bot.strings["PREFIX_SAME"].format(new_prefix))
        await ctx.send(self.bot.strings["CHANGING_PREFIX"].format(new_prefix))
        if await self.bot.db.exec("select * from prefixes where guild_id = %s", (ctx.guild.id, )):
            await self.bot.db.exec("update prefixes set prefix = %s where guild_id = %s", (new_prefix, ctx.guild.id))
        else:
            await self.bot.db.exec("insert into prefixes values(%s, %s)", (ctx.guild.id, new_prefix))
        self.bot.prefix[ctx.guild.id] = new_prefix
        await ctx.send(self.bot.strings["PREFIX_SET"].format(new_prefix))

async def setup(bot):
    await bot.add_cog(prefixes(bot, True))

async def teardown(bot):
    await bot.remove_cog(prefixes(bot))

