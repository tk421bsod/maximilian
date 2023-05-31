import asyncio
import contextlib
import functools
import inspect
import logging
from random import randint
import re
import time
import traceback
import typing
import urllib

import aiohttp
import discord
import ffmpeg
import aiomysql
import yt_dlp
from discord.ext import commands

#warning: this uses ffmpeg-python, not ffmpeg (the python module) or python-ffmpeg

class DurationLimitError(discord.ext.commands.CommandError):
    def __init__(self):
        print("Maximum duration was exceeded.")

class NoSearchResultsError(discord.ext.commands.CommandError):
    def __init__(self):
        print("No search results for this song.")

class FileTooLargeError(discord.ext.commands.CommandError):
    pass

class Metadata():
    '''An object that stores metadata about a song.'''
    __slots__ = ("duration", "filename", "id", "name", "thumbnail", "info", "url")

    def __init__(self):
        self.duration = None
        self.filename = None
        self.id = None
        self.name = None
        self.thumbnail = None
        self.info = None
        self.url = None

#TimeConverter from cogs/reminders.py.
class TimeConverter(commands.Converter):
    __slots__ = ("time_regex", "time_dict")
    def __init__(self):
        self.time_regex = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
        self.time_dict = {"h":3600, "s":1, "m":60}

    async def convert(self, ctx, argument):
        matches = self.time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += self.time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument(f"{k} is an invalid unit of time! only h/m/s are valid!")
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number!")
        return time

class CurrentSong(Metadata):
    '''A subclass of Metadata that stores information about the current song.'''
    def __init__(self):
        super().__init__() #add Metadata attrs to this
        self.volume = 0.5
        self.paused_at = 0
        self.start_time = 0
        self.time_paused = 0

class Player():
    '''An object that stores the queue and current song for a specific guild.'''
    __slots__ = ("queue", "current_song", "guild", "owner", "lock", "metadata", "checking")

    def __init__(self, ctx, logger):
        self.queue = []
        self.current_song = []
        self.guild = ctx.guild
        self.owner = ctx.author
        self.lock = asyncio.Lock()
        self.metadata = Metadata()
        self.checking = False
        logger.info(f"Created player for guild id {self.guild.id}")
    

