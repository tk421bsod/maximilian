"""
Some utility classes intended for use by modules.
These are accessible through the Bot instance passed into your module.
"""
import asyncio
import inspect

import discord

import common

class ConfirmationView(discord.ui.View):
    """A View subclass intended for use by a confirmation."""

    #TODO: Consider somehow passing the raw Interaction to callbacks instead of having to pass followups.
    #Perhaps we could require consumers to pass an interaction_callback coro when constructing a confirmation.
    #From there we could send it the Interaction and View and let it handle everything.

    __slots__ = ("confirmed", "confirm_followup", "cancel_followup")

    def __init__(self, confirm_followup=None, cancel_followup=None):
        super().__init__()
        self.confirmed = None
        self.confirm_followup = confirm_followup
        self.cancel_followup = cancel_followup

    def remove_children(self):
        for item in self.children:
            self.remove_item(item)

    @discord.ui.button(label='\U00002705', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        if self.confirm_followup:
            await interaction.channel.send(self.confirm_followup)
        self.remove_children()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label='\U0000274e', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        if self.cancel_followup:
            await interaction.channel.send(self.cancel_followup)
        self.remove_children()
        await interaction.response.edit_message(view=self)
        self.stop()

class confirmation:
    """A class that handles a bit of confirmation logic."""

    __slots__ = ("bot")

    def __init__(self, bot, followups, to_send, ctx, callback, *additional_callback_args):
        '''Handles a bit of confirmation logic for you. You\'ll need to provide a callback coroutine that takes at least (message:discord.Message, ctx:discord.ext.commands.Context, confirmed:bool). Obviously it should also take anything else you pass to additional_callback_args.'''
        self.bot = bot
        if not inspect.iscoroutinefunction(callback):
            raise TypeError("Confirmation callback must be a coroutine.")
        #call handle_confirmation to prevent weird syntax like
        #await confirmation()._handle_confirmation()
        asyncio.create_task(self._handle_confirmation(followups, to_send, ctx, callback, *additional_callback_args))

    async def _handle_confirmation(self, followups, to_send, ctx, callback, *additional_callback_args):
        '''Handles a confirmation, transferring control to a callback once ConfirmationView exits'''
        view = ConfirmationView(confirm_followup=followups[0], cancel_followup=followups[1])
        if isinstance(to_send, discord.Embed):
            message = await ctx.send(embed=to_send, view=view)
        else:
            message = await ctx.send(to_send, view=view)
        await view.wait()
        return await callback(message, ctx, view.confirmed, *additional_callback_args)

class DeletionRequestAlreadyActive(BaseException):
    """A custom exception raised when a deletion request is already active. May be removed in the future."""
    pass

#TODO: WE REALLY SHOULD RECONSIDER DELETION REQUESTS. DO WE NEED THIS AT ALL
#It's a ton of extra code for two very specific use cases and is only really kept because I'm lazy :)
class deletion_request:
    __slots__ = ("bot", "mainembeds", "clearedembeds")

    def __init__(self, bot):
        '''A class that handles some deletion request logic. Has some similar attributes to `confirmation` but doesn't subclass as `confirmation`'s __init__ calls _handle_confirmation (subclassing may cause naming conflicts too)'''
        #mainembeds and clearedembeds are mappings of type to embed (see https://discord.com/developers/docs/resources/channel#embed-object for information on the format of these embeds)
        self.mainembeds = {"todo":{'fields': [{'inline': True, 'name': bot.strings['CLEAR_EFFECTS_TITLE'], 'value': bot.strings["CLEAR_TODO_LIST_EFFECTS_DESC"]}, {'inline': False, 'name': bot.strings['CONFIRMATION_OPTIONS_TITLE'], 'value': bot.strings['CONFIRMATION_OPTIONS']}], 'color': 7506394, 'type': 'rich', 'description': bot.strings["CLEAR_TODO_LIST_DESC"], 'title': bot.strings['CLEAR_TODO_LIST_TITLE']}, "all":{'fields': [{'inline': True, 'name': bot.strings['CLEAR_EFFECTS_TITLE'], 'value': bot.strings['CLEAR_ALL_EFFECTS_DESC']}, {'inline': False, 'name': bot.strings['CONFIRMATION_OPTIONS_TITLE'], 'value': bot.strings['CONFIRMATION_OPTIONS']}], 'color': 7506394, 'type': 'rich', 'description': bot.strings['CLEAR_ALL_DESC'], 'title': bot.strings['CLEAR_ALL_TITLE']}}
        self.clearedembeds = {"todo":{'color': 7506394, 'type': 'rich', 'title': bot.strings['CLEARED_TODO_LIST']}, "all":{'color': 7506394, 'type': 'rich', 'title': bot.strings['CLEARED_ALL']}}
        self.bot = bot

    async def confirmation_callback(self, message, ctx, confirmed, requesttype, id):
        try:
            if confirmed:
                if requesttype == "todo":
                    await self.bot.db.exec("delete from todo where user_id = %s", (ctx.author.id,))
                    await self.bot.get_cog('reminders').update_todo_cache()
                elif requesttype == "all":
                    await self.delete_all(ctx)
                await self.bot.db.exec("delete from active_requests where id = %s", (id,))
                await ctx.send(embed=discord.Embed.from_dict(self.clearedembeds[requesttype]))
                return True
            if not confirmed:
                await self.bot.db.exec("delete from active_requests where id = %s", (id,))
                return True
        except Exception as e:
            #clean up
            await self.bot.db.exec("delete from active_requests where id = %s", (id,))
            #then re-raise the error
            #this **will** cancel the confirmation
            raise e
        return False

    async def _handle_request(self, id, requesttype, ctx):
        try:
            confirmation(self.bot, [self.bot.strings["DELETION_CONFIRMED"], self.bot.strings["DELETION_DENIED"]], discord.Embed.from_dict(self.mainembeds[requesttype]), ctx, self.confirmation_callback, requesttype, id)
        except asyncio.TimeoutError:
            await self.bot.db.exec("delete from active_requests where id = %s", (id,))
            await ctx.send(self.bot.strings["DELETION_TIMEOUT"])
            return

    async def create_request(self, requesttype, ctx):
        '''Attempts to create a deletion request, raises DeletionRequestAlreadyActive if one's active'''
        id = ctx.guild.id if requesttype == 'all' else ctx.author.id
        result = await self.bot.db.exec("select id from active_requests where id=%s", (id,))
        if not result:
            await self.bot.db.exec("insert into active_requests values(%s)", (id,))
            await self._handle_request(id, requesttype, ctx)
        elif result:
            raise DeletionRequestAlreadyActive()

    async def delete_all(self, ctx):
        #TODO: More elegant solution than whatever the hell this is
        await self.bot.db.exec("delete from roles where guild_id = %s", (ctx.guild.id,))
        await self.bot.db.exec("delete from responses where guild_id = %s", (ctx.guild.id,))
        await self.bot.db.exec("delete from prefixes where guild_id = %s", (ctx.guild.id,))
        responses = self.bot.get_cog("Custom Commands")
        await responses.fill_cache()
        await self.bot.prefixes.update_prefix_cache()

class _ThemedEmbed(discord.Embed):
    def __init__(self, theme_color, *args, **kwargs):
        if common.get_value(kwargs, "color"):
            color = kwargs.pop("color")
        else:
            color = theme_color
        kwargs['color'] = color
        super().__init__(*args, **kwargs)
