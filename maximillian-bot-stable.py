import discord
from discord.ext import commands 
from common import db
from common import token
import logging
import time
from zalgo_text import zalgo as zalgo_text_gen

logging.basicConfig(level=logging.WARN)
tokeninst = token()
dbinst = db()
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix="!", owner_id=538193752913608704, intents=intents, activity=discord.Game("with the API"))
decrypted_token = tokeninst.decrypt("token.txt")
bot.guildlist = []
bot.prefixes = {}
bot.responses = []

async def get_responses():
    print("getting responses...")
    if not bot.guildlist:    
        for guild in await bot.fetch_guilds().flatten():
            bot.guildlist.append(str(guild.id))
    for guild in bot.guildlist:
        count = dbinst.exec_query("maximilian", "select count(*) from responses where guild_id=" + str(guild), False, False)
        if count != None:
            response = dbinst.exec_query("maximilian", "select * from responses where guild_id=" + str(guild), False, False)
            if response != None:
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
    print("ready")
    
@bot.event
async def on_message(message):
    if message.author != bot.user:
        if message.content.startswith('<@!620022782016618528> '):
            bot.command_prefix = '<@!620022782016618528> '
        else:
            if message.guild != None:
                try:    
                    bot.command_prefix = bot.prefixes[str(message.guild.id)]
                except KeyError:
                    print("Couldn't get prefixes, using default prefix instead")
                    bot.command_prefix = "!"
                    pass
                print("command prefix is " + bot.command_prefix)
                for each in range(len(bot.responses)):
                    if int(bot.responses[each][0]) == int(message.guild.id):
                        if bot.responses[each][1] == message.content.replace(bot.command_prefix, ""):
                            await message.channel.send(bot.responses[each][2])
                            print("posted custom response")
                            return
        await bot.process_commands(message)

async def exectime(start_time, ctx):
    await ctx.send("took " + str(round(time.time()-start_time, 2)) + " seconds to execute")

@bot.command(help="Set Maximilian's prefix, only works if you're an admin")
async def prefix(ctx, arg):
    #should probably make this shorter and eliminate a bunch of those if statements
    if ctx.author.guild_permissions.administrator:
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
                await ctx.send(prefixsetmessage)
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
                deletionresult = dbinst.delete("maximilian", "prefixes", str(ctx.guild.id), "guild_id")
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

@bot.command(help="Test command.")
async def test(ctx):
    print("called test command")
    await ctx.send("Test")
    

@bot.command()
async def owner(ctx):
    await ctx.send("My owner is <@!" + str(bot.owner_id) + "> !")

@bot.command(help="zalgo text")
async def zalgo(ctx, *, arg):
    await ctx.send(zalgo_text_gen.zalgo().zalgofy(str(arg)))

@bot.command(help="Get information about a certain user, including status, roles, profile picture, and permissions")
async def userinfo(ctx):
    start_time = time.time()
    await ctx.trigger_typing()
    rolestring = ""
    permissionstring = ""
    if ctx.message.mentions != None and ctx.message.mentions != []:
    	requested_user = ctx.message.mentions[0]
    else:
        requested_user = ctx.message.author
    status = requested_user.status[0]
    statusnames = {"online" : "Online", "dnd" : "Do Not Disturb", "idle" : "Idle", "offline" : "Invisible/Offline"}
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
    embed.add_field(name="Status:", value=statusnames[status], inline=False)
    if requested_user.activity == None:
    	statusinfo = "No status details available"
    else:
        if requested_user.activity.type.name != None and requested_user.activity.type.name != "custom":
            activitytype = requested_user.activity.type.name.capitalize()
        else:
            activitytype = ""
        statusinfo = "Status details: '" + activitytype + " " + requested_user.activity.name + "'"
    if requested_user.id == bot.owner_id:
        embed.set_footer(text=statusinfo + "    |    Requested by " + ctx.author.name + "#" + ctx.author.discriminator + ".    |    This is my owner's info!")
    else:
        embed.set_footer(text=statusinfo + "    |    Requested by " + ctx.author.name + "#" + ctx.author.discriminator + ".")
    embed.set_thumbnail(url=requested_user.avatar_url)
    await ctx.send(embed=embed)
    await exectime(start_time, ctx)

@bot.command(help="Get a new list of custom responses after adding a new response")
async def fetch_responses(ctx):
    gettingresponsesmessage = await ctx.send("Getting a new list of responses...")
    await get_responses()
    await gettingresponsesmessage.edit(content="Got a new list of responses!")

@bot.command(help="List all prefixes")
async def listprefixes(ctx):
    prefixstring = ""
    for key in bot.prefixes.keys():
        print("iterating over keys")
        if key == str(ctx.message.guild.id):
            print("found prefix for this guild")
            prefixstring = prefixstring + "`" + bot.prefixes[key] + "`"
    await ctx.send("My prefixes in this server are " + prefixstring + " and <@!620022782016618528>")

@bot.event
async def on_guild_join(guild):
    print("joined guild, adding guild id to list of guilds")
    bot.guildlist.append(str(guild.id))
    await reset_prefixes()


print("starting bot")
bot.run(decrypted_token)