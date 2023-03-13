from pymysql.err import IntegrityError

import asyncio
import collections
import logging
import traceback

import discord
from discord.ext import commands

class Setting():
    """
    An object that represents a setting and its state.
    Please don't directly instantiate this.
    If you want to add settings, use settings.add_category.

    Methods
    -------

    enabled
        Returns if the setting is enabled for the specified guild.

    Attributes
    ----------

    states : dict(int:bool)
        A mapping of guild id to setting state for that guild.

    description : str
        The setting's description. Provided by the Category's settingdescmapping.

    unusablewith : Union[str, list]
        Settings this setting conflicts with. Provided by the Category's unusablewithmapping. 

    permission : str
        The permission this setting requires, as a string. Must be a valid discord.Permission e.g manage_guild.
    """
    def __init__(self, category, name, states, permission):
        self.states = states
        self.description = category.settingdescmapping[name]
        self.name = name
        self.unusablewith = category.unusablewithmapping[name]
        self.category = category
        self.permission = permission
        #add this setting as an attr of category
        #one can access it via 'bot.settings.<category>.<setting>'
        setattr(category, name.strip().replace(" ", "_"), self)
        category.logger.info(f"Registered setting {name}")

    def enabled(self, guild_id):
        """
        enabled(guild_id:int)
        Returns a boolean specifying whether this setting is enabled in the specified guild.

        Returns
        -------

        True
            The setting is enabled.

        False
            The setting is disabled.

       None
            The setting's state couldn't be determined.

        """
        if not self.category.ready:
            self.category.logger.warn(f"{self.name}.enabled was called before its parent category was ready!")
            self.category.logger.warn("This may cause issues. Consider awaiting Category.wait_ready before anything that depends on setting states.")
        try:
            return self.states[guild_id]
        except:
            return None

