import discord
import time
from discord.ext import commands

class prefixes(commands.Cog):
    '''Change Maximilian's prefix'''
    def __init__(self, bot):
        self.bot = bot

    async def reset_prefixes(self):
        print("resetting prefixes...")
        if not self.bot.guildlist:    
            for guild in await self.bot.fetch_guilds().flatten():
                self.bot.guildlist.append(str(guild.id))
        for each in self.bot.guildlist:
            prefixindb = self.bot.dbinst.retrieve(self.bot.database, "prefixes", "prefix", "guild_id", str(each), False)
            if prefixindb == "" or prefixindb == None:
                self.bot.prefixes[each] = '!'
            else:
                self.bot.prefixes[each] = prefixindb
        print("reset prefixes")

    @commands.has_permissions(manage_guild=True)
    @commands.command(help="Set Maximilian's prefix, only works if you have the Manage Server permission", aliases=['prefixes'])
    async def prefix(self, ctx, newprefix):
    #should probably make this shorter and eliminate a bunch of those if statements
        oldprefix = self.bot.command_prefix
        print("changing prefix...")
        await ctx.trigger_typing()
        await ctx.send(f"Ok. Changing prefix to `{str(newprefix)}`...")
        prefixsetmessage = f"My prefix in this server has been set to `{str(newprefix)}` ."
        duplicateprefixmessage = f"My prefix in this server is already `{str(newprefix)}`."
        dbentry = self.bot.dbinst.retrieve(self.bot.database, "prefixes", "prefix", "guild_id", str(ctx.guild.id), False)
        if dbentry == "" or dbentry == None:
            print("no db entry found")
            self.bot.prefixes[ctx.guild.id] = newprefix
            result = self.bot.dbinst.insert(self.bot.database, "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(newprefix)}, "guild_id", False, "", False, "", False)
            if result == "success":
                if ctx.guild.me.nick == None:
                    oldnickname = "Maximilian"
                else:
                    oldnickname = ctx.guild.me.nick
                if ctx.guild.me.guild_permissions.change_nickname and ctx.prefix is not None:
                    nickname = oldnickname.replace(f"[{ctx.prefix}] ", "")
                    await ctx.guild.me.edit(nick=f"[{newprefix}] {nickname}")
                elif ctx.guild.me.guild_permissions.change_nickname and ctx.prefix == None:
                    nickname = oldnickname.replace(f"[{oldprefix}] ", "")
                    await ctx.guild.me.edit(nick=f"[{newprefix}] {nickname}")
                await self.reset_prefixes()
                await ctx.send(prefixsetmessage)
                return "changed prefix"
            else:
                print("error")
                await ctx.send("An error occured while setting the prefix. Please try again later.")
                print(result)
                return "error"
        elif dbentry == newprefix:
            print("tried to change to same prefix")
            await ctx.send(duplicateprefixmessage)
            return "changed prefix"
        elif dbentry != "" and dbentry != newprefix:
            print("db entry found")
            result = self.bot.dbinst.insert(self.bot.database, "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(newprefix)}, "guild_id", False, "", False, "", False)
            if result == "success":
                if ctx.guild.me.nick == None:
                    oldnickname = "Maximilian"
                else:
                    oldnickname = ctx.guild.me.nick
                if ctx.guild.me.guild_permissions.change_nickname and ctx.prefix is not None:
                    nickname = oldnickname.replace(f"[{ctx.prefix}] ", "")
                    await ctx.guild.me.edit(nick=f"[{newprefix}] {nickname}")
                elif ctx.guild.me.guild_permissions.change_nickname and ctx.prefix == None:
                    nickname = oldnickname.replace(f"[{oldprefix}] ", "")
                    await ctx.guild.me.edit(nick=f"[{newprefix}] {nickname}")
                await self.reset_prefixes()
                await ctx.send(prefixsetmessage)
                return "changed prefix"
            elif result == "error-duplicate":
                print("there's already an entry for this guild")
                deletionresult = self.bot.dbinst.delete(self.bot.database, "prefixes", str(ctx.guild.id), "guild_id", "", "", False)
                if deletionresult == "successful":
                    result = self.bot.dbinst.insert(self.bot.database, "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(newprefix)}, "guild_id", False, "", False, "", False)
                    if result == "success":
                        print("set prefix")
                        if ctx.guild.me.nick == None:
                            oldnickname = "Maximilian"
                        else:
                            oldnickname = ctx.guild.me.nick
                        if ctx.guild.me.guild_permissions.change_nickname and ctx.prefix is not None:
                            nickname = oldnickname.replace(f"[{ctx.prefix}] ", "")
                            await ctx.guild.me.edit(nick=f"[{newprefix}] {nickname}")
                        elif ctx.guild.me.guild_permissions.change_nickname and ctx.prefix == None:
                            nickname = oldnickname.replace(f"[{oldprefix}] ", "")
                            await ctx.guild.me.edit(nick=f"[{newprefix}] {nickname}")
                        await self.reset_prefixes()
                        await ctx.send(prefixsetmessage)
                        return "success"
                    else: 
                        print("error")
                        await ctx.send("An error occurred when setting the prefix. Please try again later.")
                        print(result)
                        return "error"
                else:
                    print("error")
                    await ctx.send("An error occurred when setting the prefix. Please try again later.")
                    print(deletionresult)
                    return "error"
            else:
                await ctx.send("An error occurred when setting the prefix. Please try again later.")
                print(result)
                return "error"

def setup(bot):
    bot.add_cog(prefixes(bot))

def teardown(bot):
    bot.remove_cog(prefixes(bot))
