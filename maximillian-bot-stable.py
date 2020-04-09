import discord
from discord.ext import commands 
from discord import Embed
from discord import Reaction
import requests
import json
import time
import random
import os
import psutil
import re
import pymysql
import datetime
from cryptography.fernet import Fernet
from common import db
from common import token
reecounter = 0
jmmcounter = 0
mentioncounter = 0
#bannedwordstxt = open("bannedwords.txt", "r")
#bannedwordslist = bannedwordstxt.split(",")
global log
log = open("maximillian-bot-log.txt", "a")
# create discord client
client = discord.Client()
bot = discord.Client()
'''
commented out in case I want to use this later
## start ip commad
def ip_command(message, client, args):
    try:
        req = requests.get('http://ip-api.com/json/{}'.format(args[0]))
        resp = json.loads(req.content.decode())
        if req.status_code == 200:
            if resp['status'] == 'success':
                template = '**{}**\n**IP: **{}\n**City: **{}\n**State: **{}\n**Country: **{}\n**Latitude: **{}\n**Longitude: **{}\n**ISP: **{}'
                out = template.format(args[0], resp['query'], resp['city'], resp['regionName'], resp['country'], resp['lat'], resp['lon'], resp['isp'])
                return out
            elif resp['status'] == 'fail':
                return 'API Request Failed'
        else:
            return 'HTTP Request Failed: Error {}'.format(req.status_code)
    except Exception as e:
        print(e)
ch.add_command({
    'trigger': '!ip',
    'function': ip_command,
    'args_num': 1,
    'args_name': ['IP\Domain'],
    'description': 'Prints information about provided IP/Domain!'
})
## end ip command
'''
async def im_command(message):
    try:
        dbfile=pymysql.connect(host='10.0.0.193',
                        user='tk421bsod',
                        password=decrypted_databasepassword.decode(),
                        db='maximilian',
                        charset='utf8mb4',
                        cursorclass=pymysql.cursors.DictCursor)
        db=dbfile.cursor()
        db.execute("select * from dadjokesdisabled where guild_id=%s", (message.guild.id))
        row = db.fetchone()
        if row == None:
            if message.author.id == int(503720029456695306):
                print("ignoring message by Dadbot")
            elif message.author.id == int(675530484742094893):
                print("ignoring message by DocBot")
            else:
                print (message.author.id)
                im = content.split('I\'m')
                imvalue = str(im[1])
                if imvalue == "Maximilian":
                    await message.channel.send("You're not Maximilian, I'm Maximilian!")
                elif imvalue == "maximilian":
                    await message.channel.send("You're not Maximilian, I'm Maximilian!")
                elif imvalue == "<@!620022782016618528>":
                    await message.channel.send("You're not <@!620022782016618528>, I'm <@!620022782016618528>!")
                else:
                    immaxmilian = 'Hi ' + imvalue + ", I'm Maximilian!"
                    await message.channel.send(immaxmilian)
        else:
            pass
    except Exception as e:
        if message.guild.id == 678789014869901342:
            await message.channel.send(str(e))
        print(e)
# when bot is ready
@client.event
async def on_ready():
    try:
        print(client.user.name)
        print(client.user.id)
        print("log opened")
        log.write("I just logged in! \n")
        log.flush()
    except Exception as e:
        print(e)

