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

class music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = {}
        self.channels_playing_audio = []

    def process_queue(self, error):
        #this is a callback that is executed after song ends
        try:
            #this variable could change as we're executing the stuff below, so create (and use) a local variable just in case
            ctx = self.ctx
            channel = self.channel
            print(self.song_queue[channel.id][0])
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.song_queue[channel.id][0][0]), volume=0.5)
            coro = ctx.send(f"{self.ctx.author.mention} Playing `{self.song_queue[channel.id][0][1]}`... ({self.song_queue[channel.id][0][2]})")
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            fut.result()
            self.song_queue[channel.id].remove(self.song_queue[channel.id][0])
            ctx.voice_client.play(source, after=self.process_queue)
        except IndexError:
            self.channels_playing_audio.remove(channel.id)
            self.song_queue[channel.id] = None

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
            open(f"{video}.mp3", "r")
            #check if video id is in database, add it if it isn't
            info = self.bot.dbinst.retrieve(self.bot.database, "songs", "name", "id", f"{video}", False)
            print(info)
            if info != None:
                self.name = info
                self.filename = f"{video}.mp3"
                self.url = f"https://youtube.com/watch?v={video}"
            else:
                with youtube_dl.YoutubeDL(ydl_opts) as youtubedl:
                    info = await self.bot.loop.run_in_executor(None, lambda: youtubedl.extract_info(f"https://youtube.com/watch?v={video}", download=False))
                    self.url = f"https://youtube.com/watch?v={video}"
                    self.name = info["title"]
                    self.filename = f"{video}.mp3"
                    if self.bot.dbinst.insert(self.bot.database, "songs", {"name":self.name, "id":video}, "id") != "success":
                        self.bot.dbinst.delete(self.bot.database, "songs", self.video, "id")
                        self.bot.dbinst.insert(self.bot.database, "songs", {"name":self.name, "id":video}, "id")
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
                    self.filename = youtubedl.prepare_filename(info).replace(youtubedl.prepare_filename(info).split(".")[1], "mp3")
                    self.bot.dbinst.insert(self.bot.database, "songs", {"name":self.name, "id":video}, "id", False, None, False, None, False)
        return

    async def get_song(self, ctx, url):
        ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(id)s.%(ext)s',
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
                        #search youtube, get first result, check cache,  download file if it's not in cache
                        print("searching youtube...")
                        info = self.bot.dbinst.exec_safe_query(self.bot.database, "select * from songs where name like %s", (url))
                        print(info)
                        if info != None and info.strip() != "()":
                            id = info["id"]
                            self.name = info["name"]
                        else:
                            info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch:{url}", download=False))
                            id = info["entries"][0]["id"]
                            self.name = info["entries"][0]["title"]
                        await self.get_song_from_cache(ctx, id, ydl_opts)
                else:
                    #if the url is valid, don't try to search youtube, just get it from cache
                    await self.get_song_from_cache(ctx, url, ydl_opts)
            except Exception:
                traceback.print_exc()
                await ctx.send("There was an error. Make sure you provided a valid Youtube URL or a valid search term. The Youtube URL you provide must be prefixed by `http://` or `https://`, and be in the form `youtube.com/watch?v=xxxxxxx` or `youtu.be/xxxxxxx`.")
                return

    @commands.command(hidden=True, aliases=["s"])
    async def skip(self, ctx):
        raise NotImplementedError

    @commands.command(aliases=["p"])
    async def play(self, ctx, *, url=None):
        '''Play something from youtube. You need to provide a valid Youtube URL or a search term for this to work.'''
        if url == None:
            await ctx.send("You need to specify a url or something to search for.")
            return
        #attempt to join the vc that the command's invoker is in...
        try:
            self.channel = ctx.author.voice.channel
            try:
                self.song_queue[self.channel.id]
            except KeyError:
                self.song_queue[self.channel.id] = []
            #...unless we're already playing (or fetching) audio
            if self.channel.id not in self.channels_playing_audio:
                self.channels_playing_audio.append(self.channel.id)
                await ctx.send("Attempting to join the voice channel you're in...")
            else:
                #if we're already playing (or fetching) audio, add song to queue
                await ctx.send("Adding to your queue...")
                await self.get_song(ctx, url)
                print(self.song_queue[self.channel.id])
                self.song_queue[self.channel.id].append([self.filename, self.name, self.url])
                print(self.song_queue[self.channel.id])
                await ctx.send(f"Added `{self.name}` to your queue! ({self.url}) Currently, you have {len(self.song_queue[self.channel.id])} songs in your queue.")
                return
        except AttributeError:
            await ctx.send("You aren't in a voice channel. Join one, then run this command again.")
            return
        except Exception:
            traceback.print_exc()
        vc = ctx.voice_client
        if vc:
            if vc.channel.id == self.channel.id:
                await ctx.send(f"I'm already in your voice channel, so I won't reconnect.")
                pass
            try:
                await vc.move_to(self.channel)
            except asyncio.TimeoutError:
                await ctx.send(f'Moving to the `{self.channel}` voice channel timed out.')
                return
        else:
            try:
                await self.channel.connect()
            except asyncio.TimeoutError:
                await ctx.send(f'Connecting to the `{self.channel}` voice channel timed out.')
                return
        print("connected to vc")
        await ctx.send(f'Connected to the `{self.channel}` voice channel. Getting audio... (this may take a while for long songs)')
        #after connecting, download audio from youtube (try to get it from cache first to speed things up and save bandwidth)
        await self.get_song(ctx, url)
        self.ctx = ctx
        print("playing audio...")
        try:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.filename), volume=0.5)
        except Exception:
            await ctx.send("I've encountered an error. Either something went seriously wrong or you entered a search term with no results. Try running the command again. If you see this message again (after entering a more broad search term), contact tk421#7244. ")
            return
        await ctx.send(f"{ctx.author.mention} Playing `{self.name}`... ({self.url})")
        #then play the audio
        ctx.voice_client.play(source, after=self.process_queue)

    @commands.command(aliases=["l"])
    async def leave(self, ctx):
        '''Leaves the current voice channel.'''
        try:
            self.channels_playing_audio.remove(ctx.voice_client.channel.id)
            await ctx.voice_client.move_to(None)
            self.ctx = ctx
            self.song_queue[self.channel.id] == []
            await ctx.send("Left the voice channel.")
        except:
            await ctx.send("I'm not in a voice channel.")
    
    @commands.command(hidden=True, aliases=["q"])
    async def queue(self, ctx):
        await ctx.send("You can't see what's in your queue yet, I'm working on it.")

def setup(bot):
    bot.add_cog(music(bot))

def teardown(bot):
    bot.remove_cog(music(bot))