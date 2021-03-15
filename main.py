#import libraries
import discord
from discord.ext import commands 
from discord.ext import tasks
import logging
import sys
import init
import common
import helpcommand
import pymysql
import traceback

print("starting...")
token = common.token().get("token.txt")
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=discord.Intents.all(), activity=discord.Activity(type=discord.ActivityType.playing, name=f" v0.5.1 (stable)"))
init.config_logging(sys.argv)
init.init(bot).parse_arguments(sys.argv)
bot.logger = logging.getLogger('maximilian-stable')
bot.guildlist = []
bot.prefixes = {}
bot.responses = []
bot.dbinst = common.db(bot)
bot.database = "maximilian"
#try to connect to database, if it fails warn
print(f"Attempting to connect to database '{bot.database}' on '{bot.dbip}'...")
try:
    bot.dbinst.connect(bot.database)
    print("Connected to database successfully.")
except pymysql.err.OperationalError:
    bot.logger.critical("Couldn't connect to database, most features won't work. Make sure you passed the right IP and that the database is configured properly.")
#load extensions, starting with required ones
print("Loading required extensions...")
try:
    bot.load_extension("core")
    bot.load_extension("errorhandling")
except:
    bot.logger.error("Failed to get one or more cogs, some stuff might not work.")
print(f'loaded {extensioncount} extensions, waiting for ready')

class HelpCommand(commands.HelpCommand):
    color = discord.Colour.blurple()
    def get_ending_note(self):
        return 'Use {0}{1} [command] for more info on a command.'.format(self.clean_prefix, self.invoked_with)

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = '[%s|%s]' % (command.name, aliases)
            if parent:
                fmt = parent + ' ' + fmt
            alias = fmt
        else:
            alias = command.name if not parent else parent + ' ' + command.name

        return '%s%s %s' % (self.clean_prefix, alias, command.signature)

    async def send_bot_help(self, mapping):
        if not self.context.guild.me.permissions.embed_links:
            return await self.get_destination().send("It looks like I don't have permission to send embeds. My developer's working on a different help command that doesn't use them, but for now you'll need to enable the 'Embed Links' permission to be able to use the help command. To enable it, go to Server Settings > Roles > Maximilian, and you should see the Embed Links permission there.")
        embed = discord.Embed(title='Commands', colour=self.color)
        description = self.context.bot.description
        if description:
            embed.description = description

        for cog, commands in mapping.items():
            if cog is not None:
                name = cog.qualified_name
                filtered = await self.filter_commands(commands, sort=True)
                if filtered:
                    value = '\u2002 '.join('`' + c.name + '`' for c in commands if not c.hidden)
                    if cog and cog.description:
                        value = '{0}\n{1}'.format(cog.description, value)

                    embed.add_field(name=name, value=value)
        responseslist = self.context.bot.dbinst.exec_query(self.context.bot.database, "select * from responses where guild_id = {}".format(self.context.guild.id), False, True)
        responsestring = "A list of custom commands for this server. These don't have help entries. \n"
        if responseslist is not None and str(responseslist)!="()":
            for i in responseslist:
                responsestring += f"`{i['response_trigger']}` "
            embed.add_field(name="Custom Commands List", value=responsestring)
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        if not self.context.guild.me.permissions.embed_links:
            return await self.get_destination().send("It looks like I don't have permission to send embeds. My developer's working on a different help command that doesn't use them, but for now you'll need to enable the 'Embed Links' permission to be able to use the help command. To enable it, go to Server Settings > Roles > Maximilian, and you should see the Embed Links permission there.")
        embed = discord.Embed(title='{0.qualified_name} Commands'.format(cog), colour=self.color)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        if not self.context.guild.me.permissions.embed_links:
            return await self.get_destination().send("It looks like I don't have permission to send embeds. My developer's working on a different help command that doesn't use them, but for now you'll need to enable the 'Embed Links' permission to be able to use the help command. To enable it, go to Server Settings > Roles > Maximilian, and you should see the Embed Links permission there.")
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

@tasks.loop(seconds=60)
async def reset_status():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds and " + str(len(bot.users)) + " users!"))

print("Loaded required extensions successfully. Loading other cogs...")
init.init(bot).load_extensions()
    
@bot.event
async def on_message(message):
    if await bot.coreinst.prepare(message):
        await bot.process_commands(message)

@bot.before_invoke
async def before_anything(ctx):
    #before any commands are executed, make sure to set commandprefix (will be removed soon)
    try:
        bot.commandprefix = bot.prefixes[str(ctx.guild.id)]
    except (KeyError, AttributeError):
        bot.commandprefix = "!"

bot.run(token)