# on new message
@client.event
async def on_message(message):
    ree = "This server is a ree free zone. "
    jmm = "This server is a jmm free zone. "
    embed = discord.Embed()
    process = psutil.Process(os.getpid())
    embed.set_image(url="")
    global jmmcounter
    global reecounter 
    global mentioncounter
    global timestamp
    global bannedwordslist
    global bannedwordstxt
    content = message.content
    data = ""
    system = ""
    systemlist = ""
    securitylevel = ""
    args = []
    populatedsystems = []
    unpopulatedsystems = []
    print(content)
      # if the message is from the bot itself ignore it
    print("Memory usage in bytes: " + str(process.memory_info().rss)) 
    if message.author == client.user:
        pass
    else:  
        try:
            dbfile=pymysql.connect(host='10.0.0.193',
                             user='tk421bsod',
                             password=decrypted_databasepassword.decode(),
                             db='maximilian',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
            db=dbfile.cursor()
            db.execute("select * from responses where guild_id=%s and response_trigger like %s", (message.guild.id, message.content))
            row = db.fetchone()
            if row is None:
                pass
            else:
                log.write("Sent a custom response at " + str(datetime.datetime.now()))
                log.flush()
                await message.channel.send(row['response_text'])
            db.execute("select * from prefixes where guild_id=%s", (message.guild.id, ))
            prefixrow = db.fetchone()
            if prefixrow != None:
                prefix = str(prefixrow["prefix"])
            elif prefixrow == None:
                prefix = "!"
            db.close()
        except Exception as e:
            print(e)
        if "!systems" in content:
            try:
                #print("File opened")
                #args = content.split(" ")
                #print (str(args))
                #if args[1] != "":
                 #   if args[1] == "security":
                  #      if args[2] != "":
                   #         data = open("C:/Users/colin/bots/systems.csv")
                    #        print("File opened")
                     #       securitylevel = args[2]
                      #      print(securitylevel)
                       #     for line in data: 
                        #        system = line.split(',')
                         #       print(system[13])
                          #      if str(system[13]) == str(securitylevel):
                           #         print ("found a match")
                            #        systemlist.write("Id: " + system[0] + " EDSM Id: " + system[1] + " Name: " + system[2] + " X: " + system[3] + " Y: " + system[4] + " Z: " + system[5] + " Population: " + system[6] + " Government: " + system[9] + " Security: " + system[13])
                             #       await message.channel.send("Id: " + system[0] + " EDSM Id: " + system[1] + " Name: " + system[2] + " X: " + system[3] + " Y: " + system[4] + " Z: " + system[5] + " Population: " + system[6] + " Government: " + system[9] + " Security: " + system[13])
                 #   else:
                    
                systemlist = open("C:/Users/colin/bots/systemlist.txt", "w")
                data = open("C:/Users/colin/bots/systems.csv")
                populatedsystems = []
                systemlist.write("")
                unpopulatedsystems = []
                for line in data:
                    system = line.split(',')
                    if system[7] == "1":
                        try:
                            print(system)
                            populatedsystems.write(system[0])
                            print("This system is populated")
                            systemlist.write("Id: " + system[0] + " EDSM Id: " + system[1] + " Name: " + system[2] + " X: " + system[3] + " Y: " + system[4] + " Z: " + system[5] + " Population: " + system[6] + " Government: " + system[9] + " Security: " + system[13])
                        except Exception as e:
                            print(e)       
                    else:
                        try:
                            unpopulatedsystems.write(system[0])
                            systemlist.write("Id: " + system[0] + " EDSM Id: " + system[1] + " Name: " + system[2] + " X: " + system[3] + " Y: " + system[4] + " Z: " + system[5] + " Population: " + system[6] + " Government: " + system[9] + " Security: " + system[13])
                                            # in bytes      
                        except Exception as e:
                            print(e)
            except Exception as e:
                if message.guild.id == 678789014869901342:
                    await message.channel.send(str(e))
                print(e)
        if str(prefix) + "prefix" in content:
            await message.channel.send("Maximilian is down for maintenance. \n To keep track of changes, join the Bot Test Zone (support server coming soon) at https://discord.gg/yHEJS2p. \n DM TK421bsod#7244 if you want an invite to the repository, to keep track of changes and help with development. \n *Don't be sad it's down, be excited for Maximilian v3!*")
            '''prefixargument = content.split(" ")[1]
            dbfile=pymysql.connect(host='10.0.0.193',
                             user='tk421bsod',
                             password=decrypted_databasepassword.decode(),
                             db='maximilian',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
            db=dbfile.cursor()
            db.execute("select * from prefixes where guild_id=%s and prefix=%s", (message.guild.id, prefixargument))
            row = db.fetchone()
            if row == None:
                await message.channel.send("Setting my prefix in this server to `" + str(prefixargument) + "`...")
                log.write("Setting my prefix in " + message.guild.name + " to" + str(prefixargument))
                db.execute("delete from prefixes where guild_id=%s", (message.guild.id, ))
                dbfile.commit()
                db.execute("insert into prefixes(guild_id, prefix) values (%s, %s)", (message.guild.id, prefixargument))
                dbfile.commit()
                dbfile.close()
                log.write("My prefix has been set to " + str(prefixargument) + " in " + message.guild.name + ".")
                await message.channel.send("My prefix has been set to `" + str(prefixargument) + "` in this server. Use `" + str(prefixargument) + "` before any commands.")
            elif row != None:
                await message.channel.send("My prefix is already set to `" + str(prefixargument) + "` in this server.")
                '''
        if str(prefix) + "help" in content:
            await message.channel.send("Maximilian is down for maintenance. \n To keep track of changes, join the Bot Test Zone (support server coming soon) at https://discord.gg/yHEJS2p. \n DM TK421bsod#7244 if you want an invite to the repository, to keep track of changes and help with development. \n *Don't be sad it's down, be excited for Maximilian v3!*")
            # await message.channel.send("Help: \n If you want to create a custom response, go to http://animationdoctorstudio.net/other-projects/maximilian/responses and fill out the form. \n Dad jokes: Dad jokes are enabled by default. To disable them, type `!disable dadjokes`. To enable them, type `!enable dadjokes`. \n ")

        if str(prefix) + "cats" in content:
            await message.channel.send("Maximilian is down for maintenance. \n To keep track of changes, join the Bot Test Zone (support server coming soon) at https://discord.gg/yHEJS2p. \n DM TK421bsod#7244 if you want an invite to the repository, to keep track of changes and help with development. \n *Don't be sad it's down, be excited for Maximilian v3!*")
            '''try:
                embed.clear_fields()
                embed = discord.Embed()
                embed.set_image(url="https://cataas.com/cat")
                await message.channel.send(embed=embed)

                log.write("I posted a cat photo! \n")
            except Exception as e:
                if message.guild.id == 678789014869901342:
                    await message.channel.send(str(e))
                print(e)

        if content.startswith(str(prefix) + "disable dadjokes"):
            try:
                dbfile=pymysql.connect(host='10.0.0.193',
                             user='tk421bsod',
                             password=decrypted_databasepassword.decode(),
                             db='maximilian',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
                db=dbfile.cursor()
                print("Checking for duplicate entries...")
                db.execute("select * from dadjokesdisabled where guild_id=%s;", (message.guild.id))
                row = db.fetchone()
                print (row)
                if row == None:
                    db.execute("insert into dadjokesdisabled(guild_id) values (%s);", (message.guild.id))
                    dbfile.commit()
                    await message.channel.send("Dad jokes have been disabled in this server.")
                    db.close()
                else:
                    await message.channel.send("Dad jokes are already disabled in this server.")
                    db.close()
            except Exception as e:
                if message.guild.id == 678789014869901342:
                    await message.channel.send(str(e))
                print(e)
                '''
        if content.startswith(str(prefix) + "enable dadjokes"):
            await message.channel.send("Maximilian is down for maintenance. \n To keep track of changes, join the Bot Test Zone (support server coming soon) at https://discord.gg/yHEJS2p. \n DM TK421bsod#7244 if you want an invite to the repository, to keep track of changes and help with development. \n *Don't be sad it's down, be excited for Maximilian v3!*")
            '''try:
                dbfile=pymysql.connect(host='10.0.0.193',
                             user='tk421bsod',
                             password=decrypted_databasepassword.decode(),
                             db='maximilian',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
                db=dbfile.cursor()
                db.execute("select * from dadjokesdisabled where guild_id=%s", (message.guild.id))
                row = db.fetchone()
                if row != None:
                    db.execute("delete from dadjokesdisabled where guild_id=%s;", (message.guild.id))
                    dbfile.commit()
                    log.write("Dad jokes have been disabled in " + str(message.guild.name))
                    log.flush()
                    await message.channel.send("Dad jokes have been enabled in this server.")
                    db.close()
                else:
                    await message.channel.send("Dad jokes are already enabled in this server.")
                    db.close()
            except Exception as e:
                if message.guild.id == 678789014869901342:
                    await message.channel.send(str(e))
                print(e)
'''
        if str(prefix) + "cv" in content:
            await message.channel.send("Maximilian is down for maintenance. \n To keep track of changes, join the Bot Test Zone (support server coming soon) at https://discord.gg/yHEJS2p. \n DM TK421bsod#7244 if you want an invite to the repository, to keep track of changes and help with development. \n *Don't be sad it's down, be excited for Maximilian v3!*")
            '''
            arguments = content.split(" ")
            dbfile=pymysql.connect(host='10.0.0.193',
                            user='tk421bsod',
                            password=decrypted_databasepassword.decode(),
                            db='covid19data',
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
            db=dbfile.cursor()
            if arguments[1] == "total":
                await message.channel.send("Processing, this may take a bit.")
                db.execute('select * from covid19data order by date desc limit 1')
                row = db.fetchone()
                date = str(row['date'])
                db.execute("select cases from covid19data where date = %s;", (date, ))
                row = db.fetchone()
                casenum = 0
                deathnum = 0
                while row != None:
                    casenum = casenum + int(row['cases'])
                    row = db.fetchone()
                db.execute('select deaths from covid19data where date = %s;', (date, ))
                row = db.fetchone()
                while row != None:
                    deathnum = deathnum + int(row['deaths'])
                    row = db.fetchone()
                row = db.fetchone()
                dbfile.close()

                await message.channel.send("Total cases in the US: " + str(casenum) + " Total deaths in the US: " + str(deathnum) + " This information was last updated on " + str(date) + ".")
            elif arguments[1] == "history":
                db.execute("select date, cases, deaths from covid19data")
                casenum1 = 0
                casenum2 = 0
                row = db.fetchone()
        if "I'm".lower() in content.lower():
            try:
                im_command(message)
            except Exception as e:
                if message.guild.id == 678789014869901342:
                    await message.channel.send(str(e))
                print(e)
        '''
        '''for i in bannedwordslist:
            if i in content:
                try:
                    await message.delete()
                    reecounter = reecounter + 1
                    await message.channel.send(ree + "\n I have detected " + str(reecounter) + " banned words in the time I've been online.")
                    await message.channel.send("The original message was sent by <@!" + str(message.author.id) + ">. It said `" + content + "` and the banned word was " + i + " .")
                    print("Message deleted.")
                    
                except Exception as e:
                    print(e)
        '''
    log.flush()

@client.event
@client.event
async def on_raw_reaction_add(payload):
    '''try:
        if payload.guild_id == 631316422328451082:
            if payload.message_id == 682814407872348234:
                role = discord.utils.get(payload.member.guild.roles, id=682818963193069663)
                print(role)
                await payload.member.add_roles(role)
                print("Role assigned to " + str(payload.member.name))
                log.write("Role assigned to " + str(payload.member.name) + " \n ")
                log.flush()
            elif payload.message_id == 683162633024962599:
                await payload.member.send("Here's an invite to the Bot Test Zone: https://discord.gg/yHEJS2p")
                log.write("Sent an invite to " + str(payload.member.name) + "\n")
                log.flush()
    except Exception as e:
        if message.guild.id == 678789014869901342:
            await message.channel.send(str(e))
        print(e)'''

# start bot
client.run(decrypted_token.decode())