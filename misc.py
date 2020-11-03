import discord
from discord.ext import commands
import time
import aiohttp
import io
from zalgo_text import zalgo as zalgo_text_gen

class misc(commands.Cog):
    '''Some commands that don\'t really fit into other categories'''
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["owner"])
    async def hi(self, ctx):
        await ctx.send("Hello! I'm a robot. tk421#7244 made me!")

    @commands.command(help="zalgo text")
    async def zalgo(self, ctx, *, arg):
        await ctx.send(zalgo_text_gen.zalgo().zalgofy(str(arg)))

    @commands.command(help="Get an image of a cat. The image is generated by AI, therefore it's an image of a cat that doesn't exist", aliases=["cats"])
    async def thiscatdoesntexist(self, ctx):
        await ctx.trigger_typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://thiscatdoesnotexist.com') as r:
                buffer = io.BytesIO(await r.read())
                await ctx.send(file=discord.File(buffer, filename="cat.jpeg"))

    async def exectime(self, start_time, ctx):
        await ctx.send(f"took {str(round(time.time()-start_time, 2))} seconds to execute")

    @commands.command(aliases=['pong'])
    async def ping(self, ctx):
        await ctx.send(f"Pong! My latency is {str(round(self.bot.latency*1000, 1))} ms.")

    @commands.command(help="Get some info about the bot and commands")
    async def about(self, ctx):
        embed = discord.Embed(title="About", color=discord.Color.blurple())
        embed.add_field(name="Useful links", value=f"Use `{str(self.bot.command_prefix)}help command` for more info on a certain command. \n For more help, join the support server at https://discord.gg/PJ94gft. \n To add Maximilian to your server, with only the required permissions, click [here](https://discord.com/api/oauth2/authorize?client_id=620022782016618528&permissions=268815456&scope=bot).", inline=False)
        embed.add_field(name="Fun Commands", value="Commands that have no purpose. \n `zalgo` `cats` `ping`", inline=True)
        embed.add_field(name="Other Commands", value="Commands that actually have a purpose. \n `about` `help` `userinfo` `reactionroles` `responses` `prefix` `listprefixes` `hi`", inline=True)
        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def lc(self, ctx):
        await ctx.send("I am made of 636 lines of Python, spread across 7 files. \n Files (sorted by number of lines): common.py (159), main.py (122), prefixes.py (98), responses.py (69), reactionroles.py (65), userinfo.py (63), misc.py (60) ")

def setup(bot):
    bot.add_cog(misc(bot))

def teardown(bot):
    bot.remove_cog(misc(bot))