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
    """
    def __init__(self, category, name, states):
        self.states = states
        self.description = category.settingdescmapping[name]
        self.name = name
        self.unusablewith = category.unusablewithmapping[name]
        self.category = category
        #add this setting as an attr of category
        #one can access it via 'bot.settings.<category>.<setting>'
        setattr(category, name, self)

#the following shouldn't be used,,,,
#    def __getattribute__(self, attr):
 #       #use __getattribute__ of another instance...
  #      #because doing it on this instance would cause an infinite loop :(
   #     get_attr = super(Setting, self).__getattribute__
    #    category = get_attr("category")
     #   #hopefully getattr is fine since we're getting attr of a seperate object
      #  if not getattr(category, "ready"):
       #     raise discord.ext.commands.CommandError("This setting isn't ready for use yet.")
        #return get_attr(attr)

    def enabled(self, guild_id):
        """
        enabled(guild_id:int)
        Returns a boolean specifying whether this setting is enabled.
        
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

        AttributeError
            The Category the setting belongs to hasn't been fully initialized yet.
        """
        try:
            return self.states[guild_id]
        except:
            return None

class Category():
    """
    An object that represents a collection of Settings.
    Directly instantiating this is discouraged. Use the `add_category` method instead.

    Methods
    -------

    fill_settings_cache
        Fills the category's cache with new setting data. 

    update_setting
        Updates a setting's state in the database, then calls `update_cached_state`.

    update_cached_state
        Updates a setting's state in the cache. Much faster than fill_settings_cache as it only affects one setting and doesn't hit the database.

    config
        Toggles a setting, if specified. Not specifying a setting shows the status of all settings in the category.

    Attributes
    ----------

    ready
        Whether settings are ready to be used. False until fill_settings_cache has completed.
     """
    def __init__(self, constructor, name, settingdescmapping, unusablewithmapping):
        self._ready = False
        self.settingdescmapping = settingdescmapping
        self.unusablewithmapping = unusablewithmapping
        #more setattr shenanigans
        #make category accessible through 'bot.settings.<category>'
        setattr(constructor, name, self)
        self.name = name
        #can't fill the settings cache here because of dpy asyncio changes...
        #we'll just wait until !config is used
        self.filling = False
        self.logger = constructor.logger
        self.bot = constructor.bot

    def default_false(self):
        return False

    @property
    def ready(self):
        return self._ready

    async def fill_settings_cache(self):
        """
        Fills a Category's settings cache with data.
        """
        self.logger.info(f"Filling cache for category {self.name}...")
        self.filling = True
        #TODO: fix design flaw described below...
        #if the following conditions are true:
        #1. at least 1 setting isn't in the database
        #2. at least 1 setting is in the database
        #at least one setting won't be present in cache
        try:
            data = self.bot.dbinst.exec_safe_query('select * from config where category=%s', (self.name), fetchall=True)
        except:
            traceback.print_exc()
            self.logger.warning('An error occurred while filling the setting cache, falling back to every setting disabled')
            data = []
            #if something went wrong, fall back to everything off to prevent console spam
            for name in list(self.settingdescmapping.keys()):
                for guild in self.bot.guilds:
                    data.append({'setting':name, 'guild_id':guild.id, 'enabled':False})
        else:
            if not data:
                self.logger.info("No settings are in the database for some reason. Creating an entry for each setting and falling back to every setting disabled")
                data = []
                for name in list(self.settingdescmapping.keys()):
                    self.bot.dbinst.exec_safe_query('insert into config values(%s, %s, %s, %s)', (self.bot.guilds[0].id, self.name, name, False))
                    for guild in self.bot.guilds:
                        data.append({'setting':name, 'category':self.name, 'guild_id':guild.id, 'enabled':False})
        print(data)
        if not isinstance(data, list):
            data = [data]
        for setting in data:
            states = collections.defaultdict(self.default_false)
            for guild in self.bot.guilds:
                if setting['guild_id'] == guild.id:
                    if setting['enabled'] is not None:
                        states[guild.id] = bool(setting['enabled'])
                    else:
                        states[guild.id] = False
            #create new setting, it automatically sets itself as an attr of this category
            Setting(self, setting['setting'], states)
        self.logger.info("Done filling settings cache.")
        self._ready = True
        self.filling = False

    def get_setting(self, name:str):
        """
        Gets a setting by name. The name must be an exact match.

        Parameters
        ----------

        name : str
            The name of the setting. Must exactly match the name provided in both 'settingdescmapping' and 'unusablewithmapping'.

        Returns
        -------

        Setting
            A Setting instance matching the specified name.

        None
            Setting not found.
        """
        return getattr(self, name, None)

    async def update_cached_state(self, ctx:commands.Context, setting:Setting):
        """
        Changes a setting's state in cache. Doesn't affect the database.
        """
        setting.states[ctx.guild.id] = not setting.states[ctx.guild.id]

    async def update_setting(self, ctx:commands.Context, setting:Setting):
        """
        Changes a setting's state in the database. Calls update_cached_state to change a setting's state in cache.
        """
        if not self.bot.dbinst.exec_safe_query("select * from config where guild_id=%s and category=%s", (ctx.guild.id, self.name)):
                self.bot.dbinst.exec_safe_query("insert into config values(%s, %s, %s, %s)", (ctx.guild.id, self.name, setting.name, True))
        else:
            self.bot.dbinst.exec_safe_query("update config set enabled=%s where guild_id=%s and setting=%s", (not setting.states[ctx.guild.id], ctx.guild.id, setting.name))
        await self.update_cached_state(ctx, setting)

    async def _prepare_conflict_string(self, conflicts):
        q = "'"
        if not isinstance(conflicts, list):
            return f"{q}*{conflicts}*{q}"
        return f"{', '.join([f'{q}*{i}*{q}' for i in conflicts[:-1]])} and '*{conflicts[-1]}*'"

    async def _resolve_conflicts(self, ctx, setting):
        #multiple conflicts, so iterate over them
        if isinstance(setting.unusablewith, list):
            resolved = []
            for conflict in setting.unusablewith:
                #unusablewith only has setting names, so get the Setting
                conflict = self.get_setting(conflict)
                if conflict.enabled():
                    await self.update_setting(ctx, conflict)
                    resolved.append(conflict)
        else:
            #only one conflict, update that setting
            if setting.unusablewith:
                if self.get_setting(setting.unusablewith).enabled():
                    await self.update_setting(ctx, self.unusablewithmapping[setting])
                    resolved = self.unusablewithmapping[setting]
            else:
                return ""
        if len(resolved) == 1:
            resolved = resolved[0]
        if not resolved:
            return ""
        return f"**Automatically disabled** {await self._prepare_conflict_string(resolved)} due to a conflict."

    async def config(self, ctx, name=None):
        '''Toggles the specified setting. Settings are off by default.'''
        if not name:
            if self.name != "global":
                title = f"Settings for category '{self.name}'"
            else:
                title = "Global settings"
            embed = discord.Embed(title=title, color=0xFDFE00)
            #writing this down so i can figure out something to do without having to restructure caches etc.
            #goals of this are to:
            #1. go through every setting
            #2. fetch setting states and conflicts
            for setting in [self.get_setting(i) for i in list(self.settingdescmapping.keys())]:
                if setting.unusablewith:
                    unusablewithwarning = f"Cannot be enabled at the same time as {await self.prepare_conflict_string(setting.unusablewith)}"
                else:
                    unusablewithwarning = ""
                embed.add_field(name=f"{discord.utils.remove_markdown(setting.description.capitalize())} ({setting.name})", value=f"{'❎ Disabled' if not setting.states[ctx.guild.id] else '✅ Enabled'}\n{unusablewithwarning} ", inline=True)
            embed.set_footer(text="If you want to toggle a setting, run this command again and specify the name of the setting. Setting names are shown above in parentheses. Settings only apply to your server.")
            return await ctx.send(embed=embed)
        setting = self.get_setting(name)
        try:
            #update setting state
            await self.update_setting(ctx, setting)
            #check for conflicts and resolve them
            unusablewithmessage = await self._resolve_conflicts(ctx, setting)
        except:
            await self.bot.get_user(self.bot.owner_id).send(traceback.format_exc())
            return await ctx.send(f"Something went wrong while changing that setting. Try again in a moment. \nI've reported this error to my owner. If this keeps happening, consider opening an issue at https://github.com/tk421bsod/maximilian/issues.")
        await ctx.send(embed=discord.Embed(title="Changes saved.", description=f"**{'Disabled' if not setting.enabled(ctx.guild.id) else 'Enabled'}** *{setting.description}*.\n{unusablewithmessage}", color=0xFDFE00).set_footer(text=f"Send this command again to turn this back {'off' if setting.enabled(ctx.guild.id) else 'on'}."))


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
        self.logger = logging.getLogger(name=f"maximilian.settings")
        self.logger.info(f"Settings module initialized.")
        self.unusablewithmessage = ""

    def add_category(self, category, settingdescmapping, unusablewithmapping):
        """
        A wrapper for creating a new Category instance. Its purpose is to allow a category to register as an attribute of the main settings instance.
        After this returns, you can check the value of settings using `bot.settings.<category>.<setting>.enabled()`.

        Parameters
        ----------

        category : str
            The name of the setting category. This will be used to view and toggle settings. 

        settingdescmapping : dict(str:str)
            A mapping of setting name to description.
            Descriptions show up when viewing and toggling settings.
            Example:
                {'a':'spam'}
                Setting 'a' has the description 'spam'.
                Toggling 'a' will show 'Enabled/Disabled 'spam'.'

        unusablewithmapping : dict(str:Union[list, str]=None)
            A mapping of setting name to names of settings that conflict.
            This allows the settings system to detect and resolve conflicts.
            This must be a dict with setting names as keys.
            There are three different types one can use for declaring conflicts (or lack thereof):

                None
                    No conflict.

                List
                    More than 1 conflict.

                Str
                    1 conflict.


            Example:
                {'a':['spam', 'eggs']}
                Setting 'a' conflicts with settings 'spam' and 'eggs'.

        """
        self.logger.info(f"Registering category '{category}`...")
        Category(self, category, settingdescmapping, unusablewithmapping)
        self.logger.info(f"Category '{category}' has been registered.")

    async def config(self, ctx, category:str, *, setting:str=None):
        """
        A command that changes settings. 
        """
        try:
            category = getattr(self, category) #
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
