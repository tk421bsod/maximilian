import discord
import time
from discord.ext import commands

class prefixes(commands.Cog):
    '''Prefix-related commands'''
    def __init__(self, bot):
        self.bot = bot

    async def reset_prefixes(self):
        print("resetting prefixes...")
        if not self.bot.guildlist:    
            for guild in await self.bot.fetch_guilds().flatten():
                self.bot.guildlist.append(str(guild.id))
        for each in self.bot.guildlist:
            prefixindb = self.bot.dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False)
            if prefixindb == "" or prefixindb == None:
                self.bot.prefixes[each] = '!'
            else:
                self.bot.prefixes[each] = prefixindb
        print("reset prefixes")

    @commands.command(help="Set Maximilian's prefix, only works if you're an admin", aliases=['prefixes'])
    async def prefix(self, ctx, arg):
        #should probably make this shorter and eliminate a bunch of those if statements
        if ctx.author.guild_permissions.administrator or ctx.author.id == self.bot.owner_id:
            print("changing prefix...")
            changingprefixmessage = await ctx.send(f"Ok. Changing prefix to `{str(arg)}`...")
            start_time = time.time()
            await ctx.trigger_typing()
            prefixsetmessage = f"My prefix in this server has been set to `{str(arg)}` ."
            duplicateprefixmessage = f"My prefix in this server is already `{str(arg)}`."
            dbentry = self.bot.dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(ctx.guild.id), False)
            if dbentry == "" or dbentry == None:
                print("no db entry found")
                self.bot.prefixes[ctx.guild.id] = arg
                result = self.bot.dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
                if result == "success":
                    print("set prefix")
                    await self.reset_prefixes()
                    await changingprefixmessage.edit(content=prefixsetmessage)
                    await self.bot.miscinst.exectime(start_time, ctx)
                    return "changed prefix"
                else:
                    print("error")
                    await ctx.send("An error occured while setting the prefix. Please try again later.")
                    await self.bot.miscinst.exectime(start_time, ctx)
                    print(result)
                    return "error"
            elif dbentry == arg:
                print("tried to change to same prefix")
                await ctx.send(duplicateprefixmessage)
                await self.bot.miscinst.exectime(start_time, ctx)
                return "changed prefix"
            elif dbentry != "" and dbentry != arg:
                print("db entry found")
                result = self.bot.dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
                if result == "success":
                    print("set prefix")
                    await self.reset_prefixes()
                    await changingprefixmessage.edit(content=prefixsetmessage)
                    await self.bot.miscinst.exectime(start_time, ctx)
                    return "changed prefix"
                elif result == "error-duplicate":
                    print("there's already an entry for this guild")
                    deletionresult = self.bot.dbinst.delete("maximilian", "prefixes", str(ctx.guild.id), "guild_id", "", "", False)
                    if deletionresult == "successful":
                        result = self.bot.dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
                        if result == "success":
                            print("set prefix")
                            await self.reset_prefixes()
                            await changingprefixmessage.edit(content=prefixsetmessage)
                            await self.bot.miscinst.exectime(start_time, ctx)
                        else: 
                            print("error")
                            await changingprefixmessage.edit(content="An error occurred when setting the prefix. Please try again later.")
                            print(result)
                            await self.bot.miscinst.exectime(start_time, ctx)
                            return "error"
                    else:
                        print("error")
                        await changingprefixmessage.edit(content="An error occurred when setting the prefix. Please try again later.")
                        print(deletionresult)
                        await self.bot.miscinst.exectime(start_time, ctx)
                        return "error"
                else:
                    await changingprefixmessage.edit(content="An error occurred when setting the prefix. Please try again later.")
                    print(result)
                    await self.bot.miscinst.exectime(start_time, ctx)
                    return "error"
        else:
            await ctx.send("You don't have the permissions required to run this command.")

def setup(bot):
    bot.add_cog(prefixes(bot))

def teardown(bot):
    bot.remove_cog(prefixes(bot))