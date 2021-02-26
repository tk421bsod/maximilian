import discord
from discord.ext import commands
import typing
from polaroid import Image
import random

class images(commands.Cog):
    '''Apply different effects to images.'''
    def __init__(self, bot):
        self.bot = bot

    async def _get_avatar(self, ctx, user):
        if not user:
            avatar_bytes = await ctx.author.avatar_url_as(static_format="png").read()
            id = ctx.author.id
        else:
            avatar_bytes = await user.avatar_url_as(static_format="png").read()
            id = user.id
        return avatar_bytes, id
        

    @commands.command()
    async def avatar(self, ctx, user:typing.Optional[discord.Member]=None):
        '''View another user's avatar, or yours if you don't specify anyone'''
        if not user:
            await ctx.send(embed=discord.Embed(title=f"{ctx.author}'s avatar", color=discord.Color.blurple()).set_image(url=str(ctx.author.avatar_url)))
            return
        await ctx.send(embed=discord.Embed(title=f"{user}'s avatar", color=discord.Color.blurple()).set_image(url=str(user.avatar_url)))

    @commands.command()
    async def invert(self, ctx, user:typing.Optional[discord.Member]=None):
        '''Invert someone's avatar. Defaults to yours if you don't specify a user.'''
        avatar_bytes, id = await self._get_avatar(ctx, user)
        im = Image(avatar_bytes)
        im_inverted = await self.bot.loop.run_in_executor(None, im.invert)
        im.save(f"imgcache/{id}.png")
        await ctx.send(file=discord.File(f"imgcache/{id}.png"))

    @commands.command()
    async def blur(self, ctx, user:typing.Optional[discord.Member]=None):
        '''Blur someone's avatar. Defaults to yours if you don't specify a user.'''
        avatar_bytes, id = await self._get_avatar(ctx, user)
        im = Image(avatar_bytes)
        im_blurred = await self.bot.loop.run_in_executor(None, im.gaussian_blur, 5)
        im.save(f"imgcache/{id}.png")
        await ctx.send(file=discord.File(f"imgcache/{id}.png"))

    @commands.command(aliases=["so"])
    async def solarize(self, ctx, user:typing.Optional[discord.Member]=None):
        '''Add a washed out look to someone's avatar. (not sure how else to explain this) Defaults to yours if you don't specify a user.'''
        avatar_bytes, id = await self._get_avatar(ctx, user)
        im = Image(avatar_bytes)
        im_blurred = await self.bot.loop.run_in_executor(None, im.solarize)
        im.save(f"imgcache/{id}.png")
        await ctx.send(file=discord.File(f"imgcache/{id}.png"))

    @commands.command()
    async def noise(self, ctx, user:typing.Optional[discord.Member]=None):
        '''Add noise to someone's avatar. Defaults to yours if you don't specify a user.'''
        avatar_bytes, id = await self._get_avatar(ctx, user)
        im = Image(avatar_bytes)
        im_blurred = await self.bot.loop.run_in_executor(None, im.add_noise_rand)
        im.save(f"imgcache/{id}.png")
        await ctx.send(file=discord.File(f"imgcache/{id}.png"))
    
    @commands.command()
    async def colorize(self, ctx, user:typing.Optional[discord.Member]=None):
        '''Attempt to colorize someone's avatar. Defaults to yours if you don't specify a user.'''
        avatar_bytes, id = await self._get_avatar(ctx, user)
        im = Image(avatar_bytes)
        im_blurred = await self.bot.loop.run_in_executor(None, im.colorize)
        im.save(f"imgcache/{id}.png")
        await ctx.send(file=discord.File(f"imgcache/{id}.png"))
    
    @commands.command()
    async def gradient(self, ctx, user:typing.Optional[discord.Member]=None):
        '''Apply a rainbow gradient to someone's avatar. Defaults to yours if you don't specify a user.'''
        avatar_bytes, id = await self._get_avatar(ctx, user)
        im = Image(avatar_bytes)
        im_blurred = await self.bot.loop.run_in_executor(None, im.apply_gradient)
        im.save(f"imgcache/{id}.png")
        await ctx.send(file=discord.File(f"imgcache/{id}.png"))

    @commands.command(hidden=True)
    async def imagetest(self, ctx):
        avatar_bytes, id = await self._get_avatar(ctx, None)
        im = Image(avatar_bytes)
        im.save(f"imgcache/{id}.png")
        await ctx.send(file=discord.File(f"imgcache/{id}.png"))

def setup(bot):
    bot.add_cog(images(bot))

def teardown(bot):
    bot.remove_cog(images(bot))
