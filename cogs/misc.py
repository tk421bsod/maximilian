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
        await ctx.send("Hello! I'm a Discord bot created by tk421#2016.")

    @commands.command(help="Get an image of a cat.", aliases=["thiscatdoesntexist"])
    async def cats(self, ctx):
        await ctx.typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://thiscatdoesnotexist.com') as r:
                buffer = io.BytesIO(await r.read())
                await ctx.send(file=discord.File(buffer, filename="cat.jpeg"))

    async def ping(self, ctx):
        await ctx.send(f"Latency: {str(round(self.bot.latency*1000, 1))} ms.")

    @commands.command(help="Get some info about the bot and commands")
    async def about(self, ctx):
        embed = discord.Embed(title="About", color=self.bot.config['theme_color'])
        embed.add_field(name="What's Maximilian?", value="Quite a few things. In short, it's a versatile, multi-purpose bot.")
        embed.add_field(name="Latest update - v1.0.3 (Jan 26, 2023)", value="Some additional bug fixes.\nWant to see changes from the last few updates? Use the `news` command.")
        embed.add_field(name="Useful stuff", value=f"Use `{str(await self.bot.get_prefix(ctx.message))}help command` for more info on a certain command. \n For more help, join the support server at https://discord.gg/PJ94gft. \n To add Maximilian to your server, with only the required permissions, click [here](https://discord.com/api/oauth2/authorize?client_id=620022782016618528&permissions=335923264&scope=bot). \nIf you want to contribute to my development, visit my Github repository at https://github.com/tk421bsod/maximilian.", inline=False)
        embed.add_field(name="Commands", value=f" ".join(f'`{i.name}`' for i in self.bot.commands if not i.hidden and not i.parent and i.name != 'jishaku'))
        await ctx.send(embed=embed)

    @commands.command(help="View information about what data Maximilian accesses and stores.")
    async def privacy(self, ctx):
        embed = discord.Embed(title="Maximilian Privacy Policy", color=self.bot.config['theme_color'])
        embed.add_field(name="Why Maximilian collects data", value="Maximilian accesses/stores certain information that is necessary for certain functions. It doesn't collect any sort of personally identifiable information. (types of data collected are described below)", inline=False)
        embed.add_field(name="Data that Maximilian stores", value="**-Server IDs**\nMaximilian stores server IDs when you create a custom command, add a reaction role, or change its prefix to distinguish between different servers.", inline=False)
        embed.add_field(name="-Role IDs", value="Maximilian stores role IDs whenever you add a reaction role so it can give people the correct role.")
        embed.add_field(name="-User IDs", value="Maximilian stores user IDs so it can keep track of your todo list and active reminders.")
        embed.add_field(name="-Music", value="To keep track of what channels it's playing audio in, Maximilian puts your voice channel's ID in a list temporarily. This data isn't retrievable by anyone, and your channel ID is removed from the list when Maximilian stops playing audio in your voice channel.\nWhen you play a song, Maximilian stores information about that song, like the video ID and name, so it can play it without a long delay next time. When you add a song to your queue, Maximilian temporarily stores your voice channel's ID, the song's position in the queue, the song's name, and the song's id to keep track of your queue.")
        embed.add_field(name="I want to delete my server's data, how do I request that?", value=f"You can delete all the data in your server by using `{await self.bot.get_prefix(ctx.message)}deleteall`. This will irreversibly delete all of the reaction roles and custom commands you have set up and reset the prefix to the default of `!`. Only people with the Administrator permission can use this.", inline=False)
        await ctx.send(embed=embed)

    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.command(help="**Permanently** delete all data that Maximilian's stored about your server. (requires the Administrator permission)")
    async def deleteall(self, ctx):
        try:
            await self.bot.core.deletion_request(self.bot).create_request("all", ctx)
        except self.bot.DeletionRequestAlreadyActive:
            await ctx.send("A deletion request is already active.")

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
            return await ctx.send("I can't find the source code for that command. Make sure you didn't misspell the command's name.")
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
        await ctx.send(f"Found {len(role.members)} users with the {role.name} role. \n{rolestring}")
    
    @commands.command(aliases=["members"])
    async def membercount(self, ctx):
        '''Show the amount of people in this server.'''
        await ctx.send(f"Found {len(ctx.guild.members)} members. ({len([i for i in ctx.guild.members if not i.bot])} people and {len([i for i in ctx.guild.members if i.bot])} bots)")

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

    @commands.command(help="View patch notes for recent updates.", aliases=["updates", "patchnotes"])
    async def news(self, ctx):
        return await ctx.send(embed=discord.Embed(title="News", description="Jan 26, 2023 - 1.0.3\n[Just some bug fixes](https://gist.github.com/TK421bsod/c71364e2a10c10247ce3faede437e9a6)\n\n**Jan 17, 2023 - 1.0.2**\n[Bug fixes, `news` command](https://gist.github.com/TK421bsod/95663a2f5bde64e5fcb4bda9c8b82c05)\n\n**Jan 12, 2023 - 1.0.1**\n[Fixes for some critical bugs, some small tweaks](https://gist.github.com/TK421bsod/b8f88adfaf2d4adbe249ba9d9190e213)\n\n**Jan 4, 2023 - 1.0.0**\n[The first major release since April 2021. Lots of changes.](https://gist.github.com/TK421bsod/2980fa67a9a5f925e7cdfb9f083a5c3b)", color=self.bot.config['theme_color']))

    @commands.command(help="Repeats what you say. For example, `!say hi` would make Maximiilian say 'hi'. This command automatically prevents user, role, everyone, and here mentions from working.")
    async def say(self, ctx, *, thing):
        return await ctx.send(thing, allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):
    await bot.add_cog(misc(bot))

async def teardown(bot):
    await bot.remove_cog(misc(bot))
