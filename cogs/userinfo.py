import discord
from discord.ext import commands
import typing

class userinfo(commands.Cog):
    '''Get information about a certain user.'''
    def __init__(self, bot):
        self.bot = bot
        self.bot.requested_user = None

    #might need a refactor
    @commands.command(help="Get information about a certain user, including status, roles, profile picture, and permissions", aliases=['getuserinfo'])
    async def userinfo(self, ctx, requested_user : typing.Optional[discord.Member]=None):
        if requested_user is None:
            requested_user = self.bot.requested_user
        await ctx.trigger_typing()
        rolestring = ""
        permissionstring = ""
        status = requested_user.status[0]
        statusnames = {"online" : "Online", "dnd" : "Do Not Disturb", "idle" : "Idle", "offline" : "Invisible/Offline"}
        statusemojis = {"online" : "<:online:767294866488295475>", "dnd": "<:dnd:767510004135493662>", "idle" : "<:idle:767510329139396610>", "offline" : "<:invisible:767510747466170378>"}
        if len(requested_user.roles) == 1:
            rolecolor = discord.Color.blurple()
        else:
            rolecolor = requested_user.top_role.color
        embed = discord.Embed(title=f"User info for {str(requested_user)}", color=rolecolor)
        try:
            embed.add_field(name="Date joined:", value=requested_user.joined_at.strftime("%B %d, %Y at %-I:%M %p UTC"), inline=False)
            embed.add_field(name="Date created:", value=requested_user.created_at.strftime("%B %d, %Y at %-I:%M %p UTC"), inline=False)
        except Exception:
            self.bot.logger.warning("Timestamp formatting failed. (Is Maximilian running on Windows?) ")
            embed.add_field(name="Date joined:", value=requested_user.joined_at.strftime("%B %d, %Y at %I:%M %p UTC"), inline=False)
            embed.add_field(name="Date created:", value=requested_user.created_at.strftime("%B %d, %Y at %I:%M %p UTC"), inline=False)
        #should probably use .join instead of this
        for each in requested_user.roles:
            if each.name != "@everyone":
                rolestring = rolestring + "<@&" + str(each.id) + ">, "
            else:
                rolestring = rolestring + each.name + ", "
        for each in requested_user.guild_permissions:
            if each[1] == True:
                permissionstring = f"{permissionstring}{each[0].replace('_', ' ').replace('guild', 'server').capitalize()}, "
        rolestring = rolestring[:-2]
        permissionstring = permissionstring[:-2]
        if "Administrator" in permissionstring:
            permissionstring = "Administrator"
        embed.add_field(name="Roles:", value=rolestring, inline=False)
        embed.add_field(name="Permissions:", value=permissionstring, inline=False)
        embed.add_field(name="Status:", value=f"{statusemojis[status]} {statusnames[status]}", inline=False)
        if requested_user.activity == None:
            statusinfo = "No status details available"
        else:
            if requested_user.activity.type.name is not None and requested_user.activity.type.name != "custom":
                activitytype = requested_user.activity.type.name.capitalize()
            else:
                activitytype = ""
            statusinfo = f"Status details: '{activitytype} {requested_user.activity.name}'"
        if requested_user.id == self.bot.owner_id:
            embed.set_footer(text=f"{statusinfo}  |  Requested by {str(ctx.author)}  |  This is my owner's info!")
        else:
            embed.set_footer(text=f"{statusinfo}  |  Requested by {str(ctx.author)}")
        embed.set_thumbnail(url=requested_user.avatar_url)
        print("printed userinfo")
        await ctx.send(embed=embed)
    
    @userinfo.before_invoke
    async def before_userinfo(self, ctx):
        #a bit 'hacky', but I'm not sure how else I would implement this
        self.bot.requested_user = ctx.author

def setup(bot):
    bot.add_cog(userinfo(bot))

def teardown(bot):
    bot.remove_cog(userinfo(bot))

    
