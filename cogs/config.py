import discord
from discord.ext import commands
import pytz

class tz_setup_request():
    def __init__(self):
        self.waiting_for_reaction = False

    async def validate_tz(self, message):
        try:
            pytz.timezone(message.content.strip())
            return True
        except pytz.exceptions.UnknownTimeZoneError:
            return False

    async def confirm(self, ctx, message):
        await ctx.send(embed=discord.Embed(title="Confirm timezone change", description=f"You've said that your timezone is `{message.content.strip()}`. \n**Is this the correct timezone?* \nReact with \U00002705 to confirm and set your timezone, or react with <:red_x:813135049083191307> to cancel.").set_footer(text="Remember, you can always change this later using the tzsetup command."))

    async def handle_tz_change(self, bot, ctx):
        self.waiting_for_reaction = True
            try:
                while self.waiting_for_reaction:
                    message = await bot.wait_for('message', timeout=120.0)
                    if message.author == ctx.author:
                        if await self.validate_tz(message):
                            self.waiting_for_reaction = False
                            return await self.confirm(ctx, message)
                        await ctx.send("That's not a valid timezone!")
            except asyncio.TimeoutError:
                self.waiting_for_reaction = False
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
        if not (result := self.bot.exec_safe_query("select * from timezones where user_id=%s", (ctx.author.id,))):
            await self.timezone_setup(ctx)

def setup(bot):
    bot.add_cog(config(bot))

def teardown(bot):
    bot.remove_cog(config(bot))