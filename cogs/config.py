import discord
from discord.ext import commands
import pytz
import asyncio
import traceback

class tz_setup_request():
    def __init__(self):
        self.waiting = False

    async def validate_tz(self, message):
        try:
            if "GMT" in message.content or "UTC" in message.content:
                self.tz = f"Etc/{message.content.strip().replace('UTC', 'GMT')}"
                pytz.timezone(self.tz)
            else:
                self.tz = message.content.strip().replace(" ", "_")
                pytz.timezone(self.tz)
            return True
        except pytz.exceptions.UnknownTimeZoneError:
            traceback.print_exc()
            return False

    async def confirm(self, ctx, message):
        if (originaltimezone := self.bot.dbinst.exec_safe_query(self.bot.database, "select * from timezones where user_id=%s", (ctx.author.id,))):
            desc = f"Your timezone was set to `{originaltimezone['timezone']}`, and you're changing it to `{self.tz}`. \n**Do you want to change it?**\nReact with \U00002705 to confirm and change your timezone, or react with <:red_x:813135049083191307> to cancel."
        else:
            desc = f"You've said that your timezone is `{message.content.strip()}`. \n**Is this the correct timezone?** \nReact with \U00002705 to set your timezone, or react with <:red_x:813135049083191307> to cancel."
        confirmationmessage = await ctx.send(embed=discord.Embed(title="Confirm timezone change", description=f"{desc}").set_footer(text="You can always change this later using the tzsetup command."))
        await confirmationmessage.add_reaction("\U00002705")
        await confirmationmessage.add_reaction("<:red_x:813135049083191307>")
        await asyncio.sleep(0.5)
        self.waiting = True
        try:
            while self.waiting:
                reaction = await self.bot.wait_for('reaction_add', timeout=60.0)
                async for each in reaction[0].users():
                    if ctx.message.author == each:
                        if self.bot.dbinst.exec_safe_query(self.bot.database, "select * from timezones where user_id=%s", (ctx.author.id,)):
                            self.bot.dbinst.exec_safe_query(self.bot.database, "delete from timezones where user_id=%s", (ctx.author.id,))
                        self.waiting_for_reaction = False
                        self.bot.dbinst.exec_safe_query(self.bot.database, "insert into timezones values(%s, %s)", (ctx.author.id, self.tz))
                        self.bot.timezones[ctx.author.id] = self.tz
                        return await ctx.send(embed=discord.Embed(title=f"\U00002705 {'Changed' if originaltimezone else 'Set'} your timezone to `{self.tz}`!"))
        except asyncio.TimeoutError:
            await ctx.send("You took too long to react. Run `tzsetup` again if you want to set your timezone.")

    async def handle_tz_change(self, bot, ctx):
        self.waiting = True
        self.bot = bot
        try:
            while self.waiting:
                message = await bot.wait_for('message', timeout=120.0)
                if message.author == ctx.author:
                    if await self.validate_tz(message):
                        self.waiting = False
                        return await self.confirm(ctx, message)
                    await ctx.send("That's not a valid timezone!")
        except asyncio.TimeoutError:
            self.waiting = False
            await ctx.send("You took too long. Run `tzsetup` again if you want to set your timezone.")
            return

class settings(commands.Cog):
    '''Change Maximilian\'s settings (changes only apply to you or your server)'''
    def __init__(self, bot, load=False):
        self.bot = bot
        self.bot.timezones = {}
        self.bot.settings = {}
        if load:
            bot.loop.create_task(self.update_settings_cache())

    async def update_settings_cache(self):
        print("Updating settings cache...")
        await self.bot.wait_until_ready()
        data = self.bot.dbinst.exec_safe_query(self.bot.database, 'select * from config', (), fetchallrows=True)
        tempsettings = {}
        for setting in data:
            tempsettings[setting['setting']] = {}
        for setting in data:
            for guild in self.bot.guilds:
                if setting['guild_id'] == guild.id:
                    tempsettings[setting['setting']][guild.id] = setting['enabled'] 
        self.bot.settings = tempsettings
    
    async def timezone_setup(self, ctx):
        await ctx.send(embed=discord.Embed(title="Timezone Setup", description="To choose a timezone, enter the name or the GMT/UTC offset of your timezone."))
        await tz_setup_request().handle_tz_change(self.bot, ctx)

    @commands.command(help="Set or change your timezone.", aliases=["timezonesetup"], hidden=True)
    async def tzsetup(self, ctx):
        await self.timezone_setup(ctx)
    
    @commands.group(hidden=True)
    async def config(self, ctx):
        pass

    @config.command(hidden=True)
    async def deadchat(self, ctx):
        '''Toggles replies to "dead chat" on or off.'''
        if ctx.guild.id not in list(self.bot.settings['deadchat'].keys()):
            self.bot.dbinst.exec_safe_query(self.bot.database, "insert into config values(%s, %s, %s)", (ctx.guild.id, 'deadchat', False))
        else:
            self.bot.dbinst.exec_safe_query(self.bot.database, "update config set enabled=%s where guild_id=%s and setting=%s", (not self.bot.settings['deadchat'][ctx.guild.id], ctx.guild.id, 'deadchat'))
        await self.update_settings_cache()
        await ctx.send(embed=discord.Embed(title="Operation successful", description=f"Automatic replies to *dead chat* {'are now **enabled**' if self.bot.settings['deadchat'][ctx.guild.id] else 'are now **disabled**'}.").set_footer(text=f"Send this command again to turn them {'off' if self.bot.settings['deadchat'][ctx.guild.id] else 'on'}."))

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if self.bot.settings['deadchat'][message.guild.id] and "dead chat" in message.content.lower():
                await message.reply(content="https://media.discordapp.net/attachments/768537268452851754/874832974275809290/QRLi7Hv.png")
        except KeyError:
            pass

def setup(bot):
    bot.add_cog(settings(bot, True))

def teardown(bot):
    bot.remove_cog(settings(bot))