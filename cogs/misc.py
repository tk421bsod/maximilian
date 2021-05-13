import discord
from discord.ext import commands
import time
import aiohttp
import io
import asyncio
from zalgo_text import zalgo as zalgo_text_gen
import typing
import bottom as bottomify
import inspect
import sys
import os 
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 
import core
import errors

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
        embed.add_field(name="Useful links", value=f"Use `{str(await self.bot.get_prefix(ctx.message))}help command` for more info on a certain command. \n For more help, join the support server at https://discord.gg/PJ94gft. \n To add Maximilian to your server, with only the required permissions, click [here](https://discord.com/api/oauth2/authorize?client_id=620022782016618528&permissions=335923264&scope=bot). \nIf you want to contribute to my development, visit my Github repository, at https://github.com/tk421bsod/maximilian.", inline=False)
        embed.add_field(name="Commands", value=f" ".join(f'`{i.name}`' for i in self.bot.commands if not i.hidden and not i.parent and i.name != 'jishaku'))
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
        embed.add_field(name="Why Maximilian collects data", value="Maximilian accesses/stores certain information that is necessary for certain functions (types of data collected are described below)", inline=False)
        embed.add_field(name="Data that Maximilian stores", value="**-Server IDs**\nMaximilian stores server IDs when you create a custom command, add a reaction role, or change its prefix to distinguish between different servers.\n\n**-Role IDs**\nMaximilian stores role IDs whenever you add a reaction role so it can assign the correct role to users.\n\n**-Music**\nTo keep track of what channels it's playing audio in, Maximilian puts your voice channel's ID in a list temporarily. This data isn't retrievable by anyone, and your channel ID is removed from the list when Maximilian stops playing audio in your voice channel.\nWhen you play a song, Maximilian stores information about that song, like the video ID and name, so it can play it without a long delay next time. When you add a song to your queue, Maximilian temporarily stores your voice channel's ID, the song's position in the queue, the song's name, and the song's id to keep track of your queue.\n", inline=False)
        embed.add_field(name="I want to delete my server's data, how do I request that?", value=f"You can delete all the data in your server by using `{await self.bot.get_prefix(ctx.message)}deleteall`. This will irreversibly delete all of the reaction roles and custom commands you have set up and reset the prefix to the default of `!`. Only people with the Administrator permission can use this.", inline=False)
        await ctx.send(embed=embed)

    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(add_reactions=True)
    @commands.command(help="**Permanently** delete all data that Maximilian's stored about your server. (requires the Administrator permission)")
    async def deleteall(self, ctx):
        try:
            await core.deletion_request(self.bot).create_request("all", ctx)
        except errors.DeletionRequestAlreadyActive:
            await ctx.send("A deletion request is already active.")

    @commands.command(hidden=True)
    async def emojiinfo(self, ctx, emoji : typing.Optional[typing.Union[discord.PartialEmoji, str]]=None):
        print(str(emoji))
        if isinstance(emoji, discord.PartialEmoji):
            await ctx.send(f"`<{emoji.name}:{emoji.id}>`")
            return
        await ctx.send(f"`{emoji}`")      

    @commands.command(aliases=["bottomify", "bm"])
    async def bottom(self, ctx, action, *, text):
        '''Turn UTF-8 encoded text into Bottom encoded text, and decode from Bottom back to UTF-8. See <https://github.com/kaylynn234/bottom> for more details on Bottom encoding.'''
        if action.lower() == "encode":
            encodedtext = bottomify.encode(text)
            await ctx.send(embed=discord.Embed(title="Here's your bottom encoded text:", description=encodedtext).set_footer(text=f"Use '{await self.bot.get_prefix(ctx.message)}bottom decode {encodedtext}' to decode this."))
        elif action.lower() == "decode":
            await ctx.send(bottomify.decode(text))
        else:
            await ctx.send("You need to specify whether you want to encode or decode text.")

    @commands.command(aliases=["code", "src"])
    async def source(self, ctx, *, command: str = None):
        """Displays my full source code or the source code for the specified command.
        """
        source_url = "https://github.com/TK421bsod/maximilian"
        branch = "maximilian-dev"
        if command is None:
            await ctx.send(source_url)
            return
        obj = self.bot.get_command(command)
        if obj is None or obj.name == "jishaku":
            return await ctx.send("I can't find the source code for that command. Make sure you didn't misspell the command's name.")
        src = obj.callback.__code__
        lines, firstlineno = inspect.getsourcelines(src)
        if not obj.callback.__module__.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(src.co_filename).replace('\\', '/')
        else:
            location = obj.callback.__module__.replace('.', '/') + '.py'
            source_url = "https://github.com/Rapptz/discord.py"
            branch = "master"
        await ctx.send(f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>')

    @commands.command(aliases=["owoify", "uwu", "uwuize"])
    async def owo(self, ctx, *, text:str):
        '''Uwuify text. I can\'t uwuify text over 2000 characters.'''
        text += " uwu"
        await ctx.send(text.replace("r", "w").replace("l", "w").replace("a", "aw"))
    
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

    @commands.command(help="Repeats what you say. For example, `!say hi` would make Maximiilian say 'hi'. This command automatically prevents user, role, everyone, and here mentions from working.")
    async def say(self, ctx, *, thing):
        return await ctx.send(thing, allowed_mentions=discord.AllowedMentions.none())

def setup(bot):
    bot.add_cog(misc(bot))

def teardown(bot):
    bot.remove_cog(misc(bot))
