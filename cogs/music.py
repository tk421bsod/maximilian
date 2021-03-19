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
import logging

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
        self.current_song = {}
        self.logger = logging.getLogger(f"maximilian.{__name__}")
        
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

    async def _wait_for unlock(self)
        while self.is_locked:
            await asyncio.sleep(0.01)
        return

    async def _fade_audio(self, newvolume, ctx):
        '''Smoothly transition between volume levels'''
        while ctx.voice_client.source.volume != newvolume/100:
            #make volume a double so this doesn't loop infinitely (as volume can be something like 1.000000000004 sometimes)
            ctx.voice_client.source.volume = round(ctx.voice_client.source.volume, 2)
            if newvolume/100 < ctx.voice_client.source.volume:
                ctx.voice_client.source.volume -= 0.01
            elif newvolume/100 > ctx.voice_client.source.volume:
                ctx.voice_client.source.volume += 0.01
            await asyncio.sleep(0.005)

    def process_queue(self, ctx, channel, error):
        '''Starts playing the next song in the queue, cleans up some stuff if the queue is empty'''
        coro = asyncio.sleep(1)
        asyncio.run_coroutine_threadsafe(coro, self.bot.loop).result()
        #this is a callback that is executed after song ends
        try:
            if channel.id not in self.channels_playing_audio:
                return
            if self.current_song[channel.id][0]:
                #reset duration when repeating
                self.current_song[channel.id][6], self.current_song[channel.id][7], self.current_song[channel.id][8] = time.time(), 0, 0
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.current_song[channel.id][1]), volume=self.current_song[channel.id][9])
                self.logger.info("repeating song...")
                #we can't pass stuff to process_queue in after, so pass some stuff to it before passing it
                handle_queue = functools.partial(self.process_queue, ctx, channel)
            else:
                self.logger.info("playing next song in queue...")
                #build now playing embed, send it
                embed = discord.Embed(title="Now playing:", description=f"`{self.song_queue[channel.id][0][1]}`", color=discord.Color.blurple())
                embed.add_field(name="Video URL", value=f"<{self.song_queue[channel.id][0][2]}>", inline=True)
                embed.add_field(name="Duration", value=f"{self.song_queue[channel.id][0][3]}")
                embed.set_image(url=f"{self.song_queue[channel.id][0][4]}")
                coro = ctx.send(embed=embed)
                fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                fut.result()
                volume = self.current_song[channel.id][9]
                #update current_song with info about the new song
                self.current_song[channel.id] = [False, self.song_queue[channel.id][0][0], self.song_queue[channel.id][0][3], self.song_queue[channel.id][0][1], self.song_queue[channel.id][0][4], self.song_queue[channel.id][0][2], time.time(), 0, 0, volume]
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.song_queue[channel.id][0][0]), volume=volume)
                self.song_queue[channel.id].remove(self.song_queue[channel.id][0])
                handle_queue = functools.partial(self.process_queue, ctx, channel)
            ctx.voice_client.play(source, after=handle_queue)
        except IndexError:
            self.logger.info("done with queue!")
            #remove channel from channels_playing_audio, reset info about current song, blank queue
            try:
                self.channels_playing_audio.remove(channel.id)
                self.current_song[channel.id] = []
                self.song_queue[channel.id] = []
            except:
                pass
            #if something's downloading, wait until it finishes, then check the queue again
            while self.is_locked:
                asyncio.run_coroutine_threadsafe(asyncio.sleep(0.001), self.bot.loop).result()
                if not self.is_locked:
                    self.process_queue(ctx, channel, None)

    async def get_song_from_cache(self, ctx, url, ydl_opts):
        '''Attempts to find an mp3 matching the video id locally, downloading the video if that file isn't found. This prioritizes speed, checking if a song is saved locally before downloading it from Youtube.'''
        try:
            self.logger.info("getting song from cache")
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
            thumbnail = await self.bot.loop.run_in_executor(None, self.bot.dbinst.retrieve, self.bot.database, "songs", "thumbnail", "id", f"{video}", False)
            if name != None and duration != None and thumbnail != None:
                self.name = name
                self.filename = f"songcache/{video}.mp3"
                self.duration = duration
                self.thumbnail = thumbnail
                self.url = f"https://youtube.com/watch?v={video}"
            else:
                with youtube_dl.YoutubeDL(ydl_opts) as youtubedl:
                    info = await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=False))
                    self.url = f"https://youtube.com/watch?v={video}"
                    self.name = info["title"]
                    self.filename = f"songcache/{video}.mp3"
                    self.thumbnail = info["thumbnail"]
                    if info['duration'] == 0.0:
                        self.logger.info("this video is a stream")
                        self.filename = info["url"]
                        self.duration = "No duration available (this is a stream)"
                    else:
                        m, s = divmod(info["duration"], 60)
                        self.duration = f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}"
                        if m > 60:
                            raise DurationLimitError()
                        if await self.bot.loop.run_in_executor(None, self.bot.dbinst.insert, self.bot.database, "songs", {"name":self.name, "id":video, "duration":self.duration, "thumbnail":self.thumbnail}, "id") != "success":
                            await self.bot.loop.run_in_executor(None, self.bot.dbinst.delete, self.bot.database, "songs", video, "id")
                            await self.bot.loop.run_in_executor(None, self.bot.dbinst.insert, self.bot.database, "songs", {"name":self.name, "id":video, "duration":self.duration, "thumbnail":self.thumbnail}, "id")
            self.logger.info("got song from cache!")
        except FileNotFoundError:
            self.logger.info("song isn't in cache")
            async with ctx.typing():
                with youtube_dl.YoutubeDL(ydl_opts) as youtubedl:
                    #the self.bot.loop.run_in_executor is to prevent the extract_info call from blocking other stuff
                    info = await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=False))
                    #get name of file we're going to play, for some reason prepare_filename
                    #doesn't return the correct file extension
                    self.name = info["title"]
                    self.url = f"https://youtube.com/watch?v={video}"
                    self.thumbnail = info["thumbnail"]
                    #if duration is 0, we got a stream, don't put that in the database/download it
                    if info['duration'] == 0.0:
                        self.logger.info("this video is a stream")
                        self.filename = info["url"]
                        self.duration = "No duration available (this is a stream)"
                    else:
                        #now that we're sure it isn't a stream, download the video
                        info = await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=True))
                        m, s = divmod(info["duration"], 60)
                        self.duration = f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}"
                        if m > 60:
                            raise DurationLimitError()
                        self.filename = youtubedl.prepare_filename(info).replace(youtubedl.prepare_filename(info).split(".")[1], "mp3")
                        await self.bot.loop.run_in_executor(None, self.bot.dbinst.insert, self.bot.database, "songs", {"name":self.name, "id":video, "duration":self.duration, "thumbnail":self.thumbnail}, "id")
        return

    async def search_youtube_for_song(self, ydl, ctx, url, num):
        '''Searches Youtube for a song and extracts metadata from the first search result. If the maximum duration is exceeded, it goes to the next search result, up to 4 times.'''
        if num == 0:
            self.info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch5:{url}", download=False))
        try:
            self.id = self.info["entries"][num]["id"]
            self.name = self.info["entries"][num]["title"]
            m, s = divmod(self.info["entries"][num]["duration"], 60)
            self.duration = f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}"
            self.thumbnail = self.info["entries"][num]["thumbnail"]
        except IndexError:
            self.logger.info(self.info["entries"])
            raise NoSearchResultsError()
        #check if max duration (60 minutes) exceeded
        if m > 60:
            self.logger.warning(f"Max duration exceeded on search result {num+1}. Retrying...")
            #if so, recursively call this function, going to the next search result
            await self.search_youtube_for_song(ydl, ctx, url, num+1)

    async def get_song(self, ctx, url):
        '''Gets the filename, id, and other metadata of a song. This tries to look up a song in the database first, then it searches Youtube if that fails.'''
        #block this from executing until the previous call is finished, we don't want multiple instances of this running in parallel-
        self.is_locked = True
        self.logger.info("Locked execution.")
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
                        self.logger.info("searching youtube...")
                        info = self.bot.dbinst.exec_safe_query(self.bot.database, "select * from songs where name like %s", (f"%{url}%"))
                        if info != None:
                            self.logger.info("found song in db! trying to get from cache...")
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
                await ctx.send("I couldn't find any search results, or the first 5 search results were more than an hour long. Try running this command again (Youtube sometimes fails to give me a list of search results, this is an issue on Youtube's end), then try entering a more broad search term if you get this error again.")
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

    
    #executes when someone sends a message with the prefix followed by 'play'
    @commands.command(aliases=["p"], help=f"Play something from youtube. You need to provide a valid Youtube URL or a search term for this to work. For example, you can use `?play never gonna give you up` (this assumes the prefix is `?`, just replace `?` with the current prefix if it's different) to search youtube for a song named 'never gonna give you up' and rickroll all of your friends in the voice channel.")
    async def play(self, ctx, *, url=None):
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
            #don't join vc if we're already playing (or fetching) audio
            if channel.id not in self.channels_playing_audio:
                self.channels_playing_audio.append(channel.id)
                joiningmessage = await ctx.send("Joining your voice channel...")
            else:
                #if we're already playing (or fetching) audio, add song to queue
                await ctx.send("Adding to your queue...")
                #show warning if repeating song
                try:
                    if self.current_song[channel.id][0] == True:
                        await ctx.send(f"\U000026a0 I'm repeating a song right now. I'll still add this song to your queue, but I won't play it until you run `{self.bot.command_prefix}loop` again (and wait for the current song to finish) or skip the current song using `{self.bot.command_prefix}skip`.")
                    elif self.current_song[ctx.voice_client.channel.id][2] == "No duration available (this is a stream)":
                        await ctx.send(f"\U000026a0 I'm playing a stream right now. I'll still add this song to your queue, but I won't play it until you run `{self.bot.command_prefix}skip` or the stream ends.")
                except KeyError:
                    #if there's a keyerror, nothing's playing. this is normal if someone adds stuff to queue rapidly, so ignore it
                    pass
                try:
                    #if locked, don't do anything until unlocked
                    async with ctx.typing():
                        await self._wait_for_unlock()
                        await self.get_song(ctx, url)
                except:
                    #get_song SHOULD handle exceptions properly so we don't need to do anything here
                    traceback.print_exc()
                    return
                #actually add that stuff to queue
                self.song_queue[channel.id].append([self.filename, self.name, self.url, self.duration, self.thumbnail])
                await ctx.send(embed=discord.Embed(title=f"Added a song to your queue!", color=discord.Color.blurple()).add_field(name="Song Name:", value=f"`{self.name}`", inline=False).add_field(name="Video URL:", value=f"<{self.url}>", inline=True).set_footer(text=f"Currently, you have {len(self.song_queue[channel.id])} {'songs' if len(self.song_queue[channel.id]) != 1 else 'song'} in your queue. \nUse {self.bot.command_prefix}queue to view your queue.").add_field(name="Duration:", value=self.duration, inline=True).set_image(url=self.thumbnail))
                #unlock after sending message
                self.is_locked = False
                self.logger.info("Added song to queue, unlocked.")
                return
        except AttributeError:
            traceback.print_exc()
            await ctx.send("You aren't in a voice channel. Join one, then run this command again.")
            return
        except Exception:
            traceback.print_exc()
            return
        vc = ctx.voice_client
        if vc:
            if vc.channel.id == channel.id:
                await joiningmessage.edit(content="I'm already in your voice channel, so I won't reconnect.")
            else:
                try:
                    self.song_queue[vc.channel.id] = []
                    await vc.move_to(channel)
                except asyncio.TimeoutError:
                    await joiningmessage.edit(content='Moving to the `{channel}` voice channel timed out.')
                    return
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                await joiningmessage.edit(content='Connecting to the `{channel}` voice channel timed out.')
                return
        self.logger.info("connected to vc")
        await ctx.send(embed=discord.Embed(title=f'\U00002705 Connected to `{channel}`. Getting audio... (this may take a while for long songs)', color=discord.Color.blurple()))
        #after connecting, download audio from youtube (try to get it from cache first to speed things up and save bandwidth)
        try:
            #if locked, don't do anything until unlocked
            async with ctx.typing():
                await self._wait_for_unlock()
                #then immediately lock and get song
                await self.get_song(ctx, url)
        except:
            self.channels_playing_audio.remove(ctx.voice_client.channel.id)
            return
        self.ctx = ctx
        self.logger.info("playing audio...")
        try:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.filename), volume=0.5)
        except Exception:
            await ctx.send("I've encountered an error. Either something went seriously wrong, you provided an invalid URL, or you entered a search term with no results. Try running the command again. If you see this message again (after entering a more broad search term or a URL you're sure is valid), contact tk421#7244. ")
            return
        try:
            ctx.voice_client.stop()
        except:
            pass
        #current_song is a bunch of information about the current song that's playing.
        #that information in order:
        #0: Is this song supposed to repeat?, 1: Filename, 2: Duration (already in the m:s format), 3: Video title,  4: Thumbnail URL, 5: Video URL, 6: time the song started (now), 7: Time when paused, 8: Total time paused, 9: Volume
        self.current_song[ctx.voice_client.channel.id] = [False, self.filename, self.duration, self.name, self.thumbnail, self.url, time.time(), 0, 0, 0.5]
        embed = discord.Embed(title="Now playing:", description=f"`{self.name}`", color=discord.Color.blurple())
        embed.add_field(name="Video URL", value=f"<{self.url}>", inline=True)
        embed.add_field(name="Total Duration", value=f"{self.duration}")
        embed.set_image(url=self.thumbnail)
        await ctx.send(embed=embed)
        #unlock execution of get_song
        self.is_locked=False
        self.logger.info("Done getting song, unlocked.")
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
                self.current_song[ctx.voice_client.channel.id] = []
            except:
                pass
            await ctx.guild.voice_client.disconnect()
            self.logger.info("left vc, reset queue")
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
                    s, m = int(s), int(m)
                    try:
                        m += int(i[3].split(':')[0])
                        s += int(i[3].split(':')[1])
                    except ValueError:
                        continue
                    #don't show amounts of seconds greater than 60
                    m += s//60
                s = f"{0 if len(list(str(s))) == 1 else ''}{s%60}"
                h = f"{'' if int(m)//60 < 1 else f'{int(m)//60}:'}"
                m = f"{0 if len(str(m)) == 1 else ''}{m%60}"
                newline = "\n" #terrible, evil hack for using newlines in fstrings
                #the following statement is really long and hard to read, not sure whether to split into multiple lines or not
                #show user's queue, change how it's displayed depending on how many songs are in the queue
                await ctx.send(f"You have {queuelength} {'song in your queue: ' if queuelength == 1 else 'songs in your queue. '}\n{f'Your queue: {newline}' if queuelength != 1 else ''}{f'{newline}'.join([f'{count+1}: `{i[1]}`(<{i[2]}>) Duration: {i[3]}' for count, i in enumerate(self.song_queue[ctx.voice_client.channel.id])])}\n{f'Total duration: {h}{m}:{s}' if queuelength != 1 and f'{h}{m}:{s}' != '0:0' else ''}\nUse `{self.bot.command_prefix} remove <song's position>` to remove a song from your queue. For example, `{self.bot.command_prefix} remove 1` removes the first item in the queue.\nYou can add items to your queue by using the `play` command again while a song is playing.") 
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
            self.current_song[ctx.voice_client.channel.id][0] = False
            #fade audio out
            await self._fade_audio(0, ctx)
            await asyncio.sleep(1)
            #stop playback, this immediately calls process_queue
            ctx.voice_client.stop()
        except AssertionError:
            await ctx.send("You don't have anything in your queue.")
        except Exception:
            traceback.print_exc()
            await ctx.send("I'm not in a voice channel.")

    @commands.command()
    async def pause(self, ctx):
        '''Pause the current song'''
        try:
            assert ctx.guild.me.voice != None
            if ctx.voice_client.is_playing():
                ctx.voice_client.pause()
                self.current_song[ctx.voice_client.channel.id][7] = time.time()
                await ctx.send(embed=discord.Embed(title=f"\U000023f8 Paused. Run `{self.bot.command_prefix}resume` to resume audio, or run `{self.bot.command_prefix}leave` to make me leave the voice channel.", color=discord.Color.blurple()))
            elif ctx.voice_client.is_paused():
                await ctx.send(embed=discord.Embed(title=f"<:red_x:813135049083191307> I'm already paused. Use `{self.bot.command_prefix}resume` to resume.", color=discord.Color.blurple()))
            else:
                await ctx.send(embed=discord.Embed(title="<:red_x:813135049083191307> I'm not playing anything.", color=discord.Color.blurple()))
        except Exception:
            traceback.print_exc()
            await ctx.send("I'm not in a voice channel.")

    @commands.command(aliases=["unpause"])
    async def resume(self, ctx):
        '''Resume the current song'''
        try:
            assert ctx.guild.me.voice != None
            if ctx.voice_client.is_paused():
                self.current_song[ctx.voice_client.channel.id][8] += round(time.time() - self.current_song[ctx.voice_client.channel.id][7])
                await ctx.send(embed=discord.Embed(title="\U000025b6 Resuming...", color=discord.Color.blurple()))
                ctx.voice_client.resume()
                return
            elif ctx.voice_client.is_playing():
                await ctx.send(embed=discord.Embed(title="<:red_x:813135049083191307> I'm already playing something.", color=discord.Color.blurple()))
            else:
                await ctx.send(embed=discord.Embed(title="<:red_x:813135049083191307> I'm not playing anything.", color=discord.Color.blurple()))
        except Exception:
            traceback.print_exc()
            await ctx.send("I'm not in a voice channel.")
    
    @commands.command(aliases=["v"])
    async def volume(self, ctx, newvolume : typing.Optional[str]=None):
        '''Set the volume of audio to the provided percentage. The default volume is 50%.'''
        try:
            if newvolume == None:
                await ctx.send(f"Volume is currently set to {int(self.current_song[ctx.voice_client.channel.id][9]*100)}%.")
                return
            newvolume = int(newvolume.replace("%", ""))
            if newvolume > 100 or newvolume < 0:
                await ctx.send("You need to specify a volume percentage between 0 and 100.")
            elif newvolume/100 == ctx.voice_client.source.volume:
                await ctx.send(f"Volume is already set to {newvolume}%.")
            else:
                await self._fade_audio(newvolume, ctx)
                self.current_song[ctx.voice_client.channel.id][9] = newvolume/100
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

    @commands.command(aliases=["loop", "lo"])
    async def repeat(self, ctx):
        '''Toggle repeating the current song.'''
        try: 
            if ctx.voice_client.is_playing() and self.current_song[ctx.voice_client.channel.id][2] != "No duration available (this is a stream)":
                if self.current_song[ctx.voice_client.channel.id][0]:
                    self.current_song[ctx.voice_client.channel.id][0] = False
                    await ctx.send(embed=discord.Embed(title="I won't repeat the current song anymore.", color=discord.Color.blurple()))
                else:
                    self.current_song[ctx.voice_client.channel.id][0] = True
                    await ctx.send(embed=discord.Embed(title="\U0001f501 I'll repeat the current song after it finishes. Run this command again to stop repeating the current song.", color=discord.Color.blurple()))
            elif self.current_song[ctx.voice_client.channel.id][2] == "No duration available (this is a stream)":
                await ctx.send(embed=discord.Embed(title="<:red_x:813135049083191307> I can't repeat streams.", color=discord.Color.blurple()))
            else:
                await ctx.send(embed=discord.Embed(title="<:red_x:813135049083191307> I'm not playing anything right now.", color=discord.Color.blurple()))
        except AttributeError:
            await ctx.send(embed=discord.Embed(title="<:red_x:813135049083191307> I'm not playing anything right now.", color=discord.Color.blurple()))
        except IndexError:
            await ctx.send("I'm not in a voice channel.")

    @commands.command(aliases=["cs", "np", "song", "currentsong", "currentlyplaying", "cp"])
    async def nowplaying(self, ctx):
        '''Show the song that's currently playing.'''
        try:
            if ctx.voice_client.is_playing():
                #get elapsed duration, make it human-readable
                m, s = divmod(round((time.time() - self.current_song[ctx.voice_client.channel.id][6]) - self.current_song[ctx.voice_client.channel.id][8]), 60)
            elif ctx.voice_client.is_paused():
                m, s = divmod(round((self.current_song[ctx.voice_client.channel.id][7] - self.current_song[ctx.voice_client.channel.id][6]) - self.current_song[ctx.voice_client.channel.id][8]), 60)
            else:
                await ctx.send(embed=discord.Embed(title="<:red_x:813135049083191307> I'm not playing anything right now.", color=discord.Color.blurple()))
                return
            embed = discord.Embed(title="Currently playing:", description=f"`{self.current_song[ctx.voice_client.channel.id][3]}`", color=discord.Color.blurple())
            embed.add_field(name="Video URL", value=f"<{self.current_song[ctx.voice_client.channel.id][5]}>", inline=True)
            if self.current_song[ctx.voice_client.channel.id][2] == "No duration available (this is a stream)":
                embed.add_field(name="Duration (Elapsed/Total)", value=f"You've been listening to this stream for {m} minutes and {s} seconds.")
            else:
                embed.add_field(name="Duration (Elapsed/Total)", value=f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}/{self.current_song[ctx.voice_client.channel.id][2]}")
            embed.set_image(url=self.current_song[ctx.voice_client.channel.id][4])
            await ctx.send(embed=embed)
        except AttributeError:
            await ctx.send(embed=discord.Embed(title="<:red_x:813135049083191307> I'm not in a voice channel.", color=discord.Color.blurple()))

    @commands.command(aliases=["quit"])
    async def stop(self, ctx):
        '''Stop playing music. Clears your queue if you have anything in it.'''
        try:
            try:
                self.channels_playing_audio.remove(ctx.voice_client.channel.id)
                queuelength = len(self.song_queue[ctx.voice_client.channel.id])
                self.song_queue[ctx.voice_client.channel.id] = []
                self.current_song[ctx.voice_client.channel.id] = []
            except:
                pass
            self.logger.info("reset queue")
            ctx.voice_client.stop()
            await ctx.send(embed=discord.Embed(title=f"\U000023f9 Stopped playing music{'.' if queuelength == 0 else ' and cleared your queue.'}", color=discord.Color.blurple()))
        except AttributeError:
            await ctx.send("I'm not in a voice channel.")

    @commands.command(aliases=["r"])
    async def remove(self, ctx, item:int):
        '''Remove the specified entry from the queue. If you want to clear your queue, use the `clear` command.'''
        try:
            del self.song_queue[ctx.voice_client.channel.id][item-1]
            queuelength = len(self.song_queue[ctx.voice_client.channel.id])
            await ctx.send(f"Successfully removed that entry from your queue. You now have {queuelength} {'songs' if queuelength != 1 else 'song'} in your queue.")
        except AttributeError:
            await ctx.send("I'm not in a voice channel.")
        except IndexError:
            quote = "\'"
            await ctx.send(f"{f'That queue entry doesn{quote}t exist.' if len(self.song_queue[ctx.voice_client.channel.id]) > 0 else f'You don{quote}t have anything in your queue.'}")

    @commands.command(aliases=["d"])
    async def download(self, ctx, *, url=None):
        '''Very similar to `play`, but sends the mp3 file in chat instead of playing it in a voice channel.'''
        if not url:
            return await ctx.send(f"Run this command again and specify something you want to search for. For example, running `{self.bot.command_prefix}download never gonna give you up` will download and send Never Gonna Give You Up in the channel you sent the command in.")
        await ctx.send("Getting that song...")
        async with ctx.typing():
            await self._wait_for_unlock()
            await self.get_song(ctx, url)
            self.logger.info("Uploading file...")
            try:
                await ctx.send("Here's the file:", file=discord.File(self.filename))
            except discord.HTTPException:
                traceback.print_exc()
                await ctx.send("That file is too large. Try specifying a different song.")
            self.is_locked = False
            self.logger.info("Done getting song, unlocked.")

def setup(bot):
    bot.add_cog(music(bot))

def teardown(bot):
    bot.remove_cog(music(bot))
