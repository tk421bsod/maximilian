import asyncio
import typing

import discord


class responses(discord.ext.commands.Cog, name='Custom Commands'):
    def __init__(self, bot, teardown=False):
        self.bot = bot
        self.bot.responses = []
        if not teardown:
            self.bot.loop.create_task(self.fill_cache())

    async def fill_cache(self):
        '''Builds cache of custom commands'''
        tempresponses = []
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            response = self.bot.db.exec_safe_query("select * from responses where guild_id=%s", (guild.id, ))
            if not response:
                continue
            for each in response:
                tempresponses.append([each['guild_id'], each['response_trigger'], each['response_text']])
        self.bot.responses = tempresponses
        return

    @discord.ext.commands.has_guild_permissions(manage_guild=True)
    @discord.ext.commands.group(help=f"Add, delete, or list custom commands. This takes 3 arguments, `action` (the action you want to perform, must be either `add`, `delete`, or `list`), `command_trigger` (the text that will trigger the command), and `command_response` (what you want Maximilian to send when you enter Maximilian's prefix followed by the command trigger). \n You must have 'Manage Server' permissions to do this. Don't include Maximilian's prefix in the command trigger. You can send a custom command by typing <prefix><command_trigger>.", aliases=['command'], invoke_without_subcommand=False)
    async def commands(self, ctx):
        pass
    
    @commands.command(help="List all of the custom commands you've set up in your server")
    async def list(self, ctx):
        responsestring = ""
        for response in self.bot.responses:
            if response[0] == ctx.guild.id:
                if len(response[2]) >= 200:
                    responsetext = response[2][:200] + "..."
                else:
                    responsetext = response[2]
                responsestring += f"Command trigger: `{self.bot.responses[each][1]}` Response: `{responsetext}`\n\n"
        if responsestring == "":
            await ctx.send("I can't find any custom commands in this server.")
        else:
            await ctx.send(embed=discord.Embed(title="Custom commands in this server", description=responsestring))
    
    @commands.command(help="Add a custom command, takes the command trigger and response as parameters")
    async def add(self, ctx, command_trigger : str, command_response : str):
        command_response.replace("*", r"\*")
        command_trigger.replace("*", r"\*")
        for each in self.bot.responses:
            if command_trigger.lower() == each.name.lower() or command_trigger.lower() == "jishaku" or command_trigger.lower() == "jsk":
                await ctx.send("You can't create a custom command with the same name as one of my commands.")
                return
        try:
            self.bot.db.exec_safe_query("responses", {"guild_id" : str(ctx.guild.id), "response_trigger" : str(command_trigger), "response_text" : str(command_response)}, "response_trigger", False, "", False, "guild_id", True)
            await self.get_responses()
            await ctx.send("Added that custom command.")
        except:
            await self.bot.core.send_traceback()
            await ctx.send("Sorry, something went wrong when adding that custom command. I've reported this error to my owner.\nIf this happens again, consider opening an issue at <https://github.com/tk421bsod/maximilian>.")
            await self.bot.core.send_debug(ctx)

    @commands.command(help="Delete a custom command, takes the command trigger as a parameter")
    async def delete(self, ctx, command_trigger : str):
        try:
            self.bot.db.exec_safe_query("delete from responses where response_trigger=%s and guild_id=%s", (command_trigger, ctx.guild.id))
            await self.fill_cache()
            await ctx.send(embed=discord.Embed(title="Deleted that custom command."))
        except:
            await self.bot.core.send_traceback()
            await ctx.send("Sorry, something went wrong when deleting that custom command. I've reported this error to my owner.\nIf this happens again, consider opening an issue at <https://github.com/tk421bsod/maximilian>.")
            await self.bot.core.send_debug()

async def setup(bot):
    await bot.add_cog(responses(bot))

async def teardown(bot):
    await bot.remove_cog(responses(bot, True))
