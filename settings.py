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
        The permission this setting requires. 
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
        print(f"Registering setting '{name}'")
        setattr(category, name.strip().replace(" ", "_"), self)

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

        Raises
        ------

        AttributeError, KeyError
            The Category the setting belongs to hasn't been fully initialized yet.
        """
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

    fill_settings_cache
        Fills the Category's cache with new setting data. 

    update_setting
        Updates a setting's state in the database, then calls `update_cached_state`.

    update_cached_state
        Updates a setting's state in the cache.

    Attributes
    ----------

    ready
        Whether settings are ready to be used. False until fill_settings_cache has completed.
    """
    def __init__(self, constructor, name, settingdescmapping, unusablewithmapping, permissionmapping):
        self._ready = False
        self.settingdescmapping = settingdescmapping
        self.unusablewithmapping = unusablewithmapping
        #make category accessible through 'bot.settings.<category>'
        setattr(constructor, name, self)
        self.name = name
        self.filling = False
        self.logger = constructor.logger
        self.bot = constructor.bot
        self.permissionmapping = permissionmapping
        asyncio.create_task(self.fill_settings_cache())

    @property
    def ready(self):
        return self._ready

    def get_setting(self, name):
        return getattr(self, name.strip().replace(" ", "_"))

    def get_initial_state(self, setting):
        """
        Gets the initial state of a setting.
        """
        if setting['enabled'] is not None:
            return bool(setting['enabled'])
        return False

    async def add_to_db(self, name):
        for guild in self.bot.guilds:
            try:
                self.bot.db.exec_safe_query('insert into config values(%s, %s, %s, %s)', (guild.id, self.name, name, False))
            except IntegrityError:
                continue
            self.data.append({'setting':name, 'category':self.name, 'guild_id':guild.id, 'enabled':False})

    async def fill_settings_cache(self):
        """
        Fills a Category's settings cache with data.
        """
        await self.bot.wait_until_ready()
        self.logger.info(f"Filling cache for category {self.name}...")
        self.filling = True
        #step 1: get data for each setting, add settings to db if needed
        try:
            self.data = self.bot.db.exec_safe_query('select * from config where category=%s order by setting', (self.name), fetchall=True)
            if not isinstance(self.data, list):
                self.data = [self.data]
        except:
            traceback.print_exc()
            self.logger.warning('An error occurred while filling the setting cache, defaulting to every setting disabled')
            self.data = []
            #if something went wrong, default to everything disabled
            for name in list(self.settingdescmapping.keys()):
                for guild in self.bot.guilds:
                    self.data.append({'setting':name, 'category':self.name, 'guild_id':guild.id, 'enabled':False})
        else:
            #step 2: ensure each setting has an entry
            for name in list(self.settingdescmapping.keys()):
                if not self.data[0] or name not in [i['setting'] for i in self.data]:
                    self.logger.info(f"Setting '{name}' wasn't found in the database. Adding it.")
                    if not self.data[0]:
                        del self.data[0] #edge case where query would return None
                    await self.add_to_db(name)
        #step 3: for each setting, get initial state and register it
        states = {}
        for setting in self.data:
            print(setting)
            if self.permissionmapping:
                permission = self.permissionmapping[setting['setting']]
            else:
                permission = None
            states[setting['guild_id']] = self.get_initial_state(setting)
            #if we've finished populating list of states for a setting...
            if len(list(states.keys())) >= len(self.bot.guilds):
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
        self.bot.db.exec_safe_query("update config set enabled=%s where guild_id=%s and category=%s and setting=%s", (not setting.states[ctx.guild.id], ctx.guild.id, self.name, setting.name))
        await self.update_cached_state(ctx, setting)

    async def _prepare_conflict_string(self, conflicts):
        q = "'" # hashtag lifehack!!1!! lets me escape quotes in fstrings like a girlboss!!
        if not isinstance(conflicts, list):
            return f"{q}*{conflicts}*{q}"
        return f"{', '.join([f'{q}*{i}*{q}' for i in conflicts[:-1]])} and '*{conflicts[-1]}*'"

    async def _resolve_conflicts(self, ctx, setting):
        if isinstance(setting.unusablewith, list):
            resolved = []
            for conflict in setting.unusablewith:
                #get the Setting matching the name
                conflict = self.get_setting(conflict)
                if conflict.enabled():
                    await self.update_setting(ctx, conflict)
                    resolved.append(conflict)
        else:
            #no conflict? do nothing
            if not setting.unusablewith:
                return ""
            #conflicting setting enabled? disable it
            if self.get_setting(setting.unusablewith).enabled():
                await self.update_setting(ctx, setting.unusablewith)
                resolved = setting.unusablewith
        if len(resolved) == 1:
            resolved = resolved[0]
        if not resolved:
            return ""
        return f"**Automatically disabled** {await self._prepare_conflict_string(resolved)} due to {'a conflict' if len(resolved) == 1 else 'conflicts'}."

    def normalize_permission(self, permission):
        '''Makes a permission name more human readable. Replaces \'guild\' with \'server\', capitalizes words, swaps underscores for spaces.'''
        return permission.replace("guild", "server").replace("_", " ").title()

    async def config(self, ctx, name=None):
        '''Toggles the specified setting. Settings are off by default.'''
        if not name:
            if self.name != "general":
                title = f"Settings for category '{self.name}'"
            else:
                title = "General settings"
            embed = discord.Embed(title=title, color=0x3498db) 
            for setting in [self.get_setting(i) for i in list(self.settingdescmapping.keys())]:
                if setting.unusablewith:
                    unusablewithwarning = f"Cannot be enabled at the same time as {await self.prepare_conflict_string(setting.unusablewith)}."
                else:
                    unusablewithwarning = ""
                if setting.permission:
                    perms = f"\nRequires the **{self.normalize_permission(setting.permission)}** permission."
                else:
                    perms = ""
                embed.add_field(name=f"{discord.utils.remove_markdown(setting.description.capitalize())} ({setting.name})", value=f"{'❎ Disabled' if not setting.states[ctx.guild.id] else '✅ Enabled'}\n{unusablewithwarning}{perms}", inline=True)
            embed.set_footer(text="If you want to toggle a setting, run this command again and specify the name of the setting. Setting names are shown above in parentheses. Settings only apply to your server.")
            return await ctx.send(embed=embed)
        setting = self.get_setting(name)
        if setting.permission:
            #why am i doing this. i haet thiss
            if not getattr(ctx.channel.permissions_for(ctx.author), setting.permission):
                return await ctx.send(f"It looks like you don't have permission to change this setting.\nYou'll need the **{self.normalize_permission(setting.permission)}** permission to change it.\nUse the `userinfo` command to check your permissions.")
        try:
            #update setting state
            await self.update_setting(ctx, setting)
            #check for conflicts and resolve them
            unusablewithmessage = await self._resolve_conflicts(ctx, setting)
        except:
            await self.bot.core.send_traceback()
            await ctx.send(f"Something went wrong while changing that setting. Try again in a moment. \nI've reported this error to my owner. If this keeps happening, consider opening an issue at https://github.com/tk421bsod/maximilian/issues.")
            return await self.bot.core.send_debug(ctx)
        await ctx.send(embed=discord.Embed(title="Changes saved.", description=f"**{'Disabled' if not setting.enabled(ctx.guild.id) else 'Enabled'}** *{setting.description}*.\n{unusablewithmessage}", color=0x3498db).set_footer(text=f"Send this command again to turn this back {'off' if setting.enabled(ctx.guild.id) else 'on'}."))


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

    def add_category(self, category, settingdescmapping, unusablewithmapping, permissionmapping=None):
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

        permissionmapping : dict(str:str)=None
            An optional mapping of setting name to permission name.
            Use this to control access to settings in the category.
            Map a setting name to None to make it available to everyone.
            Note that only guild-wide permissions are checked using this.
        """
        self.logger.info(f"Registering category '{category}`...")
        if getattr(self, category, None) != None:
            self.logger.warn(f"add_category was called twice for category '{category}'!!")
            self.logger.warn("Don't try to update a category after creation. Doing so may break stuff.")
            return
        Category(self, category, settingdescmapping, unusablewithmapping, permissionmapping)
        self.categorynames.append(category)
        self.logger.info(f"Category '{category}' registered. Access it at bot.settings.{category}.")

    async def config(self, ctx, category:str=None, *, setting:str=None):
        """
        A command that changes settings.
        """
        if not category:
            if self.categorynames:
                available = "\n".join([f"`{i}`" for i in self.categorynames])
            else:
                available = "None"
            return await ctx.send(f"You need to specify a setting category.\nYou can choose from one of the following:\n{available}\nLooking for bot-wide settings? Use `config general`.")
        try:
            category = getattr(self, category) 
        except AttributeError:
            return await ctx.send("That category doesn't exist. Check the spelling.")
        try:
            if not category.ready and not category.filling:
                await category.fill_settings_cache()
            await category.config(ctx, setting)
        except RuntimeError:
            return await ctx.send("That setting doesn't exist.")
        except AttributeError:
            traceback.print_exc()
            return await ctx.send("That category wasn't set up properly.")
