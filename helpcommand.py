import discord
from discord.ext import commands
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
        embed = discord.Embed(title='Commands', colour=self.color)
        description = self.context.bot.description
        if description:
            embed.description = description

        for cog, commands in mapping.items():
            if cog is not None:
                name = cog.qualified_name
                filtered = await self.filter_commands(commands, sort=True)
                if filtered:
                    value = '\u2002 '.join([f'`{self.clean_prefix}' + c.name + '`' for c in commands if not c.hidden])
                    if cog and cog.description:
                        value = '{0}\n{1}'.format(cog.description, value)

                    embed.add_field(name=name, value=value)
        if self.context.guild is not None:
            #TODO: use the existing cache (not sure why I didn't think of it before writing this)
            #im too lazy to change it rn as it's 1 am
            responseslist = self.context.bot.dbinst.exec_query(self.context.bot.database, "select * from responses where guild_id = %s", (self.context.guild.id), fetchall=True)
            responsestring = "A list of custom commands for this server. These don't have help entries. \n"
            if responseslist is not None and str(responseslist)!="()":
                for i in responseslist:
                    responsestring += f"`{i['response_trigger']}` "
                embed.add_field(name="Custom Commands List", value=responsestring)
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
