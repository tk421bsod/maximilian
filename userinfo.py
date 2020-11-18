import discord
from discord.ext import commands
import time
from pytz import timezone

class userinfo(commands.Cog):
    '''Self explanatory. See userinfo\'s help entry for details'''
    def __init__(self, bot):
        self.bot = bot  
    
    @commands.command(help="Get information about a certain user, including status, roles, profile picture, and permissions", aliases=['getuserinfo'])
    async def userinfo(self, ctx):
        await ctx.trigger_typing()
        rolestring = ""
        permissionstring = ""
        if ctx.message.mentions is not None and ctx.message.mentions != []:
            requested_user = ctx.message.mentions[0]
        else:
            requested_user = ctx.message.author
        status = requested_user.status[0]
        statusnames = {"online" : "Online", "dnd" : "Do Not Disturb", "idle" : "Idle", "offline" : "Invisible/Offline"}
        statusemojis = {"online" : "<:online:767294866488295475>", "dnd": "<:dnd:767510004135493662>", "idle" : "<:idle:767510329139396610>", "offline" : "<:invisible:767510747466170378>"}
        if len(requested_user.roles) == 1:
            rolecolor = discord.Color.blurple()
        else:
            rolecolor = requested_user.roles[len(requested_user.roles)-1].color
        embed = discord.Embed(title=f"User info for {str(requested_user.name)}#{str(requested_user.discriminator)}", color=rolecolor)
        embed.add_field(name="Date joined:", value=requested_user.joined_at.astimezone(timezone('US/Pacific')).strftime("%B %d, %Y at %-I:%M %p PST"), inline=False)
        embed.add_field(name="Date created:", value=requested_user.created_at.astimezone(timezone('US/Pacific')).strftime("%B %d, %Y at %-I:%M %p PST"), inline=False)
        for each in requested_user.roles:
            if each.name != "@everyone":
                rolestring = rolestring + "<@&" + str(each.id) + ">, "
            else:
                rolestring = rolestring + each.name + ", "
        for each in requested_user.guild_permissions:
            if each[1] == True:
                permissionstring = f"{permissionstring}{each[0].replace('_', ' ').capitalize()}, "
        rolestring = rolestring[:-2]
        permissionstring = permissionstring[:-2]
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
            embed.set_footer(text=f"{statusinfo}  |  Requested by {ctx.author.name}#{ctx.author.discriminator}  |  This is my owner's info!")
        else:
            embed.set_footer(text=f"{statusinfo}  |  Requested by {ctx.author.name}#{ctx.author.discriminator} ")
        embed.set_thumbnail(url=requested_user.avatar_url)
        print("printed userinfo")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(userinfo(bot))

def teardown(bot):
    bot.remove_cog(userinfo(bot))

    
