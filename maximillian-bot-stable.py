import discord
from discord.ext import commands 
from common import db
from common import token
import logging
import time
import aiohttp
import io
from zalgo_text import zalgo as zalgo_text_gen

logging.basicConfig(level=logging.WARN)
tokeninst = token()
dbinst = db()
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="myself start up!"))
decrypted_token = tokeninst.decrypt("token.txt")
bot.guildlist = []
bot.prefixes = {}
bot.responses = []

async def get_responses():
    print("getting responses...")
    bot.responses = []
    if not bot.guildlist:    
        for guild in await bot.fetch_guilds().flatten():
            bot.guildlist.append(str(guild.id))
    for guild in bot.guildlist:
        count = dbinst.exec_query("maximilian", "select count(*) from responses where guild_id={}".format(str(guild)), False, False)
        if count is not None:
            if int(count['count(*)']) >= 2:
                response = dbinst.exec_query("maximilian", "select * from responses where guild_id={}".format(str(guild)), False, True)
                if response is not None:
                    for each in range(int(count['count(*)'])):
                        bot.responses.append([str(response[each]['guild_id']), response[each]['response_trigger'], response[each]['response_text']])
            elif int(count['count(*)']) == 1:
                response = dbinst.exec_query("maximilian", "select * from responses where guild_id={}".format(str(guild)), True, False)
                if response is not None:
                    bot.responses.append([str(response['guild_id']), response['response_trigger'], response['response_text']])


async def reset_prefixes():
    print("resetting prefixes...")
    if not bot.guildlist:    
        for guild in await bot.fetch_guilds().flatten():
            bot.guildlist.append(str(guild.id))
    for each in bot.guildlist:
        prefixindb = dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(each), False)
        if prefixindb == "" or prefixindb == None:
            bot.prefixes[each] = '!'
        else:
            bot.prefixes[each] = prefixindb

@bot.event
async def on_ready():
    await reset_prefixes()
    await get_responses()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds!"))
    print("ready")
    
@bot.event
async def on_message(message):
    if message.author != bot.user:
        if message.content.startswith('<@!620022782016618528> '):
            bot.command_prefix = '<@!620022782016618528> '
        else:
            if message.guild is not None:
                try:    
                    bot.command_prefix = bot.prefixes[str(message.guild.id)]
                except KeyError:
                    print("Couldn't get prefixes, using default prefix instead")
                    bot.command_prefix = "!"
                    pass
                for each in range(len(bot.responses)):
                    if int(bot.responses[each][0]) == int(message.guild.id):
                        if bot.responses[each][1] == message.content.replace(bot.command_prefix, ""):
                            await message.channel.send(bot.responses[each][2])
                            return
        await bot.process_commands(message)

async def exectime(start_time, ctx):
    await ctx.send("took " + str(round(time.time()-start_time, 2)) + " seconds to execute")

