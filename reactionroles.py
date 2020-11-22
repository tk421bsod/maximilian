import discord
from discord.ext import commands

class reactionroles(commands.Cog, name="reaction roles"):
    '''Reaction role commands'''
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Add, remove, or list reaction roles, only works if you have the manage roles permission", aliases=['reactionrole'])
    async def reactionroles(self,ctx, action, roleid, messageid):
        if ctx.author.guild_permissions.manage_roles:
            if action == "add":
                if self.bot.dbinst.insert(self.bot.database, "roles", {"guild_id" : str(ctx.guild.id), "role_id" : str(roleid), "message_id" : str(messageid)}, "role_id", False, "", False, "", False) == "success":
                    print("added a reaction role")
                    await ctx.send("Added a reaction role.")
                else: 
                    raise discord.ext.commands.CommandError(message="Failed to add a reaction role, there might be a duplicate. Try deleting the role you just tried to add.")
            if action == "delete":
                print("deleted a reaction role")
                if self.bot.dbinst.delete(self.bot.database, "roles", str(roleid), "role_id", "", "", False) == "successful":
                    await ctx.send("Deleted a reaction role.")
                else:
                    raise discord.ext.commands.CommandError(message=f"Failed to delete a reaction role, are there any reaction roles set up for role id '{str(roleid)}'? Try using '{str(self.bot.command_prefix)}'reactionroles list all all' to see if you have any reaction roles set up.")
            if action == "list":
                roles = self.bot.dbinst.exec_query(self.bot.database, "select * from roles where guild_id={}".format(ctx.guild.id), False, True)
                reactionrolestring = ""
                if roles != "()":
                    for each in roles: 
                        reactionrolestring = f"{reactionrolestring} message id:  {str(each['message_id'])}  role id:  {str(each['role_id'])}, "        
                    print("listed reaction roles")
                    await ctx.send("reaction roles: " + str(reactionrolestring[:-2]))
        else:
            await ctx.send("You don't have permission to use this command.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.bot.dbinst.retrieve(self.bot.database, "roles", "guild_id", "guild_id", str(payload.guild_id), False) is not None:
            roleid = self.bot.dbinst.retrieve(self.bot.database, "roles", "role_id", "message_id", str(payload.message_id), False)
            if roleid is not None:
                role = discord.utils.get(payload.member.guild.roles, id=int(roleid))
                if role in payload.member.roles:
                    ctx = self.bot.get_channel(payload.channel_id)
                    await ctx.send(f" <@!{str(payload.member.id)}>, you already have the '{role.name}' role.", delete_after=5)
                    return
                await payload.member.add_roles(role)
                ctx = self.bot.get_channel(payload.channel_id)
                print("added role to user")
                await ctx.send(f"Assigned <@!{str(payload.member.id)}> the '{role.name}' role!", delete_after=5)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if self.bot.dbinst.retrieve(self.bot.database, "roles", "guild_id", "guild_id", str(payload.guild_id), False) is not None:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            roleid = self.bot.dbinst.retrieve(self.bot.database, "roles", "role_id", "message_id", str(payload.message_id), False)
            if roleid is not None:
                ctx = self.bot.get_channel(payload.channel_id)
                role = discord.utils.get(guild.roles, id=int(roleid))
                if role in member.roles:
                    await member.remove_roles(role)
                    print("removed role from user")
                    await ctx.send(f"Removed the '{role.name}' role from <@!{str(member.id)}>!", delete_after=5)
                    return
                await ctx.send(f"<@!{str(member.id)}> For some reason, you don't have the '{role.name}' role, even though you reacted to this message. Try removing your reaction and adding your reaction again. If this keeps happening, notify tk421#7244.", delete_after=15)

def setup(bot):
    bot.add_cog(reactionroles(bot))

def teardown(bot):
    bot.remove_cog(reactionroles(bot))