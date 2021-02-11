import discord
from discord.ext import commands
import asyncio
import random
import os
import youtube_dl
import urllib
import aiohttp
import traceback
import time
import functools
import typing

class DurationLimitError(discord.ext.commands.CommandError):
    def __init__(self):
        print("Maximum duration was exceeded.")

class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = {}
        self.channels_playing_audio = []
        #TODO: defer adding to queue until previous get_song call finishes (this variable will be used for that)
        self.channels_getting_songs = []
        
    #some unused stuff, intended to save queues to db
    def push_queue_item_to_db(self, entry, position, ctx):
        if self.bot.dbinst.insert(self.bot.database, "queues", {"channel_id":ctx.author.voice.channel.id, "position":position, "name":entry[1], "url":entry[2], "filename":entry[0]}, "position")=="success":
            return
        else:
            raise commands.CommandInvokeError("Error while adding a song to the queue. If this happens frequently, let tk421#7244 know.")
    def remove_queue_item_from_db(self, entry, position, ctx):
        if self.bot.dbinst.delete(self.bot.database, "queues", {"channel_id":ctx.author.voice.channel.id, "position":position, "name":entry[1], "url":entry[2], "filename":entry[0]})=="success":
            return
        else:
            raise commands.CommandInvokeError("Error while removing a song from the queue. If this happens frequently, let tk421#7244 know.")

    def process_queue(self, ctx, channel, error):
        #this is a callback that is executed after song ends
        try:
            if channel.id not in self.channels_playing_audio:
                return
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.song_queue[channel.id][0][0]), volume=0.5)
            print("playing next song in queue...")
            #need to do this because we can't await coros, this isn't an async function
            coro = ctx.send(f"{ctx.author.mention} Playing `{self.song_queue[channel.id][0][1]}`... (<{self.song_queue[channel.id][0][2]}>)")
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            fut.result()
            self.song_queue[channel.id].remove(self.song_queue[channel.id][0])
            #we can't pass stuff to process_queue in after, so pass some stuff to it before passing it
            handle_queue = functools.partial(self.process_queue, ctx, channel)
            ctx.voice_client.play(source, after=handle_queue)
        except IndexError:
            print("done with queue!")
            self.channels_playing_audio.remove(channel.id)
            self.song_queue[channel.id] = []

    async def get_song_from_cache(self, ctx, url, ydl_opts):
        try:
            print("getting song from cache")
            #get video id from parameters, try to open mp3 file matching that id (if that file exists, play it instead of downloading it)
            if "youtu.be" in url:
                video = url.split("/")[3]
            elif "youtube.com" in url:
                url_data = urllib.parse.urlparse(url)
                query = urllib.parse.parse_qs(url_data.query)
                video = query["v"][0]
            else:
                #function doesn't take user input, so it's safe to assume the url is an id
                video = url 
            open(f"songcache/{video}.mp3", "r")
            #check if video id is in database, add it if it isn't
            name = self.bot.dbinst.retrieve(self.bot.database, "songs", "name", "id", f"{video}", False)
            duration = self.bot.dbinst.retrieve(self.bot.database, "songs", "duration", "id", f"{video}", False)
            if name != None and duration != None:
                self.name = name
                self.filename = f"songcache/{video}.mp3"
                self.duration = duration
                self.url = f"https://youtube.com/watch?v={video}"
            else:
                with youtube_dl.YoutubeDL(ydl_opts) as youtubedl:
                    info = await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=False))
                    self.url = f"https://youtube.com/watch?v={video}"
                    self.name = info["title"]
                    self.filename = f"songcache/{video}.mp3"
                    self.duration = f"{str(info['duration']/60).split('.')[0]}:{info['duration']%60 if len(list(str(info['duration']%60))) != 1 else '0'+str(info['duration']%60)}"
                    if int(str(info['duration']/60).split('.')[0]) > 60:
                        raise DurationLimitError()
                    if self.bot.dbinst.insert(self.bot.database, "songs", {"name":self.name, "id":video, "duration":self.duration}, "id") != "success":
                        self.bot.dbinst.delete(self.bot.database, "songs", video, "id")
                        self.bot.dbinst.insert(self.bot.database, "songs", {"name":self.name, "id":video, "duration":self.duration}, "id")
            print("got song from cache!")
        except FileNotFoundError:
            print("song isn't in cache")
            async with ctx.typing():
                with youtube_dl.YoutubeDL(ydl_opts) as youtubedl:
                    #the self.bot.loop.run_in_executor is to prevent the extract_info call from blocking other stuff
                    info = await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=True))
                    #get name of file we're going to play, for some reason prepare_filename
                    #doesn't return the correct file extension
                    self.name = info["title"]
                    self.url = f"https://youtube.com/watch?v={video}"
                    self.duration = f"{str(info['duration']/60).split('.')[0]}:{info['duration']%60}"
                    self.filename = youtubedl.prepare_filename(info).replace(youtubedl.prepare_filename(info).split(".")[1], "mp3")
                    self.bot.dbinst.insert(self.bot.database, "songs", {"name":self.name, "id":video, "duration":self.duration}, "id", False, None, False, None, False)
        return

    async def get_song(self, ctx, url):
        ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'songcache/%(id)s.%(ext)s',
        'quiet': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'no_warnings': True,
        'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192'
        }]
        }
        async with ctx.typing():
            try:
                try:
                    #check if we've been provided a valid url
                    async with aiohttp.ClientSession() as cs:
                        await cs.get(url)
                except Exception:
                    #if not, search youtube
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        #if song isn't in db, search youtube, get first result, check cache,  download file if it's not in cache
                        print("searching youtube...")
                        info = self.bot.dbinst.exec_safe_query(self.bot.database, "select * from songs where name like %s", (f"%{url}%"))
                        if info != None:
                            print("found song in db! trying to get from cache...")
                            id = info["id"]
                            self.name = info["name"]
                            if int(str(info['duration']).split(':')[0]) > 60:
                                raise DurationLimitError()
                        else:
                            info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch:{url}", download=False))
                            id = info["entries"][0]["id"]
                            self.name = info["entries"][0]["title"]
                            self.duration = f"{str(info['entries'][0]['duration']/60).split('.')[0]}:{info['entries'][0]['duration']%60 if len(list(str(info['entries'][0]['duration']%60))) != 1 else '0'+str(info['entries'][0]['duration']%60)}"
                            if int(str(info['entries'][0]['duration']/60).split('.')[0]) > 60:
                                raise DurationLimitError()
                        await self.get_song_from_cache(ctx, id, ydl_opts)
                else:
                    #if the url is valid, don't try to search youtube, just get it from cache
                    await self.get_song_from_cache(ctx, url, ydl_opts)
            except DurationLimitError:
                await ctx.send("That song is too long. Due to limits both on data usage and storage space, I can't play songs longer than an hour.")
                raise discord.ext.commands.CommandError()
            except Exception:
                traceback.print_exc()
                #raise CommandError so we don't play anything
                raise discord.ext.commands.CommandError()

    @commands.command(aliases=["p"])
    async def play(self, ctx, *, url=None):
        '''Play something from youtube. You need to provide a valid Youtube URL or a search term for this to work.'''
        if url == None:
            await ctx.send("You need to specify a url or something to search for.")
            return
        #attempt to join the vc that the command's invoker is in...
        try:
            channel = ctx.author.voice.channel
            try:
                self.song_queue[channel.id]
            except KeyError:
                self.song_queue[channel.id] = []
            #...unless we're already playing (or fetching) audio
            if channel.id not in self.channels_playing_audio:
                self.channels_playing_audio.append(channel.id)
                await ctx.send("Attempting to join the voice channel you're in...")
            else:
                #if we're already playing (or fetching) audio, add song to queue (this is likely to error or display the wrong song if many people use this command concurrently)
                await ctx.send("Adding to your queue...")
                await self.get_song(ctx, url)
                print(self.song_queue[channel.id])
                self.song_queue[channel.id].append([self.filename, self.name, self.url, self.duration])
                print(self.song_queue[channel.id])
                await ctx.send(f"Added `{self.name}` to your queue! (<{self.url}>) Currently, you have {len(self.song_queue[channel.id])} songs in your queue.")
                return
        except AttributeError:
            traceback.print_exc()
            await ctx.send("You aren't in a voice channel. Join one, then run this command again.")
            return
        except Exception:
            traceback.print_exc()
        vc = ctx.voice_client
        if vc:
            if vc.channel.id == channel.id:
                await ctx.send(f"I'm already in your voice channel, so I won't reconnect.")
            else:
                try:
                    await vc.move_to(channel)
                except asyncio.TimeoutError:
                    await ctx.send(f'Moving to the `{channel}` voice channel timed out.')
                    return
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                await ctx.send(f'Connecting to the `{channel}` voice channel timed out.')
                return
        print("connected to vc")
        await ctx.send(f'Connected to the `{channel}` voice channel. Getting audio... (this may take a while for long songs)')
        #after connecting, download audio from youtube (try to get it from cache first to speed things up and save bandwidth)
        try:
            await self.get_song(ctx, url)
        except:
            return
        self.ctx = ctx
        print("playing audio...")
        try:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.filename), volume=0.5)
        except Exception:
            await ctx.send("I've encountered an error. Either something went seriously wrong, you provided an invalid URL, or you entered a search term with no results. Try running the command again. If you see this message again (after entering a more broad search term or a URL you're sure is valid), contact tk421#7244. ")
            return
        await ctx.send(f"{ctx.author.mention} Playing `{self.name}`... (<{self.url}>) \n Duration: {self.duration}")
        #then play the audio
        #we can't pass stuff to process_queue in after, so pass some stuff to it before executing it
        handle_queue = functools.partial(self.process_queue, ctx, channel)
        ctx.voice_client.play(source, after=handle_queue)

    @commands.command(aliases=["l"])
    async def leave(self, ctx):
        '''Leaves the current voice channel.'''
        try:
            try:
                self.channels_playing_audio.remove(ctx.voice_client.channel.id)
                self.song_queue[ctx.voice_client.channel.id] = []
            except:
                pass
            await ctx.guild.voice_client.disconnect()
            print("left vc, reset queue")
            await ctx.send(embed=discord.Embed(title="\U00002705 Left the voice channel.", color=discord.Color.blurple()))
        except AttributeError:
            await ctx.send("I'm not in a voice channel.")
    
    @commands.command(hidden=True, aliases=["q"])
    async def queue(self, ctx):
        try:
            queuelength = len(self.song_queue[ctx.voice_client.channel.id])
            if queuelength != 0:
                await ctx.send(f"You have {queuelength} {'song in your queue: ' if queuelength == 1 else 'songs in your queue. '}\n{'Your queue: ' if queuelength != 1 else ''}{', '.join([f'`{i[1]}`(<{i[2]}>) Duration: {i[3]}' for i in self.song_queue[ctx.voice_client.channel.id]])}") 
            else:
                await ctx.send("You don't have anything in your queue.")
        except (IndexError, AttributeError):
            await ctx.send("You don't have anything in your queue.")

    @commands.command(aliases=["s"])
    async def skip(self, ctx):
        '''Skip the current song.'''
        try:
            assert self.song_queue[ctx.voice_client.channel.id] != []
            await ctx.send(embed=discord.Embed(title="\U000023e9 Skipping to the next song in the queue... ", color=discord.Color.blurple()))
            await asyncio.sleep(1)
            ctx.voice_client.stop()
        except AssertionError:
            await ctx.send("You don't have anything in your queue.")
        except Exception:
            await ctx.send("I'm not in a voice channel.")

    @commands.command()
    async def pause(self, ctx):
        '''Pause the current song'''
        try:
            assert ctx.guild.me.voice != None
            if ctx.voice_client.is_playing():
                ctx.voice_client.pause()
                await ctx.send(embed=discord.Embed(title=f"\U000023f8 Paused. Run `{self.bot.command_prefix}resume` to resume audio, or use `{self.bot.command_prefix}leave` to make me leave the voice channel.", color=discord.Color.blurple()))
            elif ctx.voice_client.is_paused():
                await ctx.send(embed=discord.Embed(title=f"\U0000274c I'm already paused. Use `{self.bot.command_prefix}resume` to resume.", color=discord.Color.blurple()))
            else:
                await ctx.send(embed=discord.Embed(title="\U0000274c I'm not playing anything.", color=discord.Color.blurple()))
        except Exception:
            traceback.print_exc()
            await ctx.send("I'm not in a voice channel.")

    @commands.command(aliases=["unpause"])
    async def resume(self, ctx):
        '''Resume the current song'''
        try:
            assert ctx.guild.me.voice != None
            if ctx.voice_client.is_paused():
                await ctx.send(embed=discord.Embed(title="\U000025b6 Resuming...", color=discord.Color.blurple()))
                ctx.voice_client.resume()
                return
            elif ctx.voice_client.is_playing():
                await ctx.send(embed=discord.Embed(title="\U0000274c I'm already playing something.", color=discord.Color.blurple()))
            else:
                await ctx.send(embed=discord.Embed(title="\U0000274c I'm not playing anything.", color=discord.Color.blurple()))
        except Exception:
            traceback.print_exc()
            await ctx.send("I'm not in a voice channel.")
    
    @commands.command(aliases=["v"])
    async def volume(self, ctx, newvolume):
        '''Set the volume of audio to the provided percentage. The default volume when you start playing music is 50%.'''
        try:
            newvolume = int(newvolume)
            if newvolume > 100 or newvolume < 0 or newvolume == None:
                await ctx.send("You need to specify a volume percentage between 0 and 100.")
            else:
                ctx.voice_client.source.volume = newvolume/100
                await ctx.send(embed=discord.Embed(title=f"\U00002705 Set volume to {newvolume}%.", color=discord.Color.blurple()))
        except ValueError:
            await ctx.send("You can't specify a decimal value for the volume.")
        except AttributeError:
            traceback.print_exc()
            await ctx.send("I'm not in a voice channel.")



def setup(bot):
    bot.add_cog(music(bot))

def teardown(bot):
    bot.remove_cog(music(bot))