@bot.command(help="Set Maximilian's prefix, only works if you're an admin", aliases=['prefixes'])
async def prefix(ctx, arg):
    #should probably make this shorter and eliminate a bunch of those if statements
    if ctx.author.guild_permissions.administrator or ctx.author.id == bot.owner_id:
        print("changing prefix...")
        changingprefixmessage = await ctx.send("Ok. Changing prefix...")
        start_time = time.time()
        await ctx.trigger_typing()
        prefixsetmessage = "My prefix in this server has been set to `" + str(arg) + "` ."
        duplicateprefixmessage = "My prefix in this server is already `" + str(arg) + "`."
        dbentry = dbinst.retrieve("maximilian", "prefixes", "prefix", "guild_id", str(ctx.guild.id), False)
        if dbentry == "" or dbentry == None:
            print("no db entry found")
            bot.prefixes[ctx.guild.id] = arg
            result = dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
            if result == "success":
                print("set prefix")
                await reset_prefixes()
                await changingprefixmessage.edit(content=prefixsetmessage)
                await exectime(start_time, ctx)
                return "changed prefix"
            else:
                print("error")
                await ctx.send("An error occured while setting the prefix. Please try again later.")
                await exectime(start_time, ctx)
                print(result)
                return "error"
        elif dbentry == arg:
            print("tried to change to same prefix")
            await ctx.send(duplicateprefixmessage)
            await exectime(start_time, ctx)
            return "changed prefix"
        elif dbentry != "" and dbentry != arg:
            print("db entry found")
            result = dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
            if result == "success":
                print("set prefix")
                await reset_prefixes()
                await changingprefixmessage.edit(content=prefixsetmessage)
                await exectime(start_time, ctx)
                return "changed prefix"
            elif result == "error-duplicate":
                print("there's already an entry for this guild")
                deletionresult = dbinst.delete("maximilian", "prefixes", str(ctx.guild.id), "guild_id", "", "", False)
                if deletionresult == "successful":
                    result = dbinst.insert("maximilian", "prefixes", {"guild_id":str(ctx.guild.id), "prefix":str(arg)}, "guild_id", False, "", False)
                    if result == "success":
                        print("set prefix")
                        await reset_prefixes()
                        await changingprefixmessage.edit(content=prefixsetmessage)
                        await exectime(start_time, ctx)
                    else: 
                        print("error")
                        await changingprefixmessage.edit(content="An error occurred when setting the prefix. Please try again later.")
                        print(result)
                        await exectime(start_time, ctx)
                        return "error"
                else:
                    print("error")
                    await changingprefixmessage.edit(content="An error occurred when setting the prefix. Please try again later.")
                    print(deletionresult)
                    await exectime(start_time, ctx)
                    return "error"
            else:
                await changingprefixmessage.edit(content="An error occurred when setting the prefix. Please try again later.")
                print(result)
                await exectime(start_time, ctx)
                return "error"
    else:
        await ctx.send("You don't have the permissions required to run this command.")

@bot.event
async def on_command_error(ctx, error):
    await ctx.send("There was an error. Please try again later.")
    await ctx.send("`"+str(error)+"`")

@bot.command(aliases=["owner"])
async def hi(ctx):
    await ctx.send("Hello! I'm a robot. tk421#7244 made me!")

@bot.command(help="zalgo text")
async def zalgo(ctx, *, arg):
    await ctx.send(zalgo_text_gen.zalgo().zalgofy(str(arg)))

@bot.command(help="Get information about a certain user, including status, roles, profile picture, and permissions", aliases=['getuserinfo'])
async def userinfo(ctx):
    start_time = time.time()
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
    embed = discord.Embed(title="User info for " + str(requested_user.name) + "#" + str(requested_user.discriminator), color=rolecolor)
    embed.add_field(name="Date joined:", value=requested_user.joined_at, inline=False)
    embed.add_field(name="Date created:", value=requested_user.created_at, inline=False)
    for each in requested_user.roles:
        if each.name != "@everyone":
            rolestring = rolestring + "<@&" + str(each.id) + ">, "
        else:
            rolestring = rolestring + each.name + ", "
    for each in requested_user.guild_permissions:
        if each[1] == True:
            permissionstring = permissionstring + each[0].replace("_", " ").capitalize() + ", "
    rolestring = rolestring[:-2]
    permissionstring = permissionstring[:-2]
    embed.add_field(name="Roles:", value=rolestring, inline=False)
    embed.add_field(name="Permissions:", value=permissionstring, inline=False)
    embed.add_field(name="Status:", value=statusemojis[status] + " " + statusnames[status], inline=False)
    if requested_user.activity == None:
    	statusinfo = "No status details available"
    else:
        if requested_user.activity.type.name is not None and requested_user.activity.type.name != "custom":
            activitytype = requested_user.activity.type.name.capitalize()
        else:
            activitytype = ""
        statusinfo = "Status details: '" + activitytype + " " + requested_user.activity.name + "'"
    executiontime = "took " + str(round(time.time()-start_time, 2)) + " seconds to execute"
    if requested_user.id == bot.owner_id:
        embed.set_footer(text=statusinfo + "  |  Requested by " + ctx.author.name + "#" + ctx.author.discriminator + ".  |  This is my owner's info!  |  " + executiontime)
    else:
        embed.set_footer(text=statusinfo + "  |  Requested by " + ctx.author.name + "#" + ctx.author.discriminator + ".  |  " + executiontime)
    embed.set_thumbnail(url=requested_user.avatar_url)
    await ctx.send(embed=embed)

