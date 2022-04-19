import logging
import time

import discord
from discord.ext import commands


class prefixes(commands.Cog):
    '''Change Maximilian's prefix'''
    def __init__(self, bot, load=False):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        if load:
            self.bot.loop.create_task(self.update_prefix_cache())
        
    def _get_prefix_if_exists(self, guild):
        try:
            return self.bot.prefixes[guild.id]
        except KeyError:
            return "!"
        
    def _is_prefix_same(self, guild, prefix):
        return self._get_prefix_if_exists(guild) == prefix
        
    async def _fetch_prefix(self, guild_id):
        '''Fetches a prefix corresponding to a guild id from the database'''
        prefix = self.bot.dbinst.exec_safe_query("select prefix from prefixes where guild_id = %s", (guild_id))
        if not prefix and prefix != () and prefix != "()":
            self.bot.prefixes[guild_id] = '!'
        else:
            self.bot.prefixes[guild_id] = prefix['prefix']

    async def update_prefix_cache(self, guild_id=None):
        '''Builds/updates cache of prefixes'''
        await self.bot.wait_until_ready()
        self.logger.info("updating prefix cache...")
        if guild_id:
            await self._fetch_prefix(guild_id)
        else:
            for id in [guild.id for guild in self.bot.guilds]:
                await self._fetch_prefix(id)
                try:
                    self.bot.prefixes[id]
                except KeyError:
                    self.bot.prefixes[id] = "!"
        self.logger.info("cache has been updated!")
        print(self.bot.prefixes)
        
    @commands.has_permissions(manage_guild=True)
    @commands.command(help="Set Maximilian's prefix, only works if you have the Manage Server permission. ", aliases=['prefixes'])
    async def prefix(self, ctx, new_prefix):
        if not ctx.guild:
            return await ctx.send("You can't change my prefix in a DM.")
        if self._is_prefix_same(ctx.guild, new_prefix):
            return await ctx.send(f"My prefix in this server is already set to `{new_prefix}`!")
        await ctx.send(f"Ok. Changing prefix to {new_prefix}...")
        if self.bot.dbinst.exec_safe_query("select * from prefixes where guild_id = %s", (ctx.guild.id, )):
            self.bot.dbinst.exec_safe_query("update prefixes set prefix = %s where guild_id = %s", (new_prefix, ctx.guild.id))
        else:
            self.bot.dbinst.exec_safe_query("insert into prefixes values(%s, %s)", (ctx.guild.id, new_prefix))
        await self.update_prefix_cache(ctx.guild.id)
        await ctx.send(f"Set my prefix to `{new_prefix}`.")
              
            

async def setup(bot):
    await bot.add_cog(prefixes(bot, True))

async def teardown(bot):
    await bot.remove_cog(prefixes(bot))

