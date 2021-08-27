import typing

import discord
from discord.ext import commands
import typing
import logging
import traceback
import pymysql

class reactionroles(commands.Cog, name="reaction roles"):
    '''Reaction role commands'''
    def __init__(self, bot, load=False):
        self.bot = bot
        self.bot.reaction_roles = {}
        self.logger = logging.getLogger('cogs.reactionroles')
        if load:
            self.bot.loop.create_task(self.update_reactionroles_cache())

    async def update_reactionroles_cache(self):
        await self.bot.wait_until_ready()
        self.logger.info("Updating reaction roles cache...")
        temp_reaction_roles = {}
        for guild in self.bot.guilds:
            rolesdata = self.bot.dbinst.exec_query(self.bot.database, "select role_id, message_id, emoji from roles where guild_id = %s", (guild.id), fetchall=True)
            if not rolesdata:
                continue
            temp_reaction_roles[guild.id] = []
            for row in rolesdata:
                temp_reaction_roles[guild.id].append(row)
        self.bot.reaction_roles = temp_reaction_roles
        self.logger.info("Updated reaction roles cache!")

    @commands.command(help="Add, remove, or list reaction roles, only works if you have the 'Manage Roles' permission. This command takes 4 arguments (1 optional), action (the action to perform, either `add`, `delete`, or `list`), role (a role, you can either mention it or provide the id), messageid (the id of the message you want people to react to), and emoji (the emoji you want people to react with, it must be in a server Maximilian is in or a default emoji, this can be blank if you want people to react with any emoji)", aliases=['reactionrole'])
    @commands.has_guild_permissions(manage_roles=True)
    async def reactionroles(self, ctx, action, role : typing.Optional[discord.Role]=None, emoji : typing.Optional[typing.Union[discord.PartialEmoji, str]]=None):
        if role != None and ctx.message.reference != None:
            if action == "add":
                messageid = ctx.message.reference.message_id
                try:
                    self.bot.dbinst.exec_query(self.bot.database, "insert into roles values(%s, %s, %s, %s)", (ctx.guild.id, role.id, messageid, str(emoji)), noreturn=True)
                    await self.update_reactionroles_cache()
                    await ctx.send("Added a reaction role.")
                except pymysql.err.IntegrityError: 
                    traceback.print_exc()
                    await ctx.send("Failed to add a reaction role, there might be a duplicate. Try deleting the reaction role you just tried to add.")
                except:
                    await ctx.send("There was an error while adding a reaction role. Try again.")
            if action == "delete":
                print("deleted a reaction role")
                if self.bot.dbinst.exec_query(self.bot.database, "delete from roles where role_id = %s", (role.id)) == "successful":
                    await ctx.send("Deleted a reaction role.")
                else:
                    await ctx.send(f"Failed to delete a reaction role, are there any reaction roles set up for role id '{str(role.id)}'? Try using '{str(await self.bot.get_prefix(ctx.message))}'reactionroles list all all' to see if you have any reaction roles set up.")
        elif action == "list":
            roles = self.bot.dbinst.exec_query(self.bot.database, "select * from roles where guild_id=%s", (ctx.guild.id), fetchall=True)
            reactionrolestring = ""
            if roles != "()": 
                reactionrolestring = f"{reactionrolestring} message id:  {str(each['message_id'])}  role id:  {str(each['role_id'])}  role name:  {discord.utils.get(ctx.guild.roles, id=int(each['role_id'])).name}  emoji:  {str(each['emoji'])}, "        
                print("listed reaction roles")
                await ctx.send("reaction roles: " + str(reactionrolestring[:-2]))
        elif ctx.message.reference == None:
            return await ctx.send("You need to reply to the message you want to add the reaction role to.")
        elif role == None:
            await ctx.send(f"It doesn't look like you've provided all of the required arguments. See `{await self.bot.get_prefix(ctx.message)}help reactionroles` for more details.")
            return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        #when a reaction is added, check if guild has any reaction roles set up
        if self.bot.dbinst.retrieve(self.bot.database, "roles", "guild_id", "guild_id", str(payload.guild_id), False) is not None:
            #if it does, check if there's a role associated with the emoji user reacted with
            if self.bot.dbinst.retrieve(self.bot.database, "roles", "role_id", "emoji", str(payload.emoji), False) is not None:
                #if so, get the role id associated with the emoji
                roleid = self.bot.dbinst.retrieve(self.bot.database, "roles", "role_id", "emoji", str(payload.emoji), False)
            else:
                #otherwise, get the role id associated with the message
                roleid = self.bot.dbinst.retrieve(self.bot.database, "roles", "role_id", "message_id", str(payload.message_id), False)
            #if the role is associated with the message/emoji, get the emoji and check if it matches the emoji the user reacted with (this might be redundant) 
            if roleid is not None:
                emoji = self.bot.dbinst.retrieve(self.bot.database, "roles", "emoji", "role_id", str(roleid), False)
                print(str(emoji))
                print(str(payload.emoji))
                if emoji == str(payload.emoji) or emoji == "None" or emoji == None:
                    #if it matches or is None, get the channel and role, then check if the person who reacted already had the role
                    ctx = self.bot.get_channel(payload.channel_id)
                    role = discord.utils.get(payload.member.guild.roles, id=int(roleid))
                    if role in payload.member.roles:
                        #if so, notify them
                        await ctx.send(f" <@!{payload.member.id}>, you already have the '{role.name}' role.", delete_after=5)
                        return
                    #otherwise, give them the role and notify them that they've recieved it
                    await payload.member.add_roles(role)
                    print("added role to user")
                    await ctx.send(f"Gave <@!{payload.member.id}> the '{role.name}' role.", delete_after=5)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if self.bot.dbinst.retrieve(self.bot.database, "roles", "guild_id", "guild_id", str(payload.guild_id), False) is not None:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            if self.bot.dbinst.retrieve(self.bot.database, "roles", "role_id", "emoji", str(payload.emoji), False) is not None:
                roleid = self.bot.dbinst.retrieve(self.bot.database, "roles", "role_id", "emoji", str(payload.emoji), False)
            else:
                roleid = self.bot.dbinst.retrieve(self.bot.database, "roles", "role_id", "message_id", str(payload.message_id), False)
            if roleid is not None:
                emoji = self.bot.dbinst.retrieve(self.bot.database, "roles", "emoji", "role_id", str(roleid), False)
                ctx = self.bot.get_channel(payload.channel_id)
                role = discord.utils.get(guild.roles, id=int(roleid))
                if emoji == str(payload.emoji) or emoji == "None" or emoji == None:
                    if role in member.roles:
                        await member.remove_roles(role)
                        print("removed role from user")
                        await ctx.send(f"Removed the '{role.name}' role from <@!{member.id}>.", delete_after=5)
                        return
                    await ctx.send(f"<@!{member.id}> For some reason, you don't have the '{role.name}' role, even though you reacted to this message. Try removing your reaction and adding your reaction again. If this keeps happening, notify tk421#2016.", delete_after=15)

def setup(bot):
    bot.add_cog(reactionroles(bot, True))

def teardown(bot):
    bot.remove_cog(reactionroles(bot))
