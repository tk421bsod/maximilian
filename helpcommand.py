import discord
from discord.ext import commands
import traceback

class HelpCommand(commands.HelpCommand):

    def get_ending_note(self):
        return self.context.bot.strings["ENDING_NOTE"].format(self.context.clean_prefix, self.invoked_with)

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

        return '%s%s %s' % (self.context.clean_prefix, alias, command.signature)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title=self.context.bot.strings["HELP_TITLE"], color=self.context.bot.config['theme_color'])
        description = self.context.bot.description
        if description:
            embed.description = description

        for cog, commands in mapping.items():
            if cog is not None:
                name = cog.qualified_name
                filtered = await self.filter_commands(commands, sort=True)
                if filtered:
                    value = '\u2002 '.join([f'`{self.context.clean_prefix}' + c.name + '`' for c in commands if not c.hidden])
                    if cog and cog.description:
                        value = '{0}\n{1}'.format(cog.description, value)

                    embed.add_field(name=name, value=value)
        if self.context.guild is not None:
            responseslist = [i for i in self.context.bot.responses if i[0] == self.context.guild.id]
            responsestring = self.context.bot.strings["COMMANDS_LIST"]
            if responseslist is not None:
                for i in responseslist:
                    responsestring += f"`{i[1]}` "
                embed.add_field(name=self.context.bot.strings["COMMANDS_LIST_TITLE"], value=responsestring)
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title=self.context.bot.strings["COG_HELP_TITLE"].format(cog), color=self.context.bot.config['theme_color'])
        if cog.description:
            embed.description = cog.description
        self.show_hidden = True
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        self.show_hidden = False
        for command in filtered:
            embed.add_field(name=self.get_command_signature(command), value=await self.get_command_docstring(command, append_syntax=False), inline=False)
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def get_command_docstring(self, command, append_syntax=True):
        help = None
        name = ""
        if command.parent:
            name += command.parent.name
        name += command.name
        try:
            help = command.extras['localized_help'][self.context.bot.language]
        except (AttributeError, KeyError):
            self.context.bot.logger.debug(traceback.format_exc())
            self.context.bot.logger.debug(f"No help string found for command {name.strip().replace(' ', '_').upper()} in the command's localized_help. Searching in bot.strings.")
            try:
                help = self.context.bot.strings[f"COMMAND_HELP_{name.strip().replace(' ', '_').upper()}"]
                if "COMMAND_HELP" in help:
                    raise KeyError
            except KeyError:
                self.context.bot.logger.debug(f"No help string found for command {name.strip().replace(' ', '_').upper()} in bot.strings. Falling back to provided help string.")
                if command.help:
                    help = command.help
        try:
            command.extras
            if self.context.bot.common.get_value(command.extras, "uses_timeconverter"):
                help += self.context.bot.strings["COMMAND_USES_TIMECONVERTER"]
                UNITS = {"w":"[w]eeks", "d":"[d]ays", "h":"[h]ours", "m":"[m]inutes", "s":"[s]econds"}
                unit_string = ""
                for unit in self.context.bot.common.get_value(command.extras, "timeconverter_allowed_units", ("d","h","m","s")):
                    unit_string += f"\n`{unit}` : `{UNITS[unit]}`"
                help += self.context.bot.strings["TIMECONVERTER_ALLOWED_UNITS"].format(unit_string)
        except AttributeError:
            pass
        parent = ""
        if command.parent:
            parent = command.parent.name + " "
        if help:
            if not append_syntax:
                return help
            return help + self.context.bot.strings["COMMAND_SYNTAX"].format(self.context.clean_prefix, parent, command.name, command.signature)
        self.context.bot.logger.debug(f'No help string provided for command {command.name}.')
        return '...'

    async def send_group_help(self, group):
        embed = discord.Embed(title=group.qualified_name, color=self.context.bot.config['theme_color'])
        if group.help:
            embed.description = group.help
        if isinstance(group, commands.Group):
            self.show_hidden = True
            filtered = await self.filter_commands(group.commands, sort=True)
            self.show_hidden = False
            for command in filtered:
                doc = await self.get_command_docstring(command, append_syntax=False)
                embed.add_field(name=self.get_command_signature(command), value=doc, inline=False)
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=command.qualified_name, color=self.context.bot.config['theme_color'])
        embed.description = await self.get_command_docstring(command)
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
