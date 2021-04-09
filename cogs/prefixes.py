import discord
import time
from discord.ext import commands
import logging

class prefixes(commands.Cog):
    '''Change Maximilian's prefix'''
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
    async def _fetch_prefix(self, guild_id):
        prefixindb = self.bot.dbinst.retrieve(self.bot.database, "prefixes", "prefix", "guild_id", str(guild_id), False)
            if prefixindb == "" or prefixindb == None:
                self.bot.prefixes[guild_id] = '!'
            else:
                self.bot.prefixes[guild_id] = prefixindb

    async def update_prefix_cache(self, guild_id=None):
        await self.bot.responsesinst.check_if_ready()
        self.logger.info("updating prefix cache...")
        if guild:
            await _fetch_prefix(guild_id)
        else:
            for id in [guild.id for guild in self.bot.guilds]:
                await _fetch_prefix(guild_id)
        self.logger.info("cache has been updated!")

    async def set_nickname(self, ctx, oldprefix, newprefix):
        if not ctx.guild.me.nick:
            oldnickname = "Maximilian"
        else:
            oldnickname = ctx.guild.me.nick
        if ctx.guild.me.guild_permissions.change_nickname:
            nickname = oldnickname.replace(f"[{oldprefix}] ", "")
            await ctx.guild.me.edit(nick=f"[{newprefix}] {nickname}")
        
    @commands.has_permissions(manage_guild=True)
    @commands.command(help="Set Maximilian's prefix, only works if you have the Manage Server permission", aliases=['prefixes'])
    async def prefix(self, ctx, newprefix):
    #this try/except is to fall back to a default prefix if it isn't in the list for some reason
    #might not be necessary, as a guild's prefix is set to "!" if it's not in the db (lines 15-16 of this file)
    #TODO: rework error handling in common.py
        try:
            oldprefix = self.bot.prefixes[str(ctx.guild.id)]
        except KeyError:
            oldprefix = "!"
        print("changing prefix...")
        await ctx.trigger_typing()
        await ctx.send(f"Ok. Changing prefix to `{str(newprefix)}`...")
        prefixsetmessage = f"My prefix in this server has been set to `{str(newprefix)}` ."
        duplicateprefixmessage = f"My prefix in this server is already `{str(newprefix)}`."
        dbentry = self.bot.dbinst.retrieve(self.bot.database, "prefixes", "prefix", "guild_id", str(ctx.guild.id), False)
        #might need a refactor soon
        if dbentry == "" or dbentry == None:
            print("no db entry found")
            self.bot.prefixes[ctx.guild.id] = newprefix
            result = self.bot.dbinst.insert(self.bot.database, "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(newprefix)}, "guild_id", False, "", False, "", False)
            if result == "success":
                await self.set_nickname(ctx, oldprefix, newprefix)
                await self.update_prefix_cache(ctx.guild.id)
                return await ctx.send(prefixsetmessage)
        elif dbentry == newprefix:
            print("tried to change to same prefix")
            return await ctx.send(duplicateprefixmessage)
        elif dbentry != "" and dbentry != newprefix:
            print("db entry found")
            result = self.bot.dbinst.insert(self.bot.database, "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(newprefix)}, "guild_id", False, "", False, "", False)
            if result == "success":
                await self.set_nickname(ctx, oldprefix, newprefix)
                await self.update_prefix_cache(ctx.guild.id)
                return await ctx.send(prefixsetmessage)
            elif result == "error-duplicate":
                print("there's already an entry for this guild")
                deletionresult = self.bot.dbinst.delete(self.bot.database, "prefixes", str(ctx.guild.id), "guild_id", "", "", False)
                if deletionresult == "successful":
                    result = self.bot.dbinst.insert(self.bot.database, "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(newprefix)}, "guild_id", False, "", False, "", False)
                    if result == "success":
                        await self.set_nickname(ctx, oldprefix, newprefix)
                        await self.update_prefix_cache(ctx.guild.id)
                        return await ctx.send(prefixsetmessage)
            await ctx.send("An error occurred when setting the prefix. Please try again later.")
            return "error"

def setup(bot):
    bot.add_cog(prefixes(bot))

def teardown(bot):
    bot.remove_cog(prefixes(bot))