@bot.command(help="Get a new list of custom responses after adding a new response", aliases=['fetchresponses', 'getresponses'])
async def fetch_responses(ctx):
    gettingresponsesmessage = await ctx.send("Getting a new list of responses...")
    await get_responses()
    await gettingresponsesmessage.edit(content="Got a new list of responses!")

@bot.command(help="List all prefixes")
async def listprefixes(ctx):
    prefixstring = ""
    for key in bot.prefixes.keys():
        if key == str(ctx.message.guild.id):
            prefixstring = prefixstring + "`" + bot.prefixes[key] + "`"
    await ctx.send("My prefixes in this server are " + prefixstring + " and <@!620022782016618528>")

@bot.event
async def on_raw_reaction_add(payload):
    if dbinst.retrieve("maximilian", "roles", "guild_id", "guild_id", str(payload.guild_id), False) is not None:
        roleid = dbinst.retrieve("maximilian", "roles", "role_id", "message_id", str(payload.message_id), False)
        if roleid is not None:
            role = discord.utils.get(payload.member.guild.roles, id=int(roleid))
            await payload.member.add_roles(role)
            ctx = bot.get_channel(payload.channel_id)
            await ctx.send("Assigned <@!" + str(payload.member.id) + "> the '" + role.name + "' role!", delete_after=5)

@bot.event
async def on_raw_reaction_remove(payload):
    if dbinst.retrieve("maximilian", "roles", "guild_id", "guild_id", str(payload.guild_id), False) is not None:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        roleid = dbinst.retrieve("maximilian", "roles", "role_id", "message_id", str(payload.message_id), False)
        if roleid is not None:
            role = discord.utils.get(guild.roles, id=int(roleid))
            await member.remove_roles(role)
            ctx = bot.get_channel(payload.channel_id)
            await ctx.send("Removed the '" + role.name + "' role from <@!" + str(member.id) + ">!", delete_after=5)

@bot.command(aliases=['pong'])
async def ping(ctx):
    await ctx.send("Pong! My latency is " + str(round(bot.latency*1000, 1)) + "ms.")

@bot.event
async def on_guild_join(guild):
    print("joined guild, adding guild id to list of guilds")
    bot.guildlist.append(str(guild.id))
    await reset_prefixes()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=str(len(bot.guilds))+" guilds!"))

@bot.command(help="Add, remove, or list reaction roles, only works if you have administrator privileges", aliases=['reactionroles'])
async def reactionrole(ctx, action, roleid, messageid):
    if ctx.author.guild_permissions.administrator or ctx.author.id == bot.owner_id:
        if action == "add":
            if dbinst.insert("maximilian", "roles", {"guild_id" : str(ctx.guild.id), "role_id" : str(roleid), "message_id" : str(messageid)}, "role_id", False, "", False) == "success":
                await ctx.send("Added a reaction role.")
            else: 
                raise discord.ext.commands.CommandError(message="Failed to add a reaction role, there might be a duplicate. Try deleting the role you just tried to add.")
        if action == "delete":
            if dbinst.delete("maximilian", "roles", str(roleid), "role_id", "", "", False) == "successful":
                await ctx.send("Deleted a reaction role.")
            else:
                raise discord.ext.commands.CommandError(message="Failed to delete a reaction role, are there any reaction roles set up for role id '" + str(roleid) + "'? Try using '"+ str(bot.command_prefix) +"reactionrole list all all' to see if you have any reaction roles set up.")
        if action == "list":
            roles = dbinst.exec_query("maximilian", "select * from roles where guild_id={}".format(ctx.guild.id), False, True)
            reactionrolestring = ""
            if roles != "()":
                for each in roles: 
                    reactionrolestring = reactionrolestring + " message id: " + str(each["message_id"]) + " role id: " + str(each["role_id"]) + ", "         
                await ctx.send("reaction roles: " + str(reactionrolestring[:-2]))
    else:
        await ctx.send("You don't have permission to use this command.")

