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
            desc = f"You've said that your timezone is `{message.content.strip()}`. \n**Is this the correct timezone?** \nReact with \U00002705 to confirm and set your timezone, or react with <:red_x:813135049083191307> to cancel."
        confirmationmessage = await ctx.send(embed=discord.Embed(title="Confirm timezone change", description=f"{desc}").set_footer(text="Remember, you can always change this later using the tzsetup command."))
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

class config(commands.Cog):
    '''Change Maximilian\'s settings (changes only apply to you or your server)'''
    def __init__(self, bot):
        self.bot = bot
        self.bot.timezones = {}
    
    async def timezone_setup(self, ctx):
        await ctx.send(embed=discord.Embed(title="Timezone Setup", description="To choose a timezone, enter the name or the GMT/UTC offset of your timezone."))
        await tz_setup_request().handle_tz_change(self.bot, ctx)

    @commands.command(help="Set or change your timezone.", aliases=["timezonesetup"])
    async def tzsetup(self, ctx):
        await self.timezone_setup(ctx)

def setup(bot):
    bot.add_cog(config(bot))

def teardown(bot):
    bot.remove_cog(config(bot))