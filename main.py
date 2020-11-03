import discord
from discord.ext import commands 
import common
import importlib
import logging
import time
import calendar
import os
import sys

logging.basicConfig(level=logging.WARN)
print("starting...")
tokeninst = common.token()
decrypted_token = tokeninst.decrypt("token.txt")
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="myself start up!"))
bot.guildlist = []
bot.prefixes = {}
bot.responses = []
bot.dbinst = common.db()
bot.load_extension('responses')
bot.load_extension('prefixes')
bot.load_extension('misc')
bot.load_extension('reactionroles')
bot.load_extension('userinfo')
bot.responsesinst = bot.get_cog('responses')
bot.prefixesinst = bot.get_cog('prefixes')
bot.miscinst = bot.get_cog('misc')
bot.reactionrolesinst = bot.get_cog('reactionroles')
print('loaded extensions, waiting for on-ready')

class HelpCommand(commands.HelpCommand):
    color = discord.Colour.blurple()
    def get_ending_note(self):
        return 'Use {0}{1} [command] for more info on a command.'.format(self.clean_prefix, self.invoked_with)

    def get_command_signature(self, command):
        return '{0.qualified_name} {0.signature}'.format(command)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title='Commands', colour=self.color)
        description = self.context.bot.description
        if description:
            embed.description = description

        for cog, commands in mapping.items():
            if cog is not None:
                name = cog.qualified_name
                filtered = await self.filter_commands(commands, sort=True)
                if filtered:
                    value = '\u2002 '.join('`' + c.name + '`' for c in commands)
                    if cog and cog.description:
                        value = '{0}\n{1}'.format(cog.description, value)

                    embed.add_field(name=name, value=value)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title='{0.qualified_name} Commands'.format(cog), colour=self.color)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=group.qualified_name, colour=self.color)
        if group.help:
            embed.description = group.help

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)
    send_command_help = send_group_help

async def startup():
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds!"))

@bot.event
async def on_ready():
    await bot.prefixesinst.reset_prefixes()
    await bot.responsesinst.get_responses()
    bot.help_command = HelpCommand()
    bot.loop.create_task(startup())
    print("ready")
    
@bot.event
async def on_message(message):
    if message.author != bot.user:
        if message.content.startswith('<@!620022782016618528> '):
            bot.command_prefix = '<@!620022782016618528> '
        else:
            if message.guild is not None:
                try:    
                    bot.command_prefix = bot.prefixes[str(message.guild.id)]
                except KeyError:
                    print("Couldn't get prefixes, using default prefix instead")
                    bot.command_prefix = "!"
                    pass
                for each in range(len(bot.responses)):
                    if int(bot.responses[each][0]) == int(message.guild.id):
                        if bot.responses[each][1] == message.content.replace(bot.command_prefix, ""):
                            await message.channel.send(bot.responses[each][2])
                            return
        await bot.process_commands(message)

@bot.event
async def on_error(event, *args, **kwargs):
    print(str(sys.exc_info()[0]))
    print(str(args[0]))
    if isinstance(args[0], discord.RawReactionActionEvent):
        await on_command_error(bot.get_channel(int(args[0].channel_id)), getattr(sys.exc_info()[0], 'class', sys.exc_info()[0]))

@bot.event
async def on_command_error(ctx, error):
    print("error")
    error = getattr(error, "original", error)
    if isinstance(error, commands.BotMissingPermissions) or isinstance(error, discord.errors.Forbidden) or 'discord.errors.Forbidden' in str(error):
        embed = discord.Embed(title="\U0000274c I don't have the permissions to run this command, try moving my role up in the hierarchy.", color=discord.Color.blurple())
        await ctx.send(embed=embed)
        return
    if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.NotOwner):
        embed = discord.Embed(title="\U0000274c You don't have the permissions to run this command.", color=discord.Color.blurple())
        embed.add_field(name="Why did this happen? What can I do?", value=f"Some commands require certain permissions; try using `{bot.command_prefix}help <commandname>` to get more info on that command, including the required permissions..", inline=False)
        await ctx.send(embed=embed)
        return
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(title=f"\U0000274c I can't find that command. Use `{bot.command_prefix}help` to see a list of commands.", color=discord.Color.blurple())
        await ctx.send(embed=embed)
        return
    await ctx.send("There was an error. Please try again later.")
    await ctx.send(f"`{error}`")

@bot.command(help="Get a new list of custom responses after adding a new response", aliases=['fetchresponses', 'getresponses'])
async def fetch_responses(ctx):
    gettingresponsesmessage = await ctx.send("Getting a new list of responses...")
    await bot.responsesinst.get_responses()
    await gettingresponsesmessage.edit(content="Got a new list of responses!")

@bot.command(help="List all prefixes")
async def listprefixes(ctx):
    prefixstring = ""
    for key in bot.prefixes.keys():
        if key == str(ctx.message.guild.id):
            prefixstring = prefixstring + "`" + bot.prefixes[key] + "`"
    await ctx.send("My prefixes in this server are " + prefixstring + " and <@!620022782016618528>")


@bot.event
async def on_guild_join(guild):
    print("joined guild, adding guild id to list of guilds and resetting prefixes")
    bot.guildlist.append(str(guild.id))
    await bot.prefixesinst.reset_prefixes()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds!"))

@commands.is_owner()
@bot.command(hidden=True)
async def reload(ctx, *targetextensions):
    await ctx.trigger_typing()
    try:
        if len(targetextensions) == 1:
            extensionsreloaded = "Successfully reloaded 1 extension."
        elif len(targetextensions) == 0:
            embed = discord.Embed(title="\U0000274e You need to specify at least 1 extension to reload.", color=discord.Color.blurple())
            await ctx.send(embed=embed)
            return
        else:
            extensionsreloaded = f"Successfully reloaded {str(len(targetextensions))} extensions."
        #reloadmessage = await ctx.send("Fetching latest revision...")
        #os.system("git pull")
        reloadmessage = await ctx.send("Reloading extensions...")
        for each in targetextensions:
            bot.reload_extension(each)
        bot.responsesinst = bot.get_cog('responses')
        bot.prefixesinst = bot.get_cog('prefixes')
        bot.miscinst = bot.get_cog('misc')
        bot.reactionrolesinst = bot.get_cog('reactionroles')
        await bot.prefixesinst.reset_prefixes()
        await bot.responsesinst.get_responses()
        embed = discord.Embed(title=f"\U00002705 {extensionsreloaded}", color=discord.Color.blurple())
    except Exception as e:
        embed = discord.Embed(title=f"\U0000274c Error while reloading extensions: {str(e)}.")
        embed.add_field(name="What might have happened:", value="You might have mistyped the extension name; the extensions are `misc`, `reactionroles`, `prefixes`, `responses`, and `userinfo`. If you created a new extension, make sure that it has a setup function, and you're calling `Bot.load_extension(name)` somewhere in main.py.")
    await ctx.send(embed=embed) 

bot.run(decrypted_token)