@bot.command(help="Add, delete, or list custom responses. You must have 'Manage Server' permissions to do this. Don't include Maximilian's prefix in the response trigger.", aliases=['response'])
async def responses(ctx, action, response_trigger, *, response_text):
    if ctx.author.guild_permissions.manage_guild or ctx.author.id == bot.owner_id:
        await ctx.trigger_typing()
        if action.lower() == "add":
            response_text.replace("*", "\*")
            response_trigger.replace("*", "\*")
            if dbinst.insert("maximilian", "responses", {"guild_id" : str(ctx.guild.id), "response_trigger" : str(response_trigger), "response_text" : str(response_text)}, "response_trigger", False, "", False) == "success":
                await get_responses()
                await ctx.send("Added a custom response. Try it out!")
            else: 
                raise discord.ext.commands.CommandError(message="Failed to add a response, there might be a duplicate. Try deleting the response you just tried to add.")
        if action.lower() == "delete":
            if dbinst.delete("maximilian", "responses", str(response_trigger), "response_trigger", "guild_id", str(ctx.guild.id), True) == "successful":
                await get_responses()
                await ctx.send("Deleted a custom response.")
            else:
                raise discord.ext.commands.CommandError(message="Failed to delete a custom response, are there any custom responses set up that use the response trigger '" + str(response_trigger) + "'?")
        if action.lower() == "list":
            responsestring = ""
            await get_responses()
            for each in range(len(bot.responses)):
                if int(bot.responses[each][0]) == int(ctx.guild.id):
                    if len(bot.responses[each][2]) >= 200:
                        responsetext = bot.responses[each][2][:200] + "..."
                    else:
                        responsetext = bot.responses[each][2]
                    responsestring = responsestring + " \n response trigger: `" + bot.responses[each][1] + "` response text: `" + responsetext + "`"
            if responsestring == "":
                responsestring = "I can't find any custom responses in this server."
            await ctx.send(responsestring)
    else:
        await ctx.send("You don't have permission to use this command.")

@commands.is_owner()
@bot.command(hidden=True)
async def listguildnames(ctx):
    guildstring = ""
    for each in bot.guilds:
        guildstring = guildstring + each.name + ", "
    await ctx.send(guildstring[:-2])

@bot.command(help="Get an image of a cat. The image is generated by AI, therefore it's an image of a cat that doesn't exist", aliases=["cats"])
async def thiscatdoesntexist(ctx):
    await ctx.trigger_typing()
    async with aiohttp.ClientSession() as cs:
        async with cs.get('https://thiscatdoesnotexist.com') as r:
            buffer = io.BytesIO(await r.read())
            await ctx.send(file=discord.File(buffer, filename="cat.jpeg"))

@bot.command(help="Get a bunch of info about the bot")
async def about(ctx):
    embed = discord.Embed(title="About", color=discord.Color.blurple())
    embed.add_field(name="Useful links", value="Use `" + str(bot.command_prefix) + "help command` for more info on a certain command. \n For more help, join the support server at https://discord.gg/PJ94gft. \n To add Maximilian to your server, with only the required permissions, click [here](https://discord.com/api/oauth2/authorize?client_id=620022782016618528&permissions=268815456&scope=bot).", inline=False)
    embed.add_field(name="Fun Commands", value="Commands that have no purpose. \n `zalgo` `cats` `ping`", inline=True)
    embed.add_field(name="Other Commands", value="Commands that actually have a purpose. \n `about` `help` `userinfo` `reactionroles` `responses` `prefix` `listprefixes` `hi`", inline=True)
    await ctx.send(embed=embed)

print("starting bot")
bot.run(decrypted_token)