class Category():
    """
    An object that represents a collection of Settings.
    Please don't directly instantiate this.
    Use the `add_category` method instead.

    Want to update a Category after creation?
    Don't. You shouldn't need to.

    Methods
    -------

    fill_cache
        Fills the Category's cache with new setting data. 

    update_setting
        Updates a setting's state in the database, then calls `update_cached_state`.

    update_cached_state
        Updates a setting's state in the cache.

    Attributes
    ----------

    ready
        Whether settings are ready to be used. False until fill_cache has completed.
        Warning:
            If False, the behavior of calls to Setting.enabled() is unpredictable.
            Those calls could return None or even result in an AttributeError depending on the initialization state of the setting.
    """
    def __init__(self, constructor, name, settingdescmapping, unusablewithmapping, permissionmapping):
        self._ready = False
        self.settingdescmapping = settingdescmapping
        self.unusablewithmapping = unusablewithmapping
        #make category accessible through 'bot.settings.<category>'
        setattr(constructor, name, self)
        self.name = name
        self.filling = False
        self.logger = logging.getLogger(f"settings.{name}") #TODO: rethink this. this isn't entirely needed and could introduce some overhead
        self.bot = constructor.bot
        self.permissionmapping = permissionmapping
        asyncio.create_task(self.fill_cache())

    @property
    def ready(self):
        return self._ready

    async def wait_ready(self):
        """
        Waits until settings are ready to be used.
        """
        while not self.ready:
            await asyncio.sleep(0.01)

    def get_setting(self, name):
        """
        Gets a Setting by name.
        """
        return getattr(self, name.strip().replace(" ", "_"), None)

    def get_initial_state(self, setting):
        """
        Gets the initial state of a setting.
        """
        if setting['enabled'] is not None:
            return bool(setting['enabled'])
        return False

    async def add_to_db(self, name, total_guilds):
        """
        Attempts to add a setting to the database.
        """
        target_guilds = []
        if self.data:
            target_guilds = [i['guild_id'] for i in self.data if i['setting'] == name]
        for guild in total_guilds:
            if guild.id in target_guilds:
                continue
            try:
                self.logger.debug(f"state not found for setting {name} in guild {guild.id}, adding it to database")
                self.bot.db.exec('insert into config values(%s, %s, %s, %s)', (guild.id, self.name, name, False))
            except IntegrityError:
                continue
            self.data.append({'setting':name, 'category':self.name, 'guild_id':guild.id, 'enabled':False})

    async def fill_cache(self):
        """
        Fills a Category's settings cache with data.
        """
        await self.bot.wait_until_ready()
        self.logger.info(f"Filling cache for category {self.name}...")
        self.filling = True
        guilds = self.bot.guilds #stop state population from breaking if guilds change while filling cache
        #step 1: get data for each setting, add settings to db if needed
        try:
            self.data = self.bot.db.exec('select * from config where category=%s order by setting', (self.name), fetchall=True)
            if self.data is None:
                self.data = []
            if not isinstance(self.data, list):
                self.data = [self.data]
        except:
            #TODO: Consider loudly failing instead of handling this as this state is undesireable and messes with existing settings
            traceback.print_exc()
            self.logger.warning('An error occurred while filling the setting cache, defaulting to every setting disabled')
            self.data = []
            #if something went wrong, default to everything disabled
            for name in list(self.settingdescmapping.keys()):
                for guild in guilds:
                    self.data.append({'setting':name, 'category':self.name, 'guild_id':guild.id, 'enabled':False})
        else:
            self.logger.info("Validating setting states...")
            #step 2: ensure each setting has an entry
            for name in list(self.settingdescmapping.keys()):
                if self.get_setting(name):
                    delattr(self, name.replace(" ", "_"))
                await self.add_to_db(name, guilds)
        #step 3: for each setting, get initial state and register it
        states = {}
        self.logger.debug("Populating setting states...")
        for index, setting in enumerate(self.data):
            self.logger.debug(f"Processing entry {setting}")
            if self.permissionmapping:
                permission = self.permissionmapping[setting['setting']]
            else:
                permission = None
            states[setting['guild_id']] = self.get_initial_state(setting)
            #if we've finished populating list of states for a setting...
            if index+1 == len(self.data) or self.data[index+1]['setting'] != setting['setting']:
                #create new Setting, it automatically sets itself as an attr of this category
                Setting(self, setting['setting'], states, permission)
                states = {}
        self.logger.info("Done filling settings cache.")
        self._ready = True
        self.filling = False

    async def update_cached_state(self, ctx:commands.Context, setting:Setting):
        """
        Changes a setting's state in cache. Doesn't affect the database.
        """
        setting.states[ctx.guild.id] = not setting.states[ctx.guild.id]

    async def update_setting(self, ctx:commands.Context, setting:Setting):
        """
        Changes a setting's state in the database. Calls update_cached_state to change a setting's state in cache.
        """
        self.bot.db.exec("update config set enabled=%s where guild_id=%s and category=%s and setting=%s", (not setting.states[ctx.guild.id], ctx.guild.id, self.name, setting.name.replace("_", " ")))
        await self.update_cached_state(ctx, setting)

    async def _prepare_conflict_string(self, conflicts):
        """
        Returns a string describing conflicting settings.
        """
        q = "'"
        if not isinstance(conflicts, list):
            return f"{q}*{conflicts}*{q}"
        return self.bot.strings["CONFLICT_STRING_MULTIPLE"].format(', '.join([f'{q}*{i}*{q}' for i in conflicts[:-1]]), conflicts[-1])

    async def _resolve_conflicts(self, ctx, setting):
        """
        Resolves conflicts between settings.
        """
        if isinstance(setting.unusablewith, list):
            resolved = []
            for conflict in setting.unusablewith:
                #get the Setting matching the name
                conflict = self.get_setting(conflict)
                if conflict.enabled(ctx.guild.id):
                    await self.update_setting(ctx, conflict)
                    resolved.append(conflict)
        else:
            #no conflict? do nothing
            if not setting.unusablewith:
                return ""
            #conflicting setting enabled? disable it
            if self.get_setting(setting.unusablewith).enabled(ctx.guild.id):
                await self.update_setting(ctx, setting.unusablewith)
                resolved = setting.unusablewith
        length = len(resolved)
        if length == 1:
            resolved = resolved[0]
        if not resolved:
            return ""
        resolved_string = await self._prepare_conflict_string(resolved)
        if length == 1:
            return self.bot.strings["SETTING_AUTOMATICALLY_DISABLED"].format(resolved)
        return self.bot.strings["SETTINGS_AUTOMATICALLY_DISABLED"].format(resolved)

    def normalize_permission(self, permission):
        """Makes a permission name more human readable. Replaces \'guild\' with \'server\', capitalizes words, swaps underscores for spaces."""
        return permission.replace("guild", "server").replace("_", " ").title()

    async def config(self, ctx, name=None):
        """Toggles the specified setting. Settings are off by default."""
        #setting not specified? show list of settings
        if not name:
            if self.name != "general":
                title = self.bot.strings["CURRENTSETTINGS_TITLE"].format(self.name)
            else:
                title = self.bot.strings["GENERAL_CATEGORY"]
            embed = discord.Embed(title=title, color=self.bot.config['theme_color'])
            for setting in [self.get_setting(i) for i in list(self.settingdescmapping.keys())]:
                if setting.unusablewith:
                    unusablewithwarning = self.bot.strings["SETTING_UNUSABLE_WITH"].format(await self._prepare_conflict_string(setting.unusablewith))
                else:
                    unusablewithwarning = ""
                if setting.permission:
                    perms = self.bot.strings["SETTING_REQUIRES_PERMISSION"].format(self.normalize_permission(setting.permission))
                else:
                    perms = ""
                embed.add_field(name=self.bot.strings["SETTING_ENTRY_NAME"].format(discord.utils.remove_markdown(setting.description.capitalize()), setting.name), value=f"{self.bot.strings['SETTING_CURRENTLY_DISABLED'] if not setting.states[ctx.guild.id] else self.bot.strings['SETTING_CURRENTLY_ENABLED']}\n{unusablewithwarning}{perms}", inline=True)
            embed.set_footer(text=self.bot.strings["CURRENTSETTINGS_FOOTER"])
            return await ctx.send(embed=embed)
        setting = self.get_setting(name)
        if not setting:
            return await ctx.send(self.bot.strings["UNKNOWN_SETTING"])
        if setting.permission:
            if not getattr(ctx.channel.permissions_for(ctx.author), setting.permission):
                return await ctx.send(self.bot.strings["SETTING_PERMISSION_DENIED"].format(self.normalize_permission(setting.permission)))
        try:
            #update setting state
            await self.update_setting(ctx, setting)
            #check for conflicts and resolve them
            unusablewithmessage = await self._resolve_conflicts(ctx, setting)
        except:
            await self.bot.core.send_traceback()
            await ctx.send(self.bot.strings["SETTING_ERROR"])
            return await self.bot.core.send_debug(ctx)
        await ctx.send(embed=discord.Embed(title=self.bot.strings["SETTING_CHANGED_TITLE"], description=f"**{self.bot.strings['SETTING_DISABLED'] if not setting.enabled(ctx.guild.id) else self.bot.strings['SETTING_ENABLED']}** *{setting.description}*.\n{unusablewithmessage}", color=self.bot.config['theme_color']).set_footer(text=f"{self.bot.strings['SETTING_ENABLED_FOOTER'] if setting.enabled(ctx.guild.id) else self.bot.strings['SETTING_DISABLED_FOOTER']}"))