class music(commands.Cog):
    '''Music commands'''
    __slots__ = ("logger", "channels_playing_audio", "lock", "bot", "players", "ydl_opts")

    def __init__(self, bot):
        self.channels_playing_audio = []
        self.logger = logging.getLogger(f"maximilian.{__name__}")
        self.lock = asyncio.Lock()
        self.bot = bot
        self.players = {}
        self.ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'songcache/%(id)s.%(ext)s',
        'quiet': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'no_warnings': True,
        'retries': 20,
        'fragment-retries': 20,
        'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192'
        }]
        }
        self.bot.settings.add_category("music", {'toggle':'music commands', 'performance':'better performance at the cost of audio quality'}, {'toggle':None, 'performance':None}, {'toggle':"manage_guild", 'performance':None})

    async def check_enabled(self, ctx):
        if not self.bot.settings.music.ready:
            await ctx.send(self.bot.strings["SETTING_NOT_READY"])
        while not self.bot.settings.music.ready:
            await asyncio.sleep(0.3)
        return self.bot.settings.music.toggle.enabled(ctx.guild.id)

    async def _get_player(self, ctx):
        '''Gets a player if it exists, creates one if it doesn't exist'''
        if await self._check_player(ctx):
            self.logger.info(f"A player already exists for guild {ctx.guild.id}")
        else:
            self.players[ctx.guild.id] = Player(ctx, self.logger)
        return self.players[ctx.guild.id]

    async def destroy_player(self, ctx):
        '''Destroys (deletes) the player for the specified guild.'''
        try:
            del self.players[ctx.guild.id]
        except:
            self.logger.warning("Tried to destroy a player that doesn't exist!")
        self.logger.info(f"Destroyed the player for guild {ctx.guild.id}")

    async def _check_player(self, ctx):
        '''Returns whether a player exists'''
        try:
            self.players[ctx.guild.id]
        except KeyError:
            return False
        return True

    async def _join_voice(self, ctx, channel):
        '''Joins a voice channel'''
        joiningmessage = await ctx.send(self.bot.strings["JOINING"])
        vc = ctx.voice_client
        if vc:
            if vc.channel.id == channel.id:
                await joiningmessage.edit(content=self.bot.strings["ALREADY_CONNECTED"])
            else:
                try:
                    await vc.move_to(channel)
                except asyncio.TimeoutError:
                    await joiningmessage.edit(content=self.bot.strings["MOVING_TIMEOUT"].format(channel.name))
                    return
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                await joiningmessage.edit(content=self.bot.strings["CONNECTION_TIMEOUT"].format(channel.name))
                return
        self.logger.info("connected to vc")
        title = self.bot.strings["CONNECTED"].format(channel.name) + " "
        if ctx.command.name == "play":
            title += self.bot.strings["GETTING_AUDIO"]
        else:
            title += self.bot.strings["START_PLAYING"]
        await ctx.send(embed=discord.Embed(title=title, color=self.bot.config['theme_color']))

    async def _fade_audio(self, newvolume, ctx):
        '''Smoothly transitions between volume levels'''
        while ctx.voice_client.source.volume != newvolume/100:
            #make volume a double so this doesn't loop infinitely (as volume can be something like 1.000000000004 sometimes)
            ctx.voice_client.source.volume = round(ctx.voice_client.source.volume, 2)
            if newvolume/100 < ctx.voice_client.source.volume:
                ctx.voice_client.source.volume -= 0.01
            elif newvolume/100 > ctx.voice_client.source.volume:
                ctx.voice_client.source.volume += 0.01
            await asyncio.sleep(0.005)

    async def _handle_errors(self, ctx, error):
        '''Handle certain errors (should probably use cog_command_error instead of this)'''
        if isinstance(error, DurationLimitError):
            await ctx.send(self.bot.strings["ERROR_DURATION"])
        elif isinstance(error, NoSearchResultsError):
            await ctx.send(self.bot.strings["ERROR_NO_SEARCH_RESULTS"])
        elif isinstance(error, asyncio.TimeoutError):
            await ctx.send(self.bot.strings["ERROR_TIMEOUT"])
        else:
            try:
                await self.bot.core.send_traceback()
            except discord.HTTPException:
                pass
            await ctx.send(self.bot.strings["GENERIC_ERROR"])
            with contextlib.suppress(AttributeError):
                if ctx.guild.me.voice:
                    await self.leave_voice(ctx, True)
                    await ctx.send(self.bot.strings["ERROR_LEFT_VOICE"])
            await self.bot.core.send_debug(ctx)

    async def leave_voice(self, ctx, silent=False):
        try:
            with contextlib.suppress(AttributeError, IndexError, ValueError):
                self.channels_playing_audio.remove(ctx.voice_client.channel.id)
            await self.destroy_player(ctx)
            await ctx.guild.voice_client.disconnect()
            self.logger.info("left vc, reset queue and destroyed player")
            if not silent:
                await ctx.send(embed=discord.Embed(title=self.bot.strings["LEFT_VOICE"], color=self.bot.config['theme_color']))
        except AssertionError:
            if not silent:
                return await ctx.send(self.bot.strings["NOT_IN_VOICE"])
        except:
            if not silent:
                return await ctx.send(self.bot.strings["FAILED_LEAVING_VOICE"])

    def process_queue(self, ctx, channel, error):
        '''Starts playing the next song in the queue, cleans up some stuff if the queue is empty'''
        #this is a callback that is executed after song ends
        try:
            if channel.id not in self.channels_playing_audio:
                return
            player = self.players[ctx.guild.id]
            if player.current_song[0]:
                #reset duration when repeating
                player.current_song[6], player.current_song[7], player.current_song[8] = time.time(), 0, 0
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(player.current_song[1]), volume=player.current_song[9])
                self.logger.info("repeating song...")
                handle_queue = functools.partial(self.process_queue, ctx, channel)
                ctx.voice_client.play(source, after=handle_queue)
            else:
                self.logger.info("playing next song in queue...")
                #start playing before doing anything else
                volume = player.current_song[9]
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(player.queue[0][0]), volume=volume)
                handle_queue = functools.partial(self.process_queue, ctx, channel)
                ctx.voice_client.play(source, after=handle_queue)
                queuelength = len(player.queue)-1
                newsong = player.queue[0]
                #update current_song with info about the new song
                player.current_song = [False, newsong[0], newsong[3], newsong[1], newsong[4], newsong[2], time.time(), 0, 0, volume]
                player.queue.remove(player.queue[0])
                #build now playing embed, send it
                embed = discord.Embed(title=self.bot.strings["NOW_PLAYING_TITLE"], description=f"`{newsong[1]}`", color=self.bot.config['theme_color'])
                embed.add_field(name=self.bot.strings["VIDEO_URL"], value=f"<{newsong[2]}>", inline=True)
                embed.add_field(name=self.bot.strings["DURATION"], value=f"{newsong[3]}")
                embed.set_footer(text=self.bot.strings["NOW_PLAYING_FOOTER"].format(queuelength))
                embed.set_image(url=f"{newsong[4]}")
                coro = ctx.send(embed=embed)
                fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                fut.result()
            return True
        except IndexError:
            self.logger.info("done with queue!")
            #remove channel from channels_playing_audio, reset info about current song, blank queue
            try:
                self.channels_playing_audio.remove(channel.id)
                player.current_song = []
                player.queue = []
            except:
                pass
            return False

    async def get_song_from_cache(self, ctx, url, ydl_opts, player):
        '''Attempts to find an mp3 matching the video id locally, downloading the video if that file isn't found. This prioritizes speed, checking if a song is saved locally before downloading it from Youtube.'''
        self.logger.info("getting song from cache")
        #get video id from parameters, try to open mp3 file matching that id (if that file exists, play it instead of downloading it)
        if "youtu.be" in url:
            video = url.split("/")[3]
            print(video)
        elif "youtube.com" in url:
            url_data = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(url_data.query)
            video = query["v"][0]
        else:
            #function doesn't take user input, so it's safe to assume the url is an id
            video = url 
        try:
            open(f"songcache/{video}.mp3", "r")
            #check if video id is in database, add it if it isn't
            data = await self.bot.db.exec("select * from songs where id = %s limit 1", (video))
            if data:
                data = data[0]
                player.metadata.name = data['name']
                player.metadata.filename = f"songcache/{video}.mp3"
                player.metadata.duration = data['duration']
                player.metadata.thumbnail = data['thumbnail']
                player.metadata.url = f"https://youtube.com/watch?v={video}"
            else:
                with yt_dlp.YoutubeDL(self.ydl_opts) as youtubedl:
                    info = youtubedl.sanitize_info(await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=False)))
                    player.metadata.url = f"https://youtube.com/watch?v={video}"
                    player.metadata.name = info["title"]
                    player.metadata.filename = f"songcache/{video}.mp3"
                    player.metadata.thumbnail = info["thumbnail"]
                    if info['duration'] == 0.0 or info['duration'] == self.bot.strings["STREAM_DURATION"]:
                        self.logger.info("this video is a stream")
                        self.filename = info["url"]
                        self.duration = self.bot.strings["STREAM_DURATION"]
                    else:
                        m, s = divmod(info["duration"], 60)
                        self.duration = f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}"
                        if m > 60 and ctx.author.id != self.bot.owner_id:
                            raise DurationLimitError()
                    await self.bot.db.exec("insert into songs values(%s, %s, %s, %s)", (player.metadata.name, video, player.metadata.duration, player.metadata.thumbnail))
            self.logger.info("got song from cache!")
        except FileNotFoundError:
            self.logger.info("song isn't in cache")
            async with ctx.typing():
                with yt_dlp.YoutubeDL(self.ydl_opts) as youtubedl:
                    #the self.bot.loop.run_in_executor is to prevent the extract_info call from blocking other stuff
                    info = youtubedl.sanitize_info(await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=False)))
                    #get name of file we're going to play, for some reason prepare_filename
                    #doesn't return the correct file extension
                    player.metadata.name = info["title"]
                    player.metadata.thumbnail = info["thumbnail"]
                    player.metadata.url = f"https://youtube.com/watch?v={video}"
                    #if duration is 0, we got a stream, don't put that in the database/download it
                    if info['duration'] == 0.0:
                        self.logger.info("this video is a stream")
                        player.metadata.filename = info["url"]
                        player.metadata.duration = "No duration available (this is a stream)"
                        return
                    performance = self.bot.settings.music.performance.enabled(ctx.guild.id)
                    info = None
                    if performance and ctx.command:
                        if ctx.command.name != "download":
                            info = youtubedl.sanitize_info(await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=False)))
                    if not info:
                        info = youtubedl.sanitize_info(await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=True)))
                    m, s = divmod(info["duration"], 60)
                    player.metadata.duration = f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}"
                    if m > 60 and ctx.author.id != self.bot.owner_id:
                        raise DurationLimitError()
                    player.metadata.filename = None
                    if performance and ctx.command:
                        if ctx.command.name != "download":
                            player.metadata.filename = info["formats"][0]["url"]
                    if not player.metadata.filename:
                        player.metadata.filename = youtubedl.prepare_filename(info).replace(youtubedl.prepare_filename(info).split(".")[1], "mp3")
                        try:
                            await self.bot.db.exec("insert into songs values(%s, %s, %s, %s)", (player.metadata.name, video, player.metadata.duration, player.metadata.thumbnail))
                        except aiomysql.IntegrityError:
                            pass
        except Exception as e:
            traceback.print_exc()
            raise e
        return

    async def search_youtube_for_song(self, ydl, ctx, url, num, player):
        '''Searches Youtube for a song and extracts metadata from the first search result. If the maximum duration is exceeded, it goes to the next search result, up to 4 times. If no more search results are available, it raises NoSearchResultsError'''
        if num == 0:
            player.metadata.info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch5:{url}", download=False))
        try:
            player.metadata.id = player.metadata.info["entries"][num]["id"]
            player.metadata.name = player.metadata.info["entries"][num]["title"]
            m, s = divmod(player.metadata.info["entries"][num]["duration"], 60)
            player.metadata.duration = f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}"
            player.metadata.thumbnail = player.metadata.info["entries"][num]["thumbnail"]
        #if we've gone through 5 search results already or there weren't any, raise NoSearchResultsError
        except IndexError:
            self.logger.info(player.metadata.info["entries"])
            raise NoSearchResultsError()
        except:
            traceback.print_exc()
        #check if max duration (60 minutes) exceeded
        if m > 60:
            self.logger.warning(f"Max duration exceeded on search result {num+1}. Retrying...")
            #if so, recursively call this function, going to the next search result
            await self.search_youtube_for_song(ydl, ctx, url, num+1, player)

    async def test_url(self, url, player):
        player.checking = True
        async with aiohttp.ClientSession() as cs:
            await cs.get(url)
        player.checking = False

    async def _wait(self, player, task):
        elapsed = 0.0
        sent_1 = False
        self.logger.info("Waiting for test_url to start...")
        while not player.checking:
            await asyncio.sleep(0.005)
        self.logger.info("Waiting for test_url to finish...")
        while player.checking:
            await asyncio.sleep(0.1)
            elapsed = elapsed + 0.1
            if elapsed >= 5.0 and not sent_1:
                self.logger.warn("test_url hasn't returned for 5 seconds! It will be canceled if it doesn't exit within 10 seconds.")
                sent_1 = True
            elif elapsed >= 10.0:
                self.logger.error("test_url has hung for 10 or more seconds! Canceling it.")
                try:
                    task.cancel()
                except:
                    pass
                player.checking = False
                raise asyncio.TimeoutError()
        self.logger.info("player.checking is false, assuming test_url has exited.")
        self.logger.info(f"elapsed time: {elapsed} seconds")

    async def get_song(self, ctx, url, player):
        '''Gets the filename, id, and other metadata of a song. This tries to look up a song in the database first, then it searches Youtube if that fails.'''
        self.logger.info("Locked execution.")
        async with ctx.typing():
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                self.logger.info("looking for song in db...")
                info = await self.bot.db.exec("select * from songs where name like %s", (f"%{url}%", ))
                if info:
                    info = info[0]
                    self.logger.info("found song in db! trying to get from cache...")
                    player.metadata.id = info["id"]
                    player.metadata.name = info["name"]
                    if int(str(info['duration']).split(':')[0]) > 60:
                        raise DurationLimitError()
                else:
                    try:
                        #check if we've been provided a valid url
                        task = asyncio.create_task(self.test_url(url, player))
                        await self._wait(player, task)
                    except Exception:
                        #not found and not a valid url? search youtube
                        self.logger.info("searching youtube...")
                        await self.search_youtube_for_song(ydl, ctx, url, 0, player)
            url = player.metadata.id if player.metadata.id else url
            await self.get_song_from_cache(ctx, url, self.ydl_opts, player)

    
    #executes when someone sends a message with the prefix followed by 'play'
    @commands.command(aliases=["p"], help=f"Play something from youtube. You need to provide a valid Youtube URL or a search term for this to work. For example, you can use `<prefix>play never gonna give you up` to search youtube for a song named 'never gonna give you up' and rickroll all of your friends in the voice channel.")
    async def play(self, ctx, *, url=None):
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        if not url:
            await ctx.send("You need to specify a url or something to search for.")
            return
        if self.bot.settings.music.performance.enabled(ctx.guild.id):
            await ctx.send(self.bot.strings["PERFORMANCE_MODE_ENABLED"].format(await self.bot.get_prefix(ctx.message)))
        elif randint(1, 30) == 3:
            await ctx.send(self.bot.strings["PERFORMANCE_MODE_REMINDER"].format(await self.bot.get_prefix(ctx.message)))
            await asyncio.sleep(0.2)
        #init player for this guild if it doesn't exist
        player = await self._get_player(ctx)
        #attempt to join the vc that the command's invoker is in...
        try:
            channel = ctx.author.voice.channel
            #don't join vc if we're already playing (or fetching) audio
            if channel.id not in self.channels_playing_audio:
                self.channels_playing_audio.append(channel.id)
            else:
                #if we're already playing (or fetching) audio, add song to queue
                await ctx.send("Adding to your queue...")
                #show warning if repeating song
                try:
                    if player.current_song[0] == True:
                        await ctx.send(self.bot.strings["WARNING_REPEATING"].format(await self.bot.get_prefix(ctx.message), await self.bot.get_prefix(ctx.message)))
                    elif player.current_song[2] == self.bot.strings["STREAM_DURATION"]:
                        await ctx.send(self.bot.strings["WARNING_STREAM"].format(await self.bot.get_prefix(ctx.message)))
                except (KeyError, IndexError):
                    #if there's a keyerror or indexerror, nothing's playing. this is normal if someone adds stuff to queue rapidly, so ignore it
                    pass
                async with player.lock:
                    try:
                        async with ctx.typing():
                            await self.get_song(ctx, url, player)
                    except AttributeError:
                        #might not be in a voice channel, so check player
                        if not await self._check_player(ctx):
                            return self.logger.info('Player was destroyed while getting song!')
                    except Exception as e:
                        await self._handle_errors(ctx, e)
                        return
                    #actually add that stuff to queue
                    player.queue.append([player.metadata.filename, player.metadata.name, player.metadata.url, player.metadata.duration, player.metadata.thumbnail])
                    await ctx.send(embed=discord.Embed(title=self.bot.strings["SONG_ADDED"], color=self.bot.config['theme_color']).add_field(name=self.bot.strings["SONG_NAME"], value=f"`{player.metadata.name}`", inline=False).add_field(name=self.bot.strings["VIDEO_URL"], value=f"<{player.metadata.url}>", inline=True).set_footer(text=self.bot.strings["ADDED_TO_QUEUE"].format(len(player.queue), await self.bot.get_prefix(ctx.message))).add_field(name=self.bot.strings["DURATION"], value=player.metadata.duration, inline=True).set_image(url=player.metadata.thumbnail))
                    #unlock after sending message
                    self.logger.info("Added song to queue, unlocked.")
                    return
        except AttributeError:
            traceback.print_exc()
            await ctx.send(self.bot.strings["USER_NOT_IN_VOICE"])
            return
        await self._join_voice(ctx, channel)
        #after connecting, download audio from youtube (try to get it from cache first to speed things up and save bandwidth)
        #a lock is used to stop metadata from being overwritten until it's no longer needed
        async with player.lock:
            try:
                async with ctx.typing():
                    await self.get_song(ctx, url, player)
            except AttributeError:
                #might not be in a voice channel, so check player
                if not await self._check_player(ctx):
                    return self.logger.info('Player was destroyed while getting song!')
            except Exception as e:
                await self._handle_errors(ctx, e)
                return
            try:
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(player.metadata.filename), volume=0.5)
            except Exception:
                await self.leave_voice(ctx)
                await ctx.send(self.bot.strings["UNEXPECTED_ERROR"])
                await self.bot.core.send_debug(ctx)
            try:
                ctx.voice_client.stop()
            except:
                pass
            #check if player exists, if it doesn't, that's a problem
            #we could have left the voice channel before starting to play stuff, just exit
            if not await self._check_player(ctx):
                return self.logger.info('Player was destroyed while getting song!')
            #current_song is a bunch of information about the current song that's playing.
            #that information in order:
            #0: Is this song supposed to repeat?, 1: Filename, 2: Duration (already in the m:s format), 3: Video title,  4: Thumbnail URL, 5: Video URL, 6: time the song started (now), 7: Time when paused, 8: Total time paused, 9: Volume
            player.current_song = [False, player.metadata.filename, player.metadata.duration, player.metadata.name, player.metadata.thumbnail, player.metadata.url, time.time(), 0, 0, 0.5]
            embed = discord.Embed(title="Now playing:", description=f"`{player.metadata.name}`", color=self.bot.config['theme_color'])
            embed.add_field(name="Video URL", value=f"<{player.metadata.url}>", inline=True)
            embed.add_field(name="Total Duration", value=f"{player.metadata.duration}")
            queuelength = len(player.queue)
            embed.set_footer(text=f"You have {queuelength} {'song' if queuelength == 1 else 'songs'} in your queue. \nUse the play command to add {'more songs or use the clear command to clear it.' if queuelength != 0 else 'songs to it.'}")
            embed.set_image(url=player.metadata.thumbnail)
            await ctx.send(embed=embed)
            self.logger.info("Done getting song, unlocked.")
        self.logger.info("playing audio...")
        #then play the audio
        #we can't pass stuff to process_queue in after, so pass some stuff to it before executing it
        handle_queue = functools.partial(self.process_queue, ctx, channel)
        try:
            ctx.voice_client.play(source, after=handle_queue)
        except AttributeError:
            #might not be in a voice channel, so check player
            if not await self._check_player(ctx):
                return self.logger.info('Player was destroyed while getting song!')

    @commands.command(aliases=["l"])
    async def leave(self, ctx):
        '''Leaves the current voice channel.'''
        await self.leave_voice(ctx)
    
    @commands.command(aliases=["q"])
    async def queue(self, ctx):
        '''View what's in your queue.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try:
            queuelength = len(player.queue)
            if queuelength != 0:
                m, s = 0, 0
                #get total duration, could probably clean this up a bit
                for i in player.queue:
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
                m = f"{0 if len(str(m%60)) == 1 else ''}{m%60}"
                newline = "\n" #evil hack for using newlines in fstrings
                #the following statement is really long and hard to read, not sure whether to split into multiple lines or not
                #show user's queue, change how it's displayed depending on how many songs are in the queue
                try:
                    await ctx.send(f"You have {queuelength} {'song in your queue: ' if queuelength == 1 else 'songs in your queue. '}\n{f'Your queue: {newline}' if queuelength != 1 else ''}{f'{newline}'.join([f'{count+1}: `{i[1]}`(<{i[2]}>) Duration: {i[3]}' for count, i in enumerate(player.queue)])}\n{f'Total duration: {h}{m}:{s}' if queuelength != 1 and f'{h}{m}:{s}' != '0:0' else ''}\nUse `{await self.bot.get_prefix(ctx.message)}remove <song's position>` to remove a song from your queue. For example, `{await self.bot.get_prefix(ctx.message)}remove 1` removes the first item in the queue.\nYou can add items to your queue by using the `play` command again while a song is playing. If you want to clear your queue, use the `clear` command.") 
                except discord.HTTPException:
                    await ctx.send(f"You have {queuelength} {'song in your queue: ' if queuelength == 1 else 'songs in your queue. '}\nYour queue is too long to display, so I'm only showing the first 10 songs in it.\n {f'Your queue: {newline}' if queuelength != 1 else ''}{f'{newline}'.join([f'{count+1}: `{i[1]}`(<{i[2]}>) Duration: {i[3]}' for count, i in enumerate(player.queue[:10])])}\n{f'Total duration: {h}{m}:{s}' if queuelength != 1 and f'{h}{m}:{s}' != '0:0' else ''}\nUse `{await self.bot.get_prefix(ctx.message)}remove <song's position>` to remove a song from your queue. For example, `{await self.bot.get_prefix(ctx.message)}remove 1` removes the first item in the queue.\nYou can add items to your queue by using the `play` command again while a song is playing. If you want to clear your queue, use the `clear` command.")
            else:
                await ctx.send("You don't have anything in your queue.")
        except (IndexError, AttributeError):
            traceback.print_exc()
            await ctx.send("You don't have anything in your queue.")

    @commands.command(aliases=["s"])
    async def skip(self, ctx):
        '''Skip the current song.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try:
            assert player.queue != []
            await ctx.send(embed=discord.Embed(title="\U000023e9 Skipping to the next song in the queue... ", color=self.bot.config['theme_color']))
            player.current_song[0] = False
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
        '''Pause the current song.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try:
            assert ctx.guild.me.voice != None
            if ctx.voice_client.is_playing():
                ctx.voice_client.pause()
                player.current_song[7] = time.time()
                await ctx.send(embed=discord.Embed(title=f"\U000023f8 Paused. Run `{await self.bot.get_prefix(ctx.message)}resume` to resume audio, or run `{await self.bot.get_prefix(ctx.message)}leave` to make me leave the voice channel.", color=self.bot.config['theme_color']))
            elif ctx.voice_client.is_paused():
                await ctx.send(embed=discord.Embed(title=f"\U0000274e I'm already paused. Use `{await self.bot.get_prefix(ctx.message)}resume` to resume.", color=self.bot.config['theme_color']))
            else:
                await ctx.send(embed=discord.Embed(title="\U0000274e I'm not playing anything.", color=self.bot.config['theme_color']))
        except Exception:
            traceback.print_exc()
            await ctx.send("I'm not in a voice channel.")

    @commands.command(aliases=["unpause"])
    async def resume(self, ctx):
        '''Resume the current song.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try:
            assert ctx.guild.me.voice != None
            if ctx.voice_client.is_paused():
                player.current_song[8] += round(time.time() - player.current_song[7])
                await ctx.send(embed=discord.Embed(title="\U000025b6 Resuming...", color=self.bot.config['theme_color']))
                ctx.voice_client.resume()
                return
            elif ctx.voice_client.is_playing():
                await ctx.send(embed=discord.Embed(title="\U0000274e I'm already playing something.", color=self.bot.config['theme_color']))
            else:
                await ctx.send(embed=discord.Embed(title="\U0000274e I'm not playing anything.", color=self.bot.config['theme_color']))
        except Exception:
            traceback.print_exc()
            await ctx.send("I'm not in a voice channel.")
       
    @commands.command(aliases=["v"])
    async def volume(self, ctx, newvolume : typing.Optional[str]=None):
        '''Set the volume of audio to the provided percentage. The default volume is 50%.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try:
            ctx.voice_client.source
            if newvolume == None:
                await ctx.send(f"Volume is currently set to {int(player.current_song[9]*100)}%.")
                return
            newvolume = int(newvolume.replace("%", ""))
            if newvolume > 100 or newvolume < 0:
                await ctx.send("You need to specify a volume percentage between 0 and 100.")
            elif newvolume/100 == ctx.voice_client.source.volume:
                await ctx.send(f"Volume is already set to {newvolume}%.")
            else:
                await self._fade_audio(newvolume, ctx)
                player.current_song[9] = newvolume/100
                await ctx.send(embed=discord.Embed(title=f"\U00002705 Set volume to {newvolume}%.{' Warning: Music may sound distorted at this volume level.' if newvolume >= 90 else ''}", color=self.bot.config['theme_color']))
        except ValueError:
            try:
                float(newvolume)
                return await ctx.send("You can't specify a decimal for the volume.")
            except:
                return await ctx.send("You can't specify a word for the volume.")
        except AttributeError:
            traceback.print_exc()
            if player.lock.locked():
                return await ctx.send("I can't change the volume if I'm not playing something.")
            await ctx.send("I'm not in a voice channel.")

    @commands.command()
    async def seek(self, ctx, to:TimeConverter):
        pass

    @commands.command(aliases=["c"])
    async def clear(self, ctx):
        '''Clear the queue.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try:
            assert player.queue != []
            player.queue = []
            await ctx.send(embed=discord.Embed(title="\U00002705 Cleared your queue!", color=self.bot.config['theme_color']))
        except AssertionError:
            await ctx.send("You don't have anything in your queue.")
        except Exception:
            await ctx.send("I'm not in a voice channel.")

    @commands.command(aliases=["loop", "lo"])
    async def repeat(self, ctx):
        '''Toggle repeating the current song.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try: 
            if ctx.voice_client.is_playing() and player.current_song[2] != "No duration available (this is a stream)":
                if player.current_song[0]:
                    player.current_song[0] = False
                    await ctx.send(embed=discord.Embed(title="I won't repeat the current song anymore.", color=self.bot.config['theme_color']))
                else:
                    player.current_song[0] = True
                    await ctx.send(embed=discord.Embed(title="\U0001f501 I'll repeat the current song after it finishes. Run this command again to stop repeating the current song.", color=self.bot.config['theme_color']))
            elif player.current_song[2] == "No duration available (this is a stream)":
                await ctx.send(embed=discord.Embed(title="\U0000274e I can't repeat streams.", color=self.bot.config['theme_color']))
            else:
                await ctx.send(embed=discord.Embed(title="\U0000274e I'm not playing anything right now.", color=self.bot.config['theme_color']))
        except AttributeError:
            await ctx.send(embed=discord.Embed(title="\U0000274e I'm not playing anything right now.", color=self.bot.config['theme_color']))
        except IndexError:
            await ctx.send("I'm not in a voice channel.")

    @commands.command(aliases=["cs", "np", "song", "currentsong", "currentlyplaying", "cp"])
    async def nowplaying(self, ctx):
        '''Show the song that's currently playing.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try:
            if ctx.voice_client.is_playing():
                #get elapsed duration, make it human-readable
                m, s = divmod(round((time.time() - player.current_song[6]) - player.current_song[8]), 60)
            elif ctx.voice_client.is_paused():
                m, s = divmod(round((player.current_song[7] - player.current_song[6]) - player.current_song[8]), 60)
            else:
                return await ctx.send(embed=discord.Embed(title="\U0000274e I'm not playing anything right now.", color=self.bot.config['theme_color']))
            embed = discord.Embed(title="Currently playing:", description=f"`{player.current_song[3]}`", color=self.bot.config['theme_color'])
            embed.add_field(name="Video URL", value=f"<{player.current_song[5]}>", inline=True)
            if player.current_song[2] == "No duration available (this is a stream)":
                embed.add_field(name="Duration (Elapsed/Total)", value=f"You've been listening to this stream for {m} minutes and {s} seconds.")
            else:
                embed.add_field(name="Duration (Elapsed/Total)", value=f"{m}:{0 if len(list(str(s))) == 1 else ''}{s}/{player.current_song[2]}")
            embed.set_image(url=player.current_song[4])
            await ctx.send(embed=embed)
        except AttributeError:
            await ctx.send(embed=discord.Embed(title="\U0000274e I'm not in a voice channel.", color=self.bot.config['theme_color']))

    @commands.command(aliases=["quit"])
    async def stop(self, ctx):
        '''Stop playing music. Clears your queue if you have anything in it. '''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        if not await self._check_player(ctx):
            return await ctx.send("It doesn't look like I'm in a voice channel.")
        if not ctx.voice_client.is_playing():
            return await ctx.send("I'm not playing anything right now.")
        player = await self._get_player(ctx)
        try:
            try:
                queuelength = len(player.queue)
                player.queue = []
                player.current_song = []
                self.channels_playing_audio.remove(ctx.voice_client.channel.id)
            except:
                pass
            await self.destroy_player(ctx)
            self.logger.info("reset queue")
            ctx.voice_client.stop()
            await ctx.send(embed=discord.Embed(title=f"\U000023f9 Stopped playing music{'.' if queuelength == 0 else ' and cleared your queue.'}", color=self.bot.config['theme_color']))
        except AttributeError:
            await ctx.send("I'm not in a voice channel.")

    @commands.command(aliases=["r"])
    async def remove(self, ctx, item:int):
        '''Remove the specified thing from the queue. If you want to clear your queue, use the `clear` command.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try:
            del player.queue[item-1]
            queuelength = len(player.queue)
            await ctx.send(f"Successfully removed that from your queue. You now have {queuelength} {'songs' if queuelength != 1 else 'song'} in your queue.")
        except AttributeError:
            await ctx.send("I'm not in a voice channel.")
        except IndexError:
            quote = "\'"
            await ctx.send(f"{f'That{quote}s not in your queue!' if len(player.queue) > 0 else f'You don{quote}t have anything in your queue.'}")

    @commands.command(aliases=["d"])
    async def download(self, ctx, *, url=None):
        '''Very similar to `play`, but sends the mp3 file in chat instead of playing it in a voice channel.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        if not url:
            return await ctx.send(f"Run this command again and specify something you want to search for. For example, running `{await self.bot.get_prefix(ctx.message)}download never gonna give you up` will download and send Never Gonna Give You Up in the channel you sent the command in.")
        player = await self._get_player(ctx)
        await ctx.send("Getting that song...")
        async with player.lock:
            async with ctx.typing():
                try:
                    await self.get_song(ctx, url, player)
                except Exception as e:
                    return await self._handle_errors(ctx, e)
                if player.metadata.duration == "0:0":
                    return await ctx.send("I can't download streams.")
                self.logger.info("Uploading file...")
                try:
                    await ctx.send("Here's the file:", file=discord.File(player.metadata.filename))
                except (discord.HTTPException, TimeoutError):
                    traceback.print_exc()
                    await ctx.send("I couldn't upload that file because it's too large. I'll reduce the quality (reduction in quality varies with song length) and try to send it again.")
                    try:
                        async with ctx.typing():
                            await ctx.send("Reducing quality...")
                            #parse total seconds from duration value 
                            s = 60*int(player.metadata.duration.split(":")[0])+int(player.metadata.duration.split(":")[1])
                            for i in range(320, 1, -1):
                                #check if the output file size (bitrate*seconds) in kilobytes (8 bits = 1 byte, so divide by 8)
                                #is less than the upload limit (8mb or 8000kb)
                                if ((i)*s)/8 <= 7500:
                                    self.logger.info(f"Suitable bitrate found. Transcoding to {i} kbps...")
                                    #if so, transcode to that bitrate
                                    inputfile = ffmpeg.input(player.metadata.filename)
                                    output = functools.partial(ffmpeg.output, inputfile, f"{player.metadata.filename[:-4]}temp.mp3", audio_bitrate=f"{i}k")
                                    stream = await self.bot.loop.run_in_executor(None, output)
                                    run = functools.partial(ffmpeg.run, stream, quiet=True, overwrite_output=True)
                                    await self.bot.loop.run_in_executor(None, run)
                                    await ctx.send(f"Here's the file (at {i} kbps):", file=discord.File(f"{player.metadata.filename[:-4]}temp.mp3"))
                                    self.logger.info("Done getting song, unlocked.")
                                    return
                            #if we didn't return yet, the file's too large 
                            raise FileTooLargeError
                    except (discord.HTTPException, FileTooLargeError):
                        await ctx.send("<:blobpain:822921526629236797> I couldn't upload a lower quality version. Try choosing a shorter song.")
                self.logger.info("Done getting song, unlocked.")

    @commands.command(aliases=["j"])
    async def join(self, ctx):
        '''Make Maximilian join the voice channel you're in.'''
        if not await self.check_enabled(ctx):
            return await ctx.send("Sorry, music commands are disabled in this server. Ask a moderator to enable them through `<prefix> config music toggle`.\nIf I'm playing something, you can still use `<prefix> leave`.\nIf you just added me, music features are disabled by default.")
        player = await self._get_player(ctx)
        try:
            await self._join_voice(ctx, ctx.author.voice.channel)
        except AttributeError:
            await ctx.send("You're not in a voice channel. Join one, then run this command again.")

async def setup(bot):
    await bot.add_cog(music(bot))

async def teardown(bot):
    await bot.remove_cog(music(bot))
