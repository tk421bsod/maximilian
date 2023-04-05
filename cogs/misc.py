import inspect
import io
import os
import sys
import typing

import aiohttp
import discord
from discord.ext import commands

class misc(commands.Cog):
    '''Some commands that don\'t really fit into other categories'''
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["owner"])
    async def hi(self, ctx):
        await ctx.send(self.bot.strings["HELLO"])

    @commands.command(help="Get an image of a cat.", aliases=["thiscatdoesntexist"])
    async def cats(self, ctx):
        await ctx.typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://thiscatdoesnotexist.com') as r:
                buffer = io.BytesIO(await r.read())
                await ctx.send(file=discord.File(buffer, filename="cat.jpeg"))

    async def ping(self, ctx):
        await ctx.send(self.bot.strings["LATENCY"])

    @commands.command(help="Get some info about the bot and commands")
    async def about(self, ctx):
        embed = discord.Embed(title=self.bot.strings["ABOUT_TITLE"], color=self.bot.config['theme_color'])
        embed.add_field(name=self.bot.strings["ABOUT_SUMMARY_TITLE"], value=self.bot.strings["ABOUT_SUMMARY_TEXT"])
        embed.add_field(name=self.bot.strings["ABOUT_LATESTUPDATE_TITLE"], value=self.bot.strings["ABOUT_LATESTUPDATE_TEXT"])
        embed.add_field(name=self.bot.strings["ABOUT_HELP_TITLE"], value=self.bot.strings["ABOUT_HELP_TEXT"].format(str(await self.bot.get_prefix(ctx.message))), inline=False)
        embed.add_field(name=self.bot.strings["ABOUT_COMMANDS_TITLE"], value=f" ".join(f'`{i.name}`' for i in self.bot.commands if not i.hidden and not i.parent and i.name != 'jishaku'))
        await ctx.send(embed=embed)

    @commands.command(help="View information about what data Maximilian accesses and stores.")
    async def privacy(self, ctx):
        embed = discord.Embed(title=self.bot.strings["PRIVACY_TITLE"], color=self.bot.config['theme_color'])
        embed.add_field(name=self.bot.strings["PRIVACY_DATA_COLLECTION_TITLE"], value=self.bot.strings["PRIVACY_DATA_COLLECTION"], inline=False)
        embed.add_field(name=self.bot.strings["PRIVACY_DATA_COLLECTED_TITLE"], value=self.bot.strings["PRIVACY_DATA_COLLECTED_SERVER_IDS"], inline=False)
        embed.add_field(name=self.bot.strings["PRIVACY_DATA_COLLECTED_ROLE_IDS_TITLE"], value=self.bot.strings["PRIVACY_DATA_COLLECTED_ROLE_IDS"])
        embed.add_field(name=self.bot.strings["PRIVACY_DATA_COLLECTED_USER_IDS_TITLE"], value=self.bot.strings["PRIVACY_DATA_COLLECTED_USER_IDS"])
        embed.add_field(name=self.bot.strings["PRIVACY_DATA_COLLECTED_MUSIC_TITLE"], value=self.bot.strings["PRIVACY_DATA_COLLECTED_MUSIC"])
        embed.add_field(name=self.bot.strings["PRIVACY_DELETION_HELP_TITLE"], value=self.bot.strings["PRIVACY_DELETION_HELP"].format(await self.bot.get_prefix(ctx.message)), inline=False)
        await ctx.send(embed=embed)

    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.command(help="**Permanently** delete all data that Maximilian's stored about your server. (requires the Administrator permission)")
    async def deleteall(self, ctx):
        try:
            await self.bot.deletion_request(self.bot).create_request("all", ctx)
        except self.bot.DeletionRequestAlreadyActive:
            await ctx.send(self.bot.strings["DELETION_ACTIVE"])

    @commands.command(hidden=True)
    async def emojiinfo(self, ctx, emoji : typing.Optional[typing.Union[discord.PartialEmoji, str]]=None):
        if isinstance(emoji, discord.PartialEmoji):
            await ctx.send(f"`<{emoji.name}:{emoji.id}>`")
            return
        await ctx.send(f"`{emoji}`")

    @commands.command(aliases=["code", "src"])
    async def source(self, ctx, *, command: str = None):
        """Displays my full source code or the source code for the specified command.
        """
        source_url = "https://github.com/TK421bsod/maximilian"
        branch = self.bot.common.run_command(['git', 'branch', '--show-current'])['output'][0]
        if command is None:
            await ctx.send(source_url)
            return
        obj = self.bot.get_command(command)
        if obj is None or obj.name == "jishaku":
            return await ctx.send(self.bot.strings["SOURCE_NOT_FOUND"])
        src = obj.callback.__code__
        lines, firstlineno = inspect.getsourcelines(src)
        if not obj.callback.__module__.startswith('discord'):
            location = os.path.relpath(src.co_filename).replace('\\', '/')
        else:
            location = obj.callback.__module__.replace('.', '/') + '.py'
            source_url = "https://github.com/Rapptz/discord.py"
            branch = "master"
        await ctx.send(f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>')

    @commands.command(aliases=["rm"])
    async def rolemembers(self, ctx, *, role:discord.Role):
        '''Show the names and discriminators of everyone who has the specified role.'''
        rolestring = "\n".join([str(member) for member in role.members])
        await ctx.send(self.bot.strings["ROLEMEMBERS"].format(len(role.members), role.name, rolestring))

    @commands.command(aliases=["members"])
    async def membercount(self, ctx):
        '''Show the amount of people in this server.'''
        await ctx.send(self.bot.strings["MEMBERCOUNT"].format(len(ctx.guild.members), len([i for i in ctx.guild.members if not i.bot]), len([i for i in ctx.guild.members if i.bot])))

    @commands.command()
    async def avatar(self, ctx, *, user:typing.Optional[discord.Member]=None):
        '''View another user's avatar, or yours if you don't specify anyone'''
        if not user:
            await ctx.send(embed=discord.Embed(title=self.bot.strings["AVATAR"].format(ctx.author), color=self.bot.config['theme_color']).set_image(url=str(ctx.author.avatar.url)))
            return
        await ctx.send(embed=discord.Embed(title=self.bot.strings["AVATAR"].format(user), color=self.bot.config['theme_color']).set_image(url=str(user.avatar.url)))

    @commands.command(aliases=["randomdog", "dog"])
    async def dogs(self, ctx):
        '''Get a random image of a dog.'''
        async with ctx.typing():
            async with aiohttp.ClientSession() as cs:
                async with cs.get('https://dog.ceo/api/breeds/image/random') as r:
                    imagename = (await r.json())['message']
                    async with cs.get(imagename) as img:
                        buffer = io.BytesIO(await img.read())
                    await ctx.send(file=discord.File(buffer, filename=f"dog.{imagename[-3:]}"))

    @commands.hybrid_command(help="View patch notes for recent updates.")
    async def news(self, ctx):
        return await ctx.send(embed=discord.Embed(title=self.bot.strings["NEWS_TITLE"], description=self.bot.strings["NEWS_DESC"], color=self.bot.config['theme_color']))

    @commands.command(help="Repeats what you say. For example, `!say hi` would make Maximiilian say 'hi'. This command automatically prevents user, role, everyone, and here mentions from working.")
    async def say(self, ctx, *, thing):
        return await ctx.send(thing, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(misc(bot))

async def teardown(bot):
    await bot.remove_cog(misc(bot))