class settings():
    """
    A class that allows extensions to easily add settings
    """
    def __init__(self, bot):
        """
        Parameters
        ----------

        bot : discord.ext.commands.Bot
            The main Bot instance.
        """
        self.bot = bot
        self.settings = {}
        self.logger = logging.getLogger("settings")
        self.logger.info(f"Settings module initialized.")
        self.unusablewithmessage = ""
        self.categorynames = []

    def add_category(self, category, settingdescmapping, unusablewithmapping, permissionmapping):
        """
        A wrapper for creating a new Category instance. Its purpose is to allow a category to register as an attribute of the main settings instance.
        After this returns and the Category's 'ready' attribute is True, you can check the value of settings using `bot.settings.<category>.<setting>.enabled()`.

        Parameters
        ----------

        category : str
            The name of the category. This will be used to view and toggle settings. (think `config <category> <setting>`)

        settingdescmapping : dict(str:str)
            A mapping of setting name to description.
            Descriptions show up when viewing and toggling settings.
            Example:
                {'a':'spam'}
                Setting 'a' has the description 'spam'.
                Toggling 'a' will show 'Enabled/Disabled *spam*.'
                Viewing settings for the category will show 'spam (a) \nEnabled/Disabled'

        unusablewithmapping : dict(str:Union[list, str]=None)
            A mapping of setting name to names of settings that conflict.
            This allows the settings system to detect and resolve conflicts.
            This must be a dict with setting names as keys.
            There are three different types used to declare conflicts (or lack thereof):

                None
                    No conflict.

                List
                    More than 1 conflict.

                Str
                    1 conflict.


            Example:
                {'a':['spam', 'eggs'], 'b':'a'}
                Setting 'a' conflicts with settings 'spam' and 'eggs'.
                Setting 'b' conflicts with setting 'a'.

        permissionmapping : dict(str:str)
            A mapping of setting name to permission name.
            Use this to control access to settings in the category.
            Map a setting name to None to make it available to everyone.
            Note that channel permission overrides apply.

            Example:
                {'a':'manage_guild', 'b':None}
                Setting 'a' requires the 'Manage Server' permission.
                Setting 'b' doesn't require any permissions.
        """
        self.logger.info(f"Registering category '{category}`...")
        if getattr(self, category, None) != None: #a category instance already exists??
            self.logger.warn(f"add_category was called twice for category '{category}'!!")
            self.logger.warn("Don't try to update a category after creation. Doing so may break stuff.")
            return
        Category(self, category, settingdescmapping, unusablewithmapping, permissionmapping)
        self.categorynames.append(category)
        self.logger.info(f"Category '{category}' registered. Access it at bot.settings.{category}. Settings are unavailable until bot.settings.{category}.ready == True.")

    def _prepare_category_string(self):
        if self.categorynames:
            return "\n".join([f"`{i}`" for i in self.categorynames])
        else:
            return "None"

    async def config(self, ctx, category:str=None, *, setting:str):
        """
        A command that changes settings.
        """
        #figure out what category we're using
        if not category:
            available = self._prepare_category_string()
            return await ctx.send(self.bot.strings["CATEGORY_NOT_SPECIFIED"].format(available))
        try:
            category = getattr(self, category)
        except AttributeError:
            available = self._prepare_category_string()
            return await ctx.send(self.bot.strings["UNKNOWN_CATEGORY"].format(available))
        try:
            if not category.ready:
                self.logger.error(f"It looks like cache filling for category {category.name} is happening way too late!!!")
                self.logger.error("please report this issue to tk421.")
                self.logger.error("waiting until cache fill is complete...")
                await ctx.send(self.bot.strings["CATEGORY_NOT_READY"])
                await category.wait_ready()
                self.logger.error("cache fill complete, continuing :)")
            await category.config(ctx, setting)
        except AttributeError:
            traceback.print_exc()
            return await ctx.send(self.bot.strings["CATEGORY_INVALID"])

if __name__ == "__main__":
    import sys; print(f"It looks like you're trying to run {sys.argv[0]} directly.\nThis module provides a set of APIs for other modules and doesn't do much on its own.\nLooking to run Maximilian? Just run main.py.")
