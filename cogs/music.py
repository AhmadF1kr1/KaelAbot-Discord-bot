"""
Music System Cog
Handles all music-related commands (Supports Prefix & Slash Commands)
"""

import discord
from discord.ext import commands
from discord import app_commands # Import untuk slash command features
import yt_dlp
import asyncio
from collections import deque
import random

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Music state storage
        self.queue = {}           # Song queues per guild
        self.now_playing = {}     # Current song per guild
        self.loop_mode = {}       # Loop mode per guild
        self.volume_level = {}    # Volume per guild
        
        # YouTube DL options
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'default_search': 'auto',
            'source_address': '0.0.0.0'
        }
        
        # FFmpeg options
        self.ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -bufsize 8192k'
        }
    
    async def ensure_voice(self, ctx):
        """Ensure bot is connected to voice"""
        if not ctx.author.voice:
            await ctx.send("❌ You must be in a voice channel!")
            return False
            
        if ctx.voice_client is None:
            await ctx.author.voice.channel.connect()
        elif ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.voice_client.move_to(ctx.author.voice.channel)
            
        return True
    
    async def search_song(self, query):
        """Search for a song on YouTube"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                if not query.startswith('http'):
                    query = f"ytsearch:{query}"
                
                info = ydl.extract_info(query, download=False)
                
                if 'entries' in info:
                    if len(info['entries']) > 0:
                        info = info['entries'][0]
                    else:
                        return None
                
                song = {
                    'title': info.get('title', 'Unknown Title'),
                    'url': info.get('webpage_url', ''),
                    'duration': info.get('duration', 0),
                    'source': info.get('url', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown'),
                    'views': info.get('view_count', 0)
                }

                print(song)
                
                return song
                
        except Exception as e:
            print(f"Search error: {e}")
            return None
    
    async def play_next(self, ctx):
        """Play the next song in queue"""
        guild_id = ctx.guild.id
        
        if self.loop_mode.get(guild_id) == 'song' and guild_id in self.now_playing:
            current = self.now_playing[guild_id]
            source = current.get('source')
        elif self.queue.get(guild_id) and len(self.queue[guild_id]) > 0:
            song = self.queue[guild_id].popleft()
            self.now_playing[guild_id] = song
            
            if self.loop_mode.get(guild_id) == 'queue':
                self.queue[guild_id].append(song)
            
            source = song.get('source')
        else:
            self.now_playing.pop(guild_id, None)
            
            embed = discord.Embed(
                title="📭 Queue Empty",
                description="No more songs in queue. Leaving voice channel in 60 seconds.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            
            await asyncio.sleep(60)
            if ctx.voice_client and not ctx.voice_client.is_playing():
                await ctx.voice_client.disconnect()
            return
        
        if source and ctx.voice_client:
            try:
                # audio_source = await discord.FFmpegOpusAudio.from_probe(
                #     source,
                #     **self.ffmpeg_opts
                # )

                audio_source = discord.FFmpegPCMAudio(
                    source,
                    **self.ffmpeg_opts
                )

                print(vars(audio_source))
                
                if guild_id in self.volume_level:
                    audio_source = discord.PCMVolumeTransformer(
                        audio_source,
                        volume=self.volume_level[guild_id]
                    )
                
                ctx.voice_client.play(
                    audio_source,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.play_next(ctx), 
                        self.bot.loop
                    ).result()
                )
                
                song = self.now_playing[guild_id]
                duration = f"{song['duration']//60}:{song['duration']%60:02d}"
                
                embed = discord.Embed(
                    title="🎵 Now Playing",
                    description=f"**[{song['title']}]({song['url']})**",
                    color=discord.Color.green()
                )
                embed.add_field(name="Duration", value=f"`{duration}`", inline=True)
                embed.add_field(name="Uploader", value=song['uploader'], inline=True)
                if song['thumbnail']:
                    embed.set_thumbnail(url=song['thumbnail'])
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                print(f"Playback error: {e}")
                await ctx.send(f"❌ Error playing song: {e}")
                await self.play_next(ctx)
    
    # =========================
    # HYBRID COMMANDS START HERE
    # =========================

    @commands.hybrid_command(name='play', aliases=['p'], description="Play a song from YouTube")
    @app_commands.describe(query="The song name or YouTube URL to play")
    async def play(self, ctx: commands.Context, *, query: str):
        """Play a song from YouTube"""
        await ctx.defer() # Mencegah error "Interaction failed" pada slash command
        
        if not await self.ensure_voice(ctx):
            return
        
        guild_id = ctx.guild.id
        
        if guild_id not in self.queue:
            self.queue[guild_id] = deque()
            self.loop_mode[guild_id] = 'off'
            self.volume_level[guild_id] = 1.0
        
        # Search for song (typing indicator otomatis aktif karena defer)
        song = await self.search_song(query)
        
        if not song:
            await ctx.send("❌ Could not find the song!")
            return
        
        self.queue[guild_id].append(song)
        
        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            await self.play_next(ctx)
        else:
            embed = discord.Embed(
                title="✅ Added to Queue",
                description=f"**[{song['title']}]({song['url']})**",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Queue Position",
                value=f"#{len(self.queue[guild_id])}",
                inline=True
            )
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='pause', description="Pause the current song")
    async def pause(self, ctx: commands.Context):
        """Pause the current song"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ **Paused**")
        else:
            await ctx.send("❌ Nothing is playing!")
    
    @commands.hybrid_command(name='resume', description="Resume the paused song")
    async def resume(self, ctx: commands.Context):
        """Resume the paused song"""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶️ **Resumed**")
        else:
            await ctx.send("❌ Nothing is paused!")
    
    @commands.hybrid_command(name='skip', aliases=['s'], description="Skip to the next song")
    async def skip(self, ctx: commands.Context):
        """Skip to the next song"""
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop()
            await ctx.send("⏭️ **Skipped!**")
        else:
            await ctx.send("❌ Nothing is playing!")
    
    @commands.hybrid_command(name='stop', description="Stop music and clear queue")
    async def stop(self, ctx: commands.Context):
        """Stop music and clear queue"""
        guild_id = ctx.guild.id
        
        if ctx.voice_client:
            if guild_id in self.queue:
                self.queue[guild_id].clear()
                self.loop_mode[guild_id] = 'off'
            
            await ctx.voice_client.disconnect()
            await ctx.send("🛑 **Stopped and disconnected!**")
        else:
            await ctx.send("❌ I'm not in a voice channel!")
    
    @commands.hybrid_command(name='volume', aliases=['vol'], description="Set volume level (0-200)")
    @app_commands.describe(volume="Volume level from 0 to 200 (leave empty to check current)")
    async def volume(self, ctx: commands.Context, volume: int = None):
        """Set volume level (0-200)"""
        if not ctx.voice_client:
            return await ctx.send("❌ I'm not in a voice channel!")
        
        if volume is None:
            current_vol = int(self.volume_level.get(ctx.guild.id, 1.0) * 100)
            return await ctx.send(f"🔊 Current volume: **{current_vol}%**")
        
        if 0 <= volume <= 200:
            self.volume_level[ctx.guild.id] = volume / 100
            
            if ctx.voice_client.source:
                if hasattr(ctx.voice_client.source, 'volume'):
                    ctx.voice_client.source.volume = volume / 100
            
            bar_length = 20
            filled = int(bar_length * volume / 200)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            await ctx.send(f"🔊 Volume: `{volume}%`\n{bar}")
        else:
            await ctx.send("❌ Volume must be between 0 and 200!")
    
    @commands.hybrid_command(name='queue', aliases=['q'], description="Show the current queue")
    async def show_queue(self, ctx: commands.Context):
        """Show the current queue"""
        await ctx.defer() # Defer untuk mencegah timeout jika queue panjang
        guild_id = ctx.guild.id
        
        if guild_id not in self.queue or len(self.queue[guild_id]) == 0:
            embed = discord.Embed(
                title="📋 Music Queue",
                description="Queue is empty! Use `/play` to add songs.",
                color=discord.Color.blue()
            )
            return await ctx.send(embed=embed)
        
        queue_list = ""
        total_duration = 0
        
        for i, song in enumerate(self.queue[guild_id], 1):
            duration = song['duration']
            total_duration += duration
            
            mins = duration // 60
            secs = duration % 60
            
            queue_list += f"`{i}.` **{song['title'][:50]}** `[{mins}:{secs:02d}]`\n"
            
            if i >= 10:
                remaining = len(self.queue[guild_id]) - 10
                if remaining > 0:
                    queue_list += f"\n*...and {remaining} more songs*"
                break
        
        embed = discord.Embed(
            title="📋 Music Queue",
            description=queue_list,
            color=discord.Color.blue()
        )
        
        total_mins = total_duration // 60
        total_secs = total_duration % 60
        
        loop_mode = self.loop_mode.get(guild_id, 'off')
        loop_emoji = {'off': '❌', 'song': '🔂', 'queue': '🔁'}
        
        embed.add_field(
            name="Statistics",
            value=f"📊 Total Songs: **{len(self.queue[guild_id])}**\n"
                  f"⏱️ Total Duration: **{total_mins}:{total_secs:02d}**\n"
                  f"🔁 Loop Mode: {loop_emoji.get(loop_mode, '❌')} **{loop_mode}**",
            inline=False
        )
        
        if guild_id in self.now_playing:
            current = self.now_playing[guild_id]
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{current['title'][:50]}**",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='shuffle', description="Shuffle the queue")
    async def shuffle(self, ctx: commands.Context):
        """Shuffle the queue"""
        guild_id = ctx.guild.id
        
        if guild_id in self.queue and len(self.queue[guild_id]) > 1:
            queue_list = list(self.queue[guild_id])
            random.shuffle(queue_list)
            self.queue[guild_id] = deque(queue_list)
            
            await ctx.send("🔀 **Queue shuffled!**")
        else:
            await ctx.send("❌ Queue needs at least 2 songs to shuffle!")
    
    @commands.hybrid_command(name='loop', aliases=['repeat'], description="Set loop mode: off, song, queue")
    @app_commands.describe(mode="The loop mode to set")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off", value="off"),
        app_commands.Choice(name="Song", value="song"),
        app_commands.Choice(name="Queue", value="queue")
    ])
    async def loop(self, ctx: commands.Context, mode: str = None):
        """Set loop mode: off, song, queue"""
        valid_modes = ['off', 'song', 'queue']
        
        if mode is None:
            current = self.loop_mode.get(ctx.guild.id, 'off')
            return await ctx.send(f"🔁 Current loop mode: **{current}**\n"
                                f"Available: `off/song/queue`")
        
        mode = mode.lower()
        if mode not in valid_modes:
            return await ctx.send(f"❌ Invalid mode! Use: `{'/'.join(valid_modes)}`")
        
        self.loop_mode[ctx.guild.id] = mode
        
        emoji_map = {
            'off': '❌',
            'song': '🔂',
            'queue': '🔁'
        }
        
        descriptions = {
            'off': 'Loop disabled',
            'song': 'Looping current song',
            'queue': 'Looping entire queue'
        }
        
        await ctx.send(f"{emoji_map[mode]} **{descriptions[mode]}**")
    
    @commands.hybrid_command(name='nowplaying', aliases=['np'], description="Show currently playing song")
    async def now_playing(self, ctx: commands.Context):
        """Show currently playing song"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.now_playing:
            return await ctx.send("❌ Nothing is currently playing!")
        
        song = self.now_playing[guild_id]
        
        duration = song['duration']
        mins = duration // 60
        secs = duration % 60
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{song['title']}]({song['url']})**",
            color=discord.Color.green()
        )
        embed.add_field(name="Duration", value=f"`{mins}:{secs:02d}`", inline=True)
        embed.add_field(name="Uploader", value=song['uploader'], inline=True)
        embed.add_field(name="Views", value=f"{song['views']:,}", inline=True)
        
        if song['thumbnail']:
            embed.set_thumbnail(url=song['thumbnail'])
        
        queue_length = len(self.queue.get(guild_id, []))
        embed.set_footer(text=f"Songs in queue: {queue_length}")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name='remove', description="Remove a song from queue by index")
    @app_commands.describe(index="The queue position number to remove (1-based)")
    async def remove(self, ctx: commands.Context, index: int):
        """Remove a song from queue by index"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.queue or len(self.queue[guild_id]) == 0:
            return await ctx.send("❌ Queue is empty!")
        
        if 1 <= index <= len(self.queue[guild_id]):
            queue_list = list(self.queue[guild_id])
            removed_song = queue_list.pop(index - 1)
            self.queue[guild_id] = deque(queue_list)
            
            await ctx.send(f"🗑️ Removed: **{removed_song['title']}**")
        else:
            await ctx.send(f"❌ Invalid index! Queue has {len(self.queue[guild_id])} songs.")
    
    @commands.hybrid_command(name='clearqueue', aliases=['cq'], description="Clear the entire queue")
    async def clear_queue(self, ctx: commands.Context):
        """Clear the entire queue"""
        guild_id = ctx.guild.id
        
        if guild_id in self.queue:
            self.queue[guild_id].clear()
            await ctx.send("🗑️ **Queue cleared!**")
        else:
            await ctx.send("❌ Queue is already empty!")
    
    # =========================
    # LISTENERS
    # =========================

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Leave if alone in voice channel"""
        if member.id == self.bot.user.id:
            return
        
        voice_client = member.guild.voice_client
        if voice_client and voice_client.channel:
            if len(voice_client.channel.members) == 1:
                await asyncio.sleep(60)
                if voice_client and voice_client.channel and len(voice_client.channel.members) == 1:
                    await voice_client.disconnect()
                    guild_id = member.guild.id
                    if guild_id in self.queue:
                        self.queue[guild_id].clear()

async def setup(bot):
    await bot.add_cog(Music(bot))
    print('🎵 Music cog loaded!')