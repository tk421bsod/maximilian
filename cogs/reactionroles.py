import asyncio
import typing
import traceback
from random import randint

import discord
from discord.ext import commands

class reaction_role:
    def __init__(self, id, guild_id, message_id, emoji):
        self.id = id
        self.guild_id = guild_id
        self.message_id = message_id
        self.emoji = emoji

class reaction_roles(commands.Cog, name="reaction roles"):
    '''Reaction role commands'''
    def __init__(self, bot):
        self.bot = bot
        self.roles = {}
        asyncio.create_task(self.fill_cache())
        bot.settings.add_category("reactionroles", {"notify":"Notify users when their roles are updated"}, {"notify":None}, {"notify":"manage_guild"})
        #TODO: maybe create some sort of standardized cache object?

    async def fill_cache(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            self.roles[guild.id] = {}
            guild_roles = await self.bot.db.exec("select * from roles where guild_id = %s", (guild.id, ))
            if not guild_roles:
                continue
            if isinstance(guild_roles, dict): #dicts by themselves don't play nicely with the loop below, so wrap them in a list
                guild_roles = [guild_roles]
            for role in guild_roles:
                #{guild_id : {role_id : reaction_role}}
                self.roles[guild.id].update({int(role['role_id']):reaction_role(id=int(role['role_id']), guild_id=int(role['guild_id']), message_id=int(role['message_id']), emoji=role['emoji'])})

    def detect_changes(self, original, changed):
        changes = ""
        if original.emoji != changed.emoji:
            changes += f"**Emoji**: {original.emoji} -> {changed.emoji}\n"
        if original.message_id != changed.message_id:
            changes += f"**Message**: {original.message_id} -> {changed.message_id}\n"
        return changes

    async def complete_hook(self, ctx):
        if randint(1, 10) == 5:
            if self.bot.settings.reactionroles.ready:
                if self.bot.settings.reactionroles.notify.enabled(ctx.guild.id):
                    await ctx.send(self.bot.strings["ROLE_NOTIFY_ENABLED"].format(await self.bot.get_prefix(ctx.message)))
                else:
                    await ctx.send(self.bot.strings["ROLE_NOTIFY_DISABLED"].format(await self.bot.get_prefix(ctx.message)))

    async def role_confirmation_callback(self, message, ctx, confirmed, roleid, messageid, emoji):
        if confirmed:
            await ctx.send(self.bot.strings["UPDATING_ROLE"])
            await self.bot.db.exec("replace into roles values(%s, %s, %s, %s)", (ctx.guild.id, roleid, messageid, emoji))
            self.roles[ctx.guild.id][roleid] = reaction_role(roleid, ctx.guild.id, messageid, emoji)
            await ctx.send(embed=discord.Embed(title=self.bot.strings["ROLE_UPDATED"], color=self.bot.config['theme_color']))
        else:
            await ctx.send(self.bot.strings["ROLE_NOT_UPDATED"])
        await self.complete_hook(ctx)

    async def add_role(self, ctx, role, messageid, emoji):
        if role.id in [i for i in list(self.roles[ctx.guild.id].keys())]:
            changes = self.detect_changes(self.roles[ctx.guild.id][role.id], reaction_role(role.id, ctx.guild.id, messageid, emoji))
            if not changes:
                return await ctx.send(self.bot.strings["ROLE_NOT_CHANGED"])
            self.bot.confirmation(self.bot, discord.Embed(title=self.bot.strings["ROLE_CHANGED_TITLE"], description=self.bot.strings["ROLE_CHANGED_DESC"].format(changes), color=discord.Color.yellow()), ctx, self.role_confirmation_callback, role.id, messageid, emoji)
            return
        await self.bot.db.exec("insert into roles values(%s, %s, %s, %s)", (ctx.guild.id, role.id, messageid, emoji))
        self.roles[ctx.guild.id][role.id] = reaction_role(role.id, ctx.guild.id, messageid, emoji)
        await ctx.send(embed=discord.Embed(title=self.bot.strings["ROLE_ADDED"], color=self.bot.config['theme_color']))
        await self.complete_hook(ctx)

    async def delete_role(self, ctx, role):
        await self.bot.db.exec("delete from roles where guild_id=%s and role_id=%s", (ctx.guild.id, role.id))
        del self.roles[ctx.guild.id][role.id]
        await ctx.send(embed=discord.Embed(title=self.bot.strings["ROLE_DELETED"], color=self.bot.config['theme_color']))

    @commands.command(help="Add, remove, or list reaction roles, only works if you have the 'Manage Roles' permission. This command takes 4 arguments (1 optional), action (the action to perform, either `add`, `delete`, or `list`), role (a role, you can either mention it or provide the id), messageid (the id of the message you want people to react to), and emoji (the emoji you want people to react with, it must be in a server Maximilian is in or a default emoji, this can be blank if you want people to react with any emoji)", aliases=['reaction_role'])
    @commands.has_guild_permissions(manage_roles=True)
    async def reactionroles(self, ctx, action, role : typing.Optional[discord.Role]=None, messageid : typing.Optional[int]=None, emoji : typing.Optional[typing.Union[discord.PartialEmoji, str]]=None):
        if role and messageid:
            if action == "add":
                if len(list(self.roles[ctx.guild.id].values())) >= 24:
                    return await ctx.send("You can't have more than 24 reaction roles in one server for now.")
                try:
                    await self.add_role(ctx, role, messageid, emoji)
                except:
                    self.bot.logger.info(traceback.format_exc())
                    return await ctx.send("Something went wrong while adding that reaction role. Try again in a moment.")
            if action == "delete":
                if len(list(self.roles[ctx.guild.id].values())) == 0:
                    return await ctx.send("You don't have any reaction roles set up.")
                try:
                    self.roles[ctx.guild.id][role.id]
                except KeyError:
                    return await ctx.send("That reaction role doesn't exist.")
                await self.delete_role(ctx, role)
        elif action == "list":
            if len(list(self.roles[ctx.guild.id].values())) == 0:
                return await ctx.send("You don't have any reaction roles set up.")
            desc = ""
            for role in list(self.roles[ctx.guild.id].values()):
                if not role.emoji:
                    emoji = "Any"
                else:
                    emoji = role.emoji
                desc += f"<@&{role.id}>\nMessage ID: {role.message_id} \nEmoji: {emoji}\n\n"
            await ctx.send(embed=discord.Embed(title="Reaction roles in this server:", description=desc, color=self.bot.config['theme_color']))
        elif not messageid or not role:
            await ctx.send(f"It doesn't look like you've provided all of the required arguments. See `{await self.bot.get_prefix(ctx.message)}help reactionroles` for more details.")
            return

    def lookup_role_by_message(self, guildid, messageid):
        for role in list(self.roles[guildid].values()):
            if role.message_id == messageid:
                return role
        return None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.roles[payload.guild_id]:
            role = self.lookup_role_by_message(payload.guild_id, payload.message_id)
            if role:
                if role.emoji == str(payload.emoji) or role.emoji == "None" or not role.emoji:
                    ctx = self.bot.get_channel(payload.channel_id)
                    roletoadd = discord.utils.get(payload.member.guild.roles, id=int(role.id))
                    if roletoadd in payload.member.roles:
                        await ctx.send(f" <@!{payload.member.id}>, you already have the '{roletoadd.name}' role.", delete_after=5)
                        return
                    await payload.member.add_roles(roletoadd)
                    print("added role to user")
                    if self.bot.settings.reactionroles.notify.enabled(payload.guild_id):
                        await ctx.send(f"Gave <@!{payload.member.id}> the '{roletoadd.name}' role.", delete_after=5)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if self.roles[payload.guild_id]:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = self.lookup_role_by_message(payload.guild_id, payload.message_id)
            if role:
                ctx = self.bot.get_channel(payload.channel_id)
                roletoadd = discord.utils.get(guild.roles, id=role.id)
                if role.emoji == str(payload.emoji) or role.emoji == "None" or not role.emoji:
                    if roletoadd in member.roles:
                        await member.remove_roles(roletoadd)
                        if self.bot.settings.reactionroles.notify.enabled(payload.guild_id):
                            await ctx.send(f"Removed the '{roletoadd.name}' role from <@!{member.id}>.", delete_after=5)
                        return
                    await ctx.send(f"<@!{member.id}> For some reason, you don't have the '{roletoadd.name}' role, even though you reacted to this message. Try removing your reaction and adding your reaction again. If this keeps happening, notify tk421#7244.", delete_after=15)

async def setup(bot):
    await bot.add_cog(reaction_roles(bot))

async def teardown(bot):
    await bot.remove_cog(reaction_roles(bot))
