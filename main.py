import asyncio
import os
import discord
from discord.ext import commands
import logging
import youtube_dl
import ffmpeg
import sys
from async_timeout import timeout

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

client = commands.Bot(command_prefix="!")

playlist = []
song_counter = 0
loop_counter = 0
ydl_ops = {'format': '249/250/25'}
players = {}
loop = False


class MusicPlayer:
    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.voice_client
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        print('loop start')
        await self.bot.wait_until_ready()
        print('ready')
        while not self.bot.is_closed():
            self.next.clear()

            print('open')

            try: # wait for a song to enter the queue and play it, else disconnect after 5 minutes
                async with timeout(3000):  # 5 min
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                await self._channel.disconnect()
                #return self.destroy(self._guild)

            print('playing')

            self._guild.voice_client.play(discord.FFmpegOpusAudio(
                executable='C:/Users/ROBMC/Downloads/ffmpeg-2021-09-11-git-3e127b595a-full_build/bin/ffmpeg.exe',
                source=source), after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            print('song playing')
            await self.next.wait()
            print('song done')

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        #return await self._channel.disconnect()
        return self.bot.loop.create_task(self.cleanup(guild))


@client.command()
async def play(ctx, *, search: str):
    global playlist
    global loop
    song_name = ''

    for file in os.listdir("./"):
        if file.endswith(".webm"):
            if not file in playlist:
                try:
                    os.remove(file)
                except PermissionError:
                    pass

    voice_channel = ctx.author.voice.channel

    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice is None:
        await voice_channel.connect()

    with youtube_dl.YoutubeDL(ydl_ops) as ydl:
        ydl.extract_info(f"ytsearch:{search}", download=True)['entries'][0]

    for file in os.listdir("./"):
        if file.endswith(".webm"):
            if not file in playlist:
                global song_counter
                song_name = "song" + str(song_counter) + ".webm"
                os.rename(file, song_name)
                playlist.append(song_name)
                song_counter += 1

    player = get_player(ctx)
    await player.queue.put(song_name)


def get_player(ctx):
    """Retrieve the guild player, or generate one."""
    try:
        player = players[ctx.guild.id]
    except KeyError:
        player = MusicPlayer(ctx)
        players[ctx.guild.id] = player

    return player


@client.command()
async def leave(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    voice_channel = discord.utils.get(ctx.guild.voice_channels, name='General')
    if voice.is_connected():
        ctx.send("Well! I know where I'm not wanted")
        await voice_channel.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")


@client.command()
async def pause(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
    else:
        await ctx.send("The bot is not playing any audio.")


@client.command()
async def resume(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        voice.resume()
    else:
        await ctx.send("The bot is not paused.")


@client.command()
async def stop(ctx):
    global playlist
    playlist.clear()
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    voice.stop()


@client.command()
async def commands(ctx):
    await ctx.send("my commands are:\n!play <youtube search or url>\n!skip\n!pause\n!resume\n!stop\n!leave")


@client.command()
async def skip(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        pass
    elif not voice.is_playing():
        return

    voice.stop()
    await ctx.send('song skipped!')


client.run('ODg3MzM5OTkwNjE3NTg3ODAz.YUCtww.w6GE2UXFgdPMU3nrsbEgVFpRSus')
