import asyncio
import typing
from pymysql.err import IntegrityError

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
            print(response)
            if not isinstance(response, list):
                response = [response]
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
                responsestring += f"Command trigger: `{response[1]}`\nResponse: `{responsetext}`\n\n"
        if responsestring == "":
            await ctx.send("I can't find any custom commands in this server.")
        else:
            await ctx.send(embed=discord.Embed(title="Custom commands in this server", description=responsestring, color=self.bot.config['theme_color']))
    
    @commands.command(help="Add a custom command, takes the command trigger and response as parameters")
    async def add(self, ctx, command_trigger : str, command_response : str):
        command_response.replace("*", r"\*")
        command_trigger.replace("*", r"\*")
        for each in self.bot.commands:
            if command_trigger.lower() == each.name.lower() or command_trigger.lower() == "jishaku" or command_trigger.lower() == "jsk":
                await ctx.send("You can't create a custom command with the same name as one of my commands.")
                return
        try:
            self.bot.db.exec_safe_query("insert into responses values(%s, %s, %s)", (ctx.guild.id, command_trigger, command_response))
            await self.fill_cache()
            await ctx.send(embed=discord.Embed(title="Added that custom command.", color=self.bot.config['theme_color']))
        except IntegrityError:
            return await ctx.send("Looks like a command with the same trigger already exists.")
        except:
            await self.bot.core.send_traceback()
            await ctx.send("Sorry, something went wrong when adding that custom command. I've reported this error to my owner.\nIf this happens again, consider opening an issue at <https://github.com/tk421bsod/maximilian>.")
            await self.bot.core.send_debug(ctx)

    @commands.command(help="Delete a custom command, takes the command trigger as a parameter")
    async def delete(self, ctx, command_trigger : str):
        try:
            self.bot.db.exec_safe_query("delete from responses where response_trigger=%s and guild_id=%s", (command_trigger, ctx.guild.id))
            await self.fill_cache()
            await ctx.send(embed=discord.Embed(title="Deleted that custom command.", color=self.bot.config['theme_color']))
        except IntegrityError:
            return await ctx.send("It doesn't look like that custom command exists.")
        except:
            await self.bot.core.send_traceback()
            await ctx.send("Sorry, something went wrong when deleting that custom command. I've reported this error to my owner.\nIf this happens again, consider opening an issue at <https://github.com/tk421bsod/maximilian>.")
            await self.bot.core.send_debug()

async def setup(bot):
    await bot.add_cog(responses(bot))

async def teardown(bot):
    await bot.remove_cog(responses(bot, True))
