import discord 
from discord.ext import commands
import typing

class responses(commands.Cog, name='Custom Commands'):
    def __init__(self, bot):
        self.bot = bot
    
    async def get_responses(self):
        print("getting responses...")
        tempresponses = []
        #if guildlist doesn't exist for some reason, get it
        if not self.bot.guildlist:    
            for guild in await self.bot.fetch_guilds().flatten():
                self.bot.guildlist.append(str(guild.id))
        #then for each guild in the list, check if the guild has any responses in the database
        for guild in self.bot.guildlist:
            count = self.bot.dbinst.exec_query(self.bot.database, "select count(*) from responses where guild_id={}".format(str(guild)), False, False)
            if count is not None:
                #if there are responses, check if there's one or more
                if int(count['count(*)']) >= 1:
                    #if so, get a list of responses and iterate over that, adding each one to the list
                    response = self.bot.dbinst.exec_query(self.bot.database, "select * from responses where guild_id={}".format(str(guild)), False, True)
                    for each in range(int(count['count(*)'])):
                        tempresponses.append([str(response[each]['guild_id']), response[each]['response_trigger'], response[each]['response_text']])
        self.bot.responses = tempresponses
        return

    @commands.has_guild_permissions(manage_guild=True)
    @commands.command(help=f"Add, delete, or list custom commands. This takes 3 arguments, `action` (the action you want to perform, must be either `add`, `delete`, or `list`), `command_trigger` (the text that will trigger the command), and `command_response` (what you want Maximilian to send when you enter Maximilian's prefix followed by the command trigger). \n You must have 'Manage Server' permissions to do this. Don't include Maximilian's prefix in the command trigger. You can send a custom command by typing <prefix><command_trigger>.", aliases=['command'])
    async def commands(self, ctx, action, command_trigger : typing.Optional[str]=None, *, command_response : typing.Optional[str]=None):
        await ctx.trigger_typing()
        if action.lower() == "list":
            responsestring = ""
            await self.get_responses()
            for each in range(len(self.bot.responses)):
                if int(self.bot.responses[each][0]) == int(ctx.guild.id):
                    if len(self.bot.responses[each][2]) >= 200:
                        responsetext = self.bot.responses[each][2][:200] + "..."
                    else:
                        responsetext = self.bot.responses[each][2]
                    responsestring = responsestring + " \n command trigger: `" + self.bot.responses[each][1] + "` response: `" + responsetext + "`"
            if responsestring == "":
                responsestring = "I can't find any custom commands in this server."
            else: 
                await ctx.send(responsestring)
            return
        if action.lower() == "add" and command_trigger != None and command_response != None:
            command_response.replace("*", r"\*")
            command_trigger.replace("*", r"\*")
            for each in self.bot.commands:
                print(each.name)
                if command_trigger.lower() == each.name.lower():
                    await ctx.send("You can't create a custom command with the same name as one of my commands.")
                    return
            if self.bot.dbinst.insert(self.bot.database, "responses", {"guild_id" : str(ctx.guild.id), "response_trigger" : str(command_trigger), "response_text" : str(command_response)}, "response_trigger", False, "", False, "guild_id", True) == "success":
                await self.get_responses()
                print("added response")
                await ctx.send("Added a custom command.")
            else: 
                raise discord.ext.commands.CommandError(message="Failed to add a command, there might be a duplicate. Try deleting the command you just tried to add.")
            return
        elif command_trigger == None or command_response == None:
            await ctx.send(f"It doesn't look like you've provided all of the required arguments. See `{self.bot.command_prefix}help commands` for more details.")
        if action.lower() == "delete" and command_trigger != None and command_response != None:
            if self.bot.dbinst.delete(self.bot.database, "responses", str(command_trigger), "response_trigger", "guild_id", str(ctx.guild.id), True) == "successful":
                await self.get_responses()
                print("deleted response")
                await ctx.send("Deleted a custom command.")
            else:
                raise discord.ext.commands.CommandError(message="Failed to delete a custom command, are there any custom commands set up that use the command trigger '" + str(command_trigger) + "'?")
            return
        elif command_trigger == None or command_response == None:
            await ctx.send(f"It doesn't look like you've provided all of the required arguments. See `{self.bot.command_prefix}help commands` for more details.")
    
def setup(bot):
    bot.add_cog(responses(bot))

def teardown(bot):
    bot.remove_cog(responses(bot))
