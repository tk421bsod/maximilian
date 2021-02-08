import discord 
import typing

class responses(discord.ext.commands.Cog, name='Custom Commands'):
    def __init__(self, bot):
        self.bot = bot
    
    async def check_if_ready(self):
        if not self.bot.is_ready():
            self.bot.logger.warn("not ready yet, waiting for cache")
            await self.bot.wait_until_ready()
        else:
            print("already ready") 
    
    async def get_responses(self):
        tempresponses = []
        #make sure cache is ready before we try to iterate over bot.guilds (if we don't wait, bot.guilds may be incomplete)
        await self.check_if_ready()
        #then for each guild in the list, check if the guild has any responses in the database
        for guild in self.bot.guilds:
            if (count := self.bot.dbinst.exec_query(self.bot.database, "select count(*) from responses where guild_id={}".format(str(guild.id)), False, False)) is not None:
                #if there are responses, check if there's one or more
                if int(count['count(*)']) >= 1:
                    #if so, get a list of responses and iterate over that, adding each one to the list
                    response = self.bot.dbinst.exec_query(self.bot.database, "select * from responses where guild_id={}".format(str(guild.id)), False, True)
                    for each in range(int(count['count(*)'])):
                        tempresponses.append([str(response[each]['guild_id']), response[each]['response_trigger'], response[each]['response_text']])
        self.bot.responses = tempresponses
        return

    @discord.ext.commands.has_guild_permissions(manage_guild=True)
    @discord.ext.commands.group(help=f"Add, delete, or list custom commands. This takes 3 arguments, `action` (the action you want to perform, must be either `add`, `delete`, or `list`), `command_trigger` (the text that will trigger the command), and `command_response` (what you want Maximilian to send when you enter Maximilian's prefix followed by the command trigger). \n You must have 'Manage Server' permissions to do this. Don't include Maximilian's prefix in the command trigger. You can send a custom command by typing <prefix><command_trigger>.", aliases=['command'])
    async def commands(self, ctx):
        await ctx.trigger_typing()
    
    @commands.command(help="List all of the custom commands you've set up in your server")
    async def list(self, ctx):
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
    
    @commands.command(help="Add a custom command")
    async def add(self, ctx, command_trigger : str, command_response : str):
        command_response.replace("*", r"\*")
        command_trigger.replace("*", r"\*")
        for each in self.bot.commands:
            print(each.name)
            if command_trigger.lower() == each.name.lower() or command_trigger.lower() == "jishaku" or command_trigger.lower() == "jsk":
                await ctx.send("You can't create a custom command with the same name as one of my commands.")
                return
        if self.bot.dbinst.insert(self.bot.database, "responses", {"guild_id" : str(ctx.guild.id), "response_trigger" : str(command_trigger), "response_text" : str(command_response)}, "response_trigger", False, "", False, "guild_id", True) == "success":
            await self.get_responses()
            print("added response")
            await ctx.send("Added a custom command.")
        else: 
            raise discord.ext.commands.CommandError(message="Failed to add a command, there might be a duplicate. Try deleting the command you just tried to add.")
            return
    
    @commands.command(help="Delete a custom command")
    async def delete(self, ctx, command_trigger : str, command_response : str):
        if self.bot.dbinst.delete(self.bot.database, "responses", str(command_trigger), "response_trigger", "guild_id", str(ctx.guild.id), True) == "successful":
            await self.get_responses()
            print("deleted response")
            await ctx.send("Deleted a custom command.")
        else:
            raise discord.ext.commands.CommandError(message="Failed to delete a custom command, are there any custom commands set up that use the command trigger '" + str(command_trigger) + "'?")
            return
        
def setup(bot):
    bot.add_cog(responses(bot))

def teardown(bot):
    bot.remove_cog(responses(bot))
