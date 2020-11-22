import discord 
from discord.ext import commands

class responses(commands.Cog, name='Custom Commands'):
    def __init__(self, bot):
        self.bot = bot
    
    async def get_responses(self):
        print("getting responses...")
        self.bot.responses = []
        #if guildlist doesn't exist for some reason, get it
        if not self.bot.guildlist:    
            for guild in await self.bot.fetch_guilds().flatten():
                self.bot.guildlist.append(str(guild.id))
        #then for each guild in the list, check if the guild has any responses in the database
        for guild in self.bot.guildlist:
            count = self.bot.dbinst.exec_query(self.bot.database, "select count(*) from responses where guild_id={}".format(str(guild)), False, False)
            if count is not None:
                #if there are responses, check if there's more than one
                if int(count['count(*)']) >= 2:
                    #if so, get a list of responses and iterate over that, adding each one to the list
                    response = self.bot.dbinst.exec_query(self.bot.database, "select * from responses where guild_id={}".format(str(guild)), False, True)
                    for each in range(int(count['count(*)'])):
                        self.bot.responses.append([str(response[each]['guild_id']), response[each]['response_trigger'], response[each]['response_text']])
                elif int(count['count(*)']) == 1:
                    #otherwise get the one response and add it to the list
                    response = self.bot.dbinst.exec_query(self.bot.database, "select * from responses where guild_id={}".format(str(guild)), True, False)
                    self.bot.responses.append([str(response['guild_id']), response['response_trigger'], response['response_text']])

    @commands.command(help=f"Add, delete, or list custom commands. You must have 'Manage Server' permissions to do this. Don't include Maximilian's prefix in the command trigger. You can send a custom command by typing <prefix><command_trigger>.", aliases=['command'])
    async def commands(self, ctx, action, command_trigger, *, command_response):
        if ctx.author.guild_permissions.manage_guild or ctx.author.id == self.bot.owner_id:
            await ctx.trigger_typing()
            if action.lower() == "add":
                command_response.replace("*", "\*")
                command_trigger.replace("*", "\*")
                if self.bot.dbinst.insert(self.bot.database, "responses", {"guild_id" : str(ctx.guild.id), "response_trigger" : str(command_trigger), "response_text" : str(command_response)}, "response_trigger", False, "", False, "guild_id", True) == "success":
                    await self.get_responses()
                    print("added response")
                    await ctx.send("Added a custom command.")
                else: 
                    raise discord.ext.commands.CommandError(message="Failed to add a command, there might be a duplicate. Try deleting the command you just tried to add.")
            if action.lower() == "delete":
                if self.bot.dbinst.delete(self.bot.database, "responses", str(command_trigger), "response_trigger", "guild_id", str(ctx.guild.id), True) == "successful":
                    await self.get_responses()
                    print("deleted response")
                    await ctx.send("Deleted a custom command.")
                else:
                    raise discord.ext.commands.CommandError(message="Failed to delete a custom command, are there any custom commands set up that use the command trigger '" + str(command_trigger) + "'?")
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
                print("listed responses")
                await ctx.send(responsestring)
        else:
            await ctx.send("You don't have permission to use this command.")
    
def setup(bot):
    bot.add_cog(responses(bot))

def teardown(bot):
    bot.remove_cog(responses(bot))
