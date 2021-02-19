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
import datetime

class DurationLimitError(discord.ext.commands.CommandError):
    def __init__(self):
        print("Maximum duration was exceeded.")

class NoSearchResultsError(discord.ext.commands.CommandError):
    def __init__(self):
        print("No search results for this song.")

class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = {}
        self.channels_playing_audio = []
        self.is_locked = False
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
        coro = asyncio.sleep(1)
        asyncio.run_coroutine_threadsafe(coro, self.bot.loop).result()
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
            name = await self.bot.loop.run_in_executor(None, self.bot.dbinst.retrieve, self.bot.database, "songs", "name", "id", f"{video}", False)
            duration = await self.bot.loop.run_in_executor(None, self.bot.dbinst.retrieve, self.bot.database, "songs", "duration", "id", f"{video}", False)
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
                    if info['duration'] == 0.0:
                        print("this video is a stream")
                        self.filename = info["url"]
                        self.duration = "No duration available (this is a stream)"
                    else:
                        m, s = divmod(info["duration"], 60)
                        print(m)
                        print(s)
                        self.duration = f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}"
                        if m > 60:
                            raise DurationLimitError()
                        if await self.bot.loop.run_in_executor(None, self.bot.dbinst.insert, self.bot.database, "songs", {"name":self.name, "id":video, "duration":self.duration}, "id") != "success":
                            await self.bot.loop.run_in_executor(None, self.bot.dbinst.delete, self.bot.database, "songs", video, "id")
                            await self.bot.loop.run_in_executor(None, self.bot.dbinst.insert, self.bot.database, "songs", {"name":self.name, "id":video, "duration":self.duration}, "id")
            print("got song from cache!")
        except FileNotFoundError:
            print("song isn't in cache")
            async with ctx.typing():
                with youtube_dl.YoutubeDL(ydl_opts) as youtubedl:
                    #the self.bot.loop.run_in_executor is to prevent the extract_info call from blocking other stuff
                    info = await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=False))
                    #get name of file we're going to play, for some reason prepare_filename
                    #doesn't return the correct file extension
                    self.name = info["title"]
                    self.url = f"https://youtube.com/watch?v={video}"
                    #if duration is 0, we got a stream, don't put that in the database/download it
                    if info['duration'] == 0.0:
                        print("this video is a stream")
                        self.filename = info["url"]
                        self.duration = "No duration available (this is a stream)"
                    else:
                        info = await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=True))
                        m, s = divmod(info["duration"], 60)
                        self.duration = f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}"
                        if m > 60:
                            raise DurationLimitError()
                        self.filename = youtubedl.prepare_filename(info).replace(youtubedl.prepare_filename(info).split(".")[1], "mp3")
                        await self.bot.loop.run_in_executor(None, self.bot.dbinst.insert, self.bot.database, "songs", {"name":self.name, "id":video, "duration":self.duration}, "id")
        return

    async def search_youtube_for_song(self, ydl, ctx, url, num):
        if num == 0:
            self.info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch5:{url}", download=False))
        try:
            self.id = self.info["entries"][num]["id"]
            self.name = self.info["entries"][num]["title"]
            m, s = divmod(self.info["entries"][num]["duration"], 60)
            self.duration = f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}"
        except IndexError:
            raise NoSearchResultsError()
        #check if max duration (60 minutes) exceeded
        if m > 60:
            print(f"Max duration exceeded on search result {num+1}. Retrying...")
            #if so, recursively call this function, going to the next search result
            await self.search_youtube_for_song(ydl, ctx, url, num+1)

    async def get_song(self, ctx, url):
        #block this from executing until the previous call is finished, we don't want multiple instances of this running in parallel-
        print("Locked execution.")
        self.is_locked = True
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
                            self.id = info["id"]
                            self.name = info["name"]
                            if int(str(info['duration']).split(':')[0]) > 60:
                                raise DurationLimitError()
                        else:
                            await self.search_youtube_for_song(ydl, ctx, url, 0)
                        await self.get_song_from_cache(ctx, self.id, ydl_opts)
                else:
                    #if the url is valid, don't try to search youtube, just get it from cache
                    await self.get_song_from_cache(ctx, url, ydl_opts)
            except DurationLimitError:
                await ctx.send("That song is too long. Due to limits on both data usage and storage space, I can't play songs longer than an hour.")
                self.is_locked = False
                raise discord.ext.commands.CommandError()
            except NoSearchResultsError:
                await ctx.send("I couldn't find any search results, or the first 5 search results were more than an hour long. Try running this command again, then try entering a more broad search term.")
                await self.bot.get_user(self.bot.owner_id).send(traceback.format_exc())
                traceback.print_exc()
                self.is_locked = False
                #raise CommandError so we don't play anything
                raise discord.ext.commands.CommandError()
            except Exception:
                await self.bot.get_user(self.bot.owner_id).send(traceback.format_exc())
                traceback.print_exc()
                self.is_locked = False
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
            #check if queue exists, init it if it doesn't exist
            try:
                self.song_queue[channel.id]
            except KeyError:
                self.song_queue[channel.id] = []
            #...unless we're already playing (or fetching) audio
            if channel.id not in self.channels_playing_audio:
                self.channels_playing_audio.append(channel.id)
                await ctx.send("Attempting to join the voice channel you're in...")
            else:
                #if we're already playing (or fetching) audio, add song to queue
                await ctx.send("Adding to your queue...")
                try:
                    #if locked, don't do anything until unlocked
                    async with ctx.typing():
                        while self.is_locked:
                            await asyncio.sleep(0.01)
                        await self.get_song(ctx, url)
                except:
                    traceback.print_exc()
                    return
                print(self.song_queue[channel.id])
                #actually add that stuff to queue
                self.song_queue[channel.id].append([self.filename, self.name, self.url, self.duration])
                print(self.song_queue[channel.id])
                await ctx.send(f"Added `{self.name}` to your queue! (<{self.url}>) Currently, you have {len(self.song_queue[channel.id])} {'songs' if len(self.song_queue[channel.id]) != 1 else 'song'} in your queue.")
                #unlock after sending message
                self.is_locked = False
                print("Added song to queue, unlocked.")
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
                    self.song_queue[vc.channel.id] = []
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
            #if locked, don't do anything until unlocked
            async with ctx.typing():
                while self.is_locked:
                    await asyncio.sleep(0.01)
                #then immediately lock and get song
                self.is_locked=True
                await self.get_song(ctx, url)
        except:
            self.channels_playing_audio.remove(ctx.voice_client.channel.id)
            return
        self.ctx = ctx
        print("playing audio...")
        try:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.filename), volume=0.5)
        except Exception:
            await ctx.send("I've encountered an error. Either something went seriously wrong, you provided an invalid URL, or you entered a search term with no results. Try running the command again. If you see this message again (after entering a more broad search term or a URL you're sure is valid), contact tk421#7244. ")
            return
        try:
            ctx.voice_client.stop()
        except:
            pass
        await ctx.send(f"{ctx.author.mention} Playing `{self.name}`... (<{self.url}>) \n Duration: {self.duration}")
        #unlock execution of get_song
        self.is_locked=False
        print("Done getting song, unlocked.")
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
    
    @commands.command(aliases=["q"])
    async def queue(self, ctx):
        '''View what's in your queue'''
        try:
            queuelength = len(self.song_queue[ctx.voice_client.channel.id])
            if queuelength != 0:
                m, s = 0, 0
                #get total duration, could probably clean this up a bit
                for i in self.song_queue[ctx.voice_client.channel.id]:
                    m += int(i[3].split(':')[0])
                    s += int(i[3].split(':')[1])
                #don't show amounts of seconds greater than 60
                m += s//60
                s = f"{0 if len(list(str(s))) == 1 else ''}{s%60}"
                await ctx.send(f"You have {queuelength} {'song in your queue: ' if queuelength == 1 else 'songs in your queue. '}\n{'Your queue: ' if queuelength != 1 else ''}{', '.join([f'`{i[1]}`(<{i[2]}>) Duration: {i[3]}' for i in self.song_queue[ctx.voice_client.channel.id]])}\n{f'Total duration: {m}:{s}' if queuelength != 1 else ''}") 
            else:
                await ctx.send("You don't have anything in your queue.")
        except (IndexError, AttributeError):
            traceback.print_exc()
            await ctx.send("You don't have anything in your queue.")

    @commands.command(aliases=["s"])
    async def skip(self, ctx):
        '''Skip the current song.'''
        try:
            assert self.song_queue[ctx.voice_client.channel.id] != []
            await ctx.send(embed=discord.Embed(title="\U000023e9 Skipping to the next song in the queue... ", color=discord.Color.blurple()))
            #fade audio out
            while ctx.voice_client.source.volume != 0:
                ctx.voice_client.source.volume -= 0.01
                await asyncio.sleep(0.01)
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
                await ctx.send(embed=discord.Embed(title=f"\U000023f8 Paused. Run `{self.bot.command_prefix}resume` to resume audio, or run `{self.bot.command_prefix}leave` to make me leave the voice channel.", color=discord.Color.blurple()))
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
        '''Set the volume of audio to the provided percentage. The default volume is 50%.'''
        try:
            newvolume = int(newvolume.replace("%", ""))
            if newvolume > 100 or newvolume < 0 or newvolume == None:
                await ctx.send("You need to specify a volume percentage between 0 and 100.")
            else:
                ctx.voice_client.source.volume = newvolume/100
                await ctx.send(embed=discord.Embed(title=f"\U00002705 Set volume to {newvolume}%.{' Warning: Music may sound distorted at this volume level.' if newvolume >= 90 else ''}", color=discord.Color.blurple()))
        except ValueError:
            await ctx.send("You can't specify a decimal value for the volume.")
        except AttributeError:
            traceback.print_exc()
            await ctx.send("I'm not in a voice channel.")

    @commands.command(aliases=["c"])
    async def clear(self, ctx):
        '''Clear the queue.'''
        try:
            assert self.song_queue[ctx.voice_client.channel.id] != []
            self.song_queue[ctx.voice_client.channel.id] = []
            await ctx.send(embed=discord.Embed(title="\U00002705 Cleared your queue!", color=discord.Color.blurple()))
        except AssertionError:
            await ctx.send("You don't have anything in your queue.")
        except Exception:
            await ctx.send("I'm not in a voice channel.")



def setup(bot):
    bot.add_cog(music(bot))

def teardown(bot):
    bot.remove_cog(music(bot))
