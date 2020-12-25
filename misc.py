import discord
from discord.ext import commands
import time
import aiohttp
import io
import asyncio
from zalgo_text import zalgo as zalgo_text_gen
import typing

class misc(commands.Cog):
    '''Some commands that don\'t really fit into other categories'''
    def __init__(self, bot):
        self.bot = bot
        self.bot.waiting_for_reaction = False

    @commands.command(aliases=["owner"])
    async def hi(self, ctx):
        print("said hi")
        await ctx.send("Hello! I'm a robot. tk421#7244 made me!")

    @commands.command(help="zalgo text")
    async def zalgo(self, ctx, *, arg):
        print("generated zalgo text")
        await ctx.send(zalgo_text_gen.zalgo().zalgofy(str(arg)))

    @commands.command(help="Get an image of a cat.", aliases=["cats"])
    async def thiscatdoesntexist(self, ctx):
        await ctx.trigger_typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://thiscatdoesnotexist.com') as r:
                buffer = io.BytesIO(await r.read())
                print("got a cat image")
                await ctx.send(file=discord.File(buffer, filename="cat.jpeg"))

    @commands.command(aliases=['pong'])
    async def ping(self, ctx):
        print("sent latency")
        await ctx.send(f"Pong! My latency is {str(round(self.bot.latency*1000, 1))} ms.")

    @commands.command(help="Get some info about the bot and commands")
    async def about(self, ctx):
        embed = discord.Embed(title="About", color=discord.Color.blurple())
        embed.add_field(name="Useful links", value=f"Use `{str(self.bot.command_prefix)}help command` for more info on a certain command. \n For more help, join the support server at https://discord.gg/PJ94gft. \n To add Maximilian to your server, with only the required permissions, click [here](https://discord.com/api/oauth2/authorize?client_id=620022782016618528&permissions=335923264&scope=bot).", inline=False)
        embed.add_field(name="Fun Commands", value="Commands that have no purpose. \n `zalgo` `cats` `ping`", inline=True)
        embed.add_field(name="Other Commands", value="Commands that actually have a purpose. \n `about` `help` `userinfo` `reactionroles` `responses` `prefix` `listprefixes` `hi`", inline=True)
        print("sent some info about me")
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def listguildnames(self, ctx):
        guildstring = ""
        for each in self.bot.guilds:
            guildstring = guildstring + each.name + "(" + str(len(list(each.members))) + " members), "
        await ctx.send("Guilds: " + guildstring[:-2])

    @commands.command(help="View information about what data Maximilian accesses and stores.")
    async def privacy(self, ctx):
        embed = discord.Embed(title="Maximilian Privacy Policy", color=discord.Color.blurple())
        embed.add_field(name="Why Maximilian collects data", value="Maximilian collects certain information that is necessary for its functions (types of data collected are described below)", inline=False)
        embed.add_field(name="Data that Maximilian collects", value="**-Server IDs**\nMaximilian collects server IDs when you create a custom command or add a reaction role to distinguish between different servers.\n\n**-Role IDs**\nMaximilian collects role IDs whenever you add a reaction role so it can assign the correct role to users.\n\n**-User Info**\nTo provide the userinfo command, Maximilian accesses, but doesn't store, certain data about users like their roles, permissions, status, and account age.", inline=False)
        embed.add_field(name="I want to delete my data, how do I request that?", value=f"You can delete all the data in your server by using `{self.bot.command_prefix}deleteall`. This will irreversibly delete all of the reaction roles and custom commands you have set up and reset the prefix to the default of `!`. Only people with the Administrator permission can use this.", inline=False)
        await ctx.send(embed=embed)

    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.command(help="**Permanently** delete all data that Maximilian's stored about your server. (requires the Administrator permission)")
    async def deleteall(self, ctx):
        if not self.bot.waiting_for_reaction:
            embed = discord.Embed(title="Delete all data?", description=f"You've requested that I delete all the information I have stored about this server. (see `{self.bot.command_prefix}privacy` for details on the data I collect)", color=discord.Color.blurple())
            embed.add_field(name="Effects", value="If you proceed, all of the reaction roles and custom commands you've set up will be deleted, and my prefix will be reset to `!`.\n**THIS CANNOT BE UNDONE.**", inline=False)
            embed.add_field(name="Your options", value="React with \U00002705 to proceed, or react with \U0000274c to stop the deletion process.", inline=False)
            deletionmessage = await ctx.send(embed=embed)
            await deletionmessage.add_reaction("\U00002705")
            await deletionmessage.add_reaction("\U0000274c")
            try:
                await asyncio.sleep(1)
                while True:
                    self.bot.waiting_for_reaction = True
                    reaction = await self.bot.wait_for('reaction_add', timeout=120.0)
                    async for each in reaction[0].users():
                        if ctx.message.author == each:
                            self.bot.waiting_for_reaction = False
                            if str(reaction[0].emoji) == '\U00002705':
                                await ctx.send("Deleting data for this server...")
                                await ctx.trigger_typing()
                                self.bot.dbinst.delete(self.bot.database, "roles", str(ctx.guild.id), "guild_id", "", "", False)
                                self.bot.dbinst.delete(self.bot.database, "responses", str(ctx.guild.id), "guild_id", "", "", False)
                                self.bot.dbinst.delete(self.bot.database, "prefixes", str(ctx.guild.id), "guild_id", "", "", False)
                                await ctx.guild.me.edit(nick=f"[!] Maximilian")
                                await self.bot.responsesinst.get_responses()
                                await self.bot.prefixesinst.reset_prefixes()
                                embed = discord.Embed(title="\U00002705 All data for this server has been cleared!", color=discord.Color.blurple())
                                await ctx.send(embed=embed)
                                return
                            if str(reaction[0].emoji) == '\U0000274c':
                                await ctx.send("Ok. I won't delete anything.")
                                return
            except asyncio.TimeoutError:
                self.bot.waiting_for_reaction = False
                await ctx.send('Deletion request timed out.')
        else:
            await ctx.send("It looks like you already have an active deletion request.")

    @commands.command(hidden=True)
    async def emojitest(self, ctx, emoji : typing.Optional[typing.Union[discord.PartialEmoji, str]]=None):
        print(str(emoji))
        if isinstance(emoji, discord.PartialEmoji):
            await ctx.send(f"`<{emoji.name}:{emoji.id}>`")
            return
        await ctx.send(f"`{emoji}`")


def setup(bot):
    bot.add_cog(misc(bot))

def teardown(bot):
    bot.remove_cog(misc(bot))