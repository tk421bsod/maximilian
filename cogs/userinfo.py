import typing

import discord
from discord.ext import commands


class userinfo(commands.Cog):
    '''Get information about a certain user.'''
    def __init__(self, bot):
        self.bot = bot

    #might need a refactor
    @commands.command(help="Get information about a certain user, including status, roles, profile picture, and permissions", aliases=['getuserinfo'])
    async def userinfo(self, ctx, *, requested_user=None):
        if requested_user is None:
            requested_user = ctx.author
        else:
            try:
                requested_user = await commands.MemberConverter().convert(ctx, requested_user)
            except:
                await ctx.send("I couldn't find that user, so I'll show your information instead. Make sure that the user is in this server and you didn't make any typos.")
                requested_user = ctx.author
        rolestring = ""
        permissionstring = ""
        status = requested_user.status[0]
        if len(requested_user.roles) == 1:
            rolecolor = discord.Color.blurple()
        else:
            rolecolor = requested_user.top_role.color
        embed = discord.Embed(title=f"User info for {str(requested_user)}", color=rolecolor)
        try:
            embed.add_field(name="Date joined:", value=requested_user.joined_at.strftime("%B %d, %Y at %-I:%M %p UTC"), inline=False)
            embed.add_field(name="Date created:", value=requested_user.created_at.strftime("%B %d, %Y at %-I:%M %p UTC"), inline=False)
        except:
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
        embed.set_footer(text=f"Requested by {str(ctx.author)}.")
        embed.set_thumbnail(url=requested_user.avatar.url)
        await ctx.send(embed=embed)
    

async def setup(bot):
    await bot.add_cog(userinfo(bot))

async def teardown(bot):
    await bot.remove_cog(userinfo(bot))

