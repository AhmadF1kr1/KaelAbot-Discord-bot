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
import aiohttp
import pykakasi

class NowPlayingView(discord.ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=None) # Keep buttons active
        self.cog = cog
        self.ctx = ctx
        self.update_buttons()

    def update_buttons(self):
        guild_id = self.ctx.guild.id
        
        # Update Pause/Resume button style and label
        voice_client = self.ctx.guild.voice_client
        is_paused = voice_client.is_paused() if voice_client else False
        self.pause_resume.label = "Resume" if is_paused else "Pause"
        self.pause_resume.emoji = "▶️" if is_paused else "⏸️"
        self.pause_resume.style = discord.ButtonStyle.green if is_paused else discord.ButtonStyle.blurple
        
        # Update Loop button
        loop_mode = self.cog.loop_mode.get(guild_id, 'off')
        loop_labels = {'off': 'Loop: Off', 'song': 'Loop: Song', 'queue': 'Loop: Queue'}
        loop_emojis = {'off': '🔁', 'song': '🔂', 'queue': '🔁'}
        loop_styles = {
            'off': discord.ButtonStyle.grey,
            'song': discord.ButtonStyle.green,
            'queue': discord.ButtonStyle.green
        }
        self.loop_toggle.label = loop_labels[loop_mode]
        self.loop_toggle.emoji = loop_emojis[loop_mode]
        self.loop_toggle.style = loop_styles[loop_mode]
        
        # Update Autoplay button
        autoplay_active = self.cog.autoplay.get(guild_id, False)
        self.autoplay_toggle.label = f"Autoplay: {'On' if autoplay_active else 'Off'}"
        self.autoplay_toggle.style = discord.ButtonStyle.green if autoplay_active else discord.ButtonStyle.grey

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice or not interaction.guild.voice_client or interaction.user.voice.channel != interaction.guild.voice_client.channel:
            await interaction.response.send_message("❌ You must be in the same voice channel to use the music controls!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.grey, emoji="⏮️", row=0)
    async def prev_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        history_list = self.cog.history.get(guild_id, [])
        if not history_list:
            return await interaction.response.send_message("❌ No previous songs in history!", ephemeral=True)
            
        # Pop the last song from history
        prev_song = history_list.pop()
        
        # Prepends
        if guild_id in self.cog.now_playing:
            self.cog.queue[guild_id].appendleft(self.cog.now_playing[guild_id])
            
        self.cog.queue[guild_id].appendleft(prev_song)
        
        # Stop current playback, play_next will trigger automatically
        if self.ctx.voice_client:
            self.ctx.voice_client.stop()
            await interaction.response.send_message("⏮️ **Playing previous song...**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Not in a voice channel!", ephemeral=True)

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.blurple, emoji="⏸️", row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        voice_client = self.ctx.guild.voice_client
        if not voice_client:
            return await interaction.response.send_message("❌ Not connected to voice!", ephemeral=True)

        if voice_client.is_playing():
            voice_client.pause()
            if guild_id in self.cog.start_time and self.cog.start_time[guild_id] is not None:
                import time
                self.cog.accumulated_time[guild_id] += time.time() - self.cog.start_time[guild_id]
                self.cog.start_time[guild_id] = None
            await interaction.response.send_message("⏸️ **Paused**", ephemeral=True)
        elif voice_client.is_paused():
            voice_client.resume()
            import time
            self.cog.start_time[guild_id] = time.time()
            await interaction.response.send_message("▶️ **Resumed**", ephemeral=True)
        else:
            return await interaction.response.send_message("❌ Nothing is currently playing or paused!", ephemeral=True)

        self.update_buttons()
        embed = self.cog.get_now_playing_embed(guild_id)
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.grey, emoji="⏭️", row=0)
    async def skip_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = self.ctx.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await interaction.response.send_message("⏭️ **Skipped!**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)

    @discord.ui.button(label="Shuffle", style=discord.ButtonStyle.grey, emoji="🔀", row=0)
    async def shuffle_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        if guild_id in self.cog.queue and len(self.cog.queue[guild_id]) > 1:
            queue_list = list(self.cog.queue[guild_id])
            import random
            random.shuffle(queue_list)
            self.cog.queue[guild_id] = deque(queue_list)
            await interaction.response.send_message("🔀 **Queue shuffled!**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Queue needs at least 2 songs to shuffle!", ephemeral=True)

    @discord.ui.button(label="Loop: Off", style=discord.ButtonStyle.grey, emoji="🔁", row=0)
    async def loop_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        current = self.cog.loop_mode.get(guild_id, 'off')
        next_mode = {'off': 'song', 'song': 'queue', 'queue': 'off'}[current]
        self.cog.loop_mode[guild_id] = next_mode
        
        self.update_buttons()
        embed = self.cog.get_now_playing_embed(guild_id)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"🔁 Loop mode set to: **{next_mode}**", ephemeral=True)

    @discord.ui.button(label="Queue", style=discord.ButtonStyle.grey, emoji="📋", row=1)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        if guild_id not in self.cog.queue or len(self.cog.queue[guild_id]) == 0:
            embed = discord.Embed(
                title="📋 Music Queue",
                description="Queue is empty! Use `/play` to add songs.",
                color=discord.Color.blue()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        queue_len = len(self.cog.queue[guild_id])
        if queue_len > 10:
            view = QueueView(self.cog, guild_id, interaction.user.id)
            embed = view.get_page_embed()
            return await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        queue_list = ""
        total_duration = 0
        for i, song in enumerate(self.cog.queue[guild_id], 1):
            duration = song['duration']
            total_duration += duration
            mins = duration // 60
            secs = duration % 60
            queue_list += f"`{i}.` **{song['title'][:50]}** `[{mins}:{secs:02d}]`\n"
        
        embed = discord.Embed(
            title="📋 Music Queue",
            description=queue_list,
            color=discord.Color.blue()
        )
        total_mins = total_duration // 60
        total_secs = total_duration % 60
        loop_mode = self.cog.loop_mode.get(guild_id, 'off')
        loop_emoji = {'off': '❌', 'song': '🔂', 'queue': '🔁'}
        
        embed.add_field(
            name="Statistics",
            value=f"📊 Total Songs: **{queue_len}**\n"
                  f"⏱️ Total Duration: **{total_mins}:{total_secs:02d}**\n"
                  f"🔁 Loop Mode: {loop_emoji.get(loop_mode, '❌')} **{loop_mode}**",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Autoplay: Off", style=discord.ButtonStyle.grey, emoji="📻", row=1)
    async def autoplay_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        current = self.cog.autoplay.get(guild_id, False)
        self.cog.autoplay[guild_id] = not current
        
        self.update_buttons()
        embed = self.cog.get_now_playing_embed(guild_id)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"📻 Autoplay is now **{'Enabled' if not current else 'Disabled'}**", ephemeral=True)

    @discord.ui.button(label="-10%", style=discord.ButtonStyle.grey, emoji="🔉", row=1)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        current_vol = self.cog.volume_level.get(guild_id, 1.0)
        new_vol = max(0.0, current_vol - 0.1)
        self.cog.volume_level[guild_id] = new_vol
        
        if self.ctx.voice_client and self.ctx.voice_client.source:
            if hasattr(self.ctx.voice_client.source, 'volume'):
                self.ctx.voice_client.source.volume = new_vol
                
        self.update_buttons()
        embed = self.cog.get_now_playing_embed(guild_id)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"🔉 Volume reduced to **{int(new_vol * 100)}%**", ephemeral=True)

    @discord.ui.button(label="+10%", style=discord.ButtonStyle.grey, emoji="🔊", row=1)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.ctx.guild.id
        current_vol = self.cog.volume_level.get(guild_id, 1.0)
        new_vol = min(2.0, current_vol + 0.1)
        self.cog.volume_level[guild_id] = new_vol
        
        if self.ctx.voice_client and self.ctx.voice_client.source:
            if hasattr(self.ctx.voice_client.source, 'volume'):
                self.ctx.voice_client.source.volume = new_vol
                
        self.update_buttons()
        embed = self.cog.get_now_playing_embed(guild_id)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(f"🔊 Volume increased to **{int(new_vol * 100)}%**", ephemeral=True)


class QueueView(discord.ui.View):
    def __init__(self, cog, guild_id, user_id):
        super().__init__(timeout=60.0)
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id
        self.current_page = 0
        self.per_page = 10
        self.update_buttons()

    def update_buttons(self):
        queue = self.cog.queue.get(self.guild_id, [])
        total_pages = (len(queue) - 1) // self.per_page + 1
        
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= total_pages - 1
        
        self.prev_page.label = f"Page {self.current_page}" if self.current_page > 0 else "Prev"
        self.next_page.label = f"Page {self.current_page + 2}" if self.current_page < total_pages - 1 else "Next"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
            return False
        return True

    def get_page_embed(self):
        queue = self.cog.queue.get(self.guild_id, [])
        total_songs = len(queue)
        
        if total_songs == 0:
            return discord.Embed(
                title="📋 Music Queue",
                description="Queue is empty! Use `/play` to add songs.",
                color=discord.Color.blue()
            )
            
        start_idx = self.current_page * self.per_page
        end_idx = start_idx + self.per_page
        page_songs = list(queue)[start_idx:end_idx]
        
        queue_list = ""
        for i, song in enumerate(page_songs, start_idx + 1):
            duration = song['duration']
            mins = duration // 60
            secs = duration % 60
            queue_list += f"`{i}.` **{song['title'][:50]}** `[{mins}:{secs:02d}]`\n"

        total_duration = sum(song['duration'] for song in queue)
        total_mins = total_duration // 60
        total_secs = total_duration % 60
        
        loop_mode = self.cog.loop_mode.get(self.guild_id, 'off')
        loop_emoji = {'off': '❌', 'song': '🔂', 'queue': '🔁'}
        
        total_pages = (total_songs - 1) // self.per_page + 1
        
        embed = discord.Embed(
            title="📋 Music Queue",
            description=queue_list,
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Statistics",
            value=f"📊 Total Songs: **{total_songs}**\n"
                  f"⏱️ Total Duration: **{total_mins}:{total_secs:02d}**\n"
                  f"🔁 Loop Mode: {loop_emoji.get(loop_mode, '❌')} **{loop_mode}**",
            inline=False
        )
        
        if self.guild_id in self.cog.now_playing:
            current = self.cog.now_playing[self.guild_id]
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{current['title'][:50]}**",
                inline=False
            )
            
        embed.set_footer(text=f"Page {self.current_page + 1} of {total_pages}")
        return embed

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.blurple, emoji="◀️")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        embed = self.get_page_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple, emoji="▶️")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        embed = self.get_page_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._session = None
        self.kks = pykakasi.kakasi()
        
        # Music state storage
        self.queue = {}           # Song queues per guild
        self.now_playing = {}     # Current song per guild
        self.loop_mode = {}       # Loop mode per guild
        self.volume_level = {}    # Volume per guild
        self.search_results = {}  # Last search results per guild
        self.start_time = {}      # Play start time per guild
        self.accumulated_time = {} # Accumulated play time before last pause per guild
        self.history = {}         # Played songs history per guild
        self.autoplay = {}        # Autoplay toggle state per guild
        
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
            'source_address': '0.0.0.0',
            'cachedir': False
        }
        
        # FFmpeg options
        self.ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

    @property
    def session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def cog_unload(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def cleanup_guild(self, guild_id):
        """Cleans up all cached music state data for a guild to prevent memory leaks"""
        self.queue.pop(guild_id, None)
        self.now_playing.pop(guild_id, None)
        self.loop_mode.pop(guild_id, None)
        self.volume_level.pop(guild_id, None)
        self.search_results.pop(guild_id, None)
        self.start_time.pop(guild_id, None)
        self.accumulated_time.pop(guild_id, None)
        self.history.pop(guild_id, None)
        self.autoplay.pop(guild_id, None)
    
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
            loop = asyncio.get_running_loop()
            def extract():
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    q = query if query.startswith('http') else f"ytsearch:{query}"
                    return ydl.extract_info(q, download=False)
            
            info = await loop.run_in_executor(None, extract)
            
            if not info:
                return None
                
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

    async def search_multiple_songs(self, query, limit=5):
        """Search for up to limit songs on YouTube"""
        try:
            loop = asyncio.get_running_loop()
            def extract():
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    q = query if query.startswith('http') else f"ytsearch{limit}:{query}"
                    return ydl.extract_info(q, download=False)
            
            info = await loop.run_in_executor(None, extract)
            
            if not info:
                return []
                
            songs = []
            if 'entries' in info:
                entries = info['entries']
            else:
                entries = [info]
            
            for entry in entries:
                if not entry:
                    continue
                songs.append({
                    'title': entry.get('title', 'Unknown Title'),
                    'url': entry.get('webpage_url', ''),
                    'duration': entry.get('duration', 0),
                    'source': entry.get('url', ''),
                    'thumbnail': entry.get('thumbnail', ''),
                    'uploader': entry.get('uploader', 'Unknown'),
                    'views': entry.get('view_count', 0)
                })
                if len(songs) >= limit:
                    break
            
            return songs
        except Exception as e:
            print(f"Multiple search error: {e}")
            return []
    
    async def play_next(self, ctx):
        """Play the next song in queue"""
        guild_id = ctx.guild.id
        
        # Save current song to history if we are moving to a new song
        old_song = self.now_playing.get(guild_id)
        
        # Determine next song source
        if self.loop_mode.get(guild_id) == 'song' and old_song:
            source = old_song.get('source')
        elif self.queue.get(guild_id) and len(self.queue[guild_id]) > 0:
            if old_song:
                self.history.setdefault(guild_id, []).append(old_song)
                if len(self.history[guild_id]) > 20:
                    self.history[guild_id].pop(0)
            song = self.queue[guild_id].popleft()
            self.now_playing[guild_id] = song
            
            if self.loop_mode.get(guild_id) == 'queue':
                self.queue[guild_id].append(song)
            
            source = song.get('source')
        elif self.autoplay.get(guild_id, False) and old_song:
            if old_song:
                self.history.setdefault(guild_id, []).append(old_song)
                if len(self.history[guild_id]) > 20:
                    self.history[guild_id].pop(0)
            
            # Send notification info
            await ctx.send("📻 **Queue ended. Autoplay searching for next song...**")
            
            query = old_song['title']
            songs = await self.search_multiple_songs(query, limit=3)
            autoplay_song = None
            for s in songs:
                if s['url'] != old_song['url']:
                    autoplay_song = s
                    break
            if not autoplay_song and songs:
                autoplay_song = songs[0]
                
            if autoplay_song:
                self.now_playing[guild_id] = autoplay_song
                source = autoplay_song.get('source')
            else:
                self.now_playing.pop(guild_id, None)
                source = None
        else:
            if old_song:
                self.history.setdefault(guild_id, []).append(old_song)
                if len(self.history[guild_id]) > 20:
                    self.history[guild_id].pop(0)
            self.now_playing.pop(guild_id, None)
            source = None
        
        if not source:
            embed = discord.Embed(
                title="📭 Queue Empty",
                description="No more songs in queue. Leaving voice channel in 60 seconds.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            
            await asyncio.sleep(60)
            if ctx.voice_client and not ctx.voice_client.is_playing():
                await ctx.voice_client.disconnect()
                self.cleanup_guild(guild_id)
            return
        
        if source and ctx.voice_client:
            try:
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
                
                def after_playing(error):
                    if error:
                        print(f"Playback error in after callback: {error}")
                    asyncio.run_coroutine_threadsafe(
                        self.play_next(ctx), 
                        self.bot.loop
                    )

                ctx.voice_client.play(
                    audio_source,
                    after=after_playing
                )
                
                import time
                self.start_time[guild_id] = time.time()
                self.accumulated_time[guild_id] = 0.0
                
                embed = self.get_now_playing_embed(guild_id)
                view = NowPlayingView(self, ctx)
                await ctx.send(embed=embed, view=view)
                
            except Exception as e:
                print(f"Playback error: {e}")
                await ctx.send(f"❌ Error playing song: {e}")
                await self.play_next(ctx)
    def get_now_playing_embed(self, guild_id):
        if guild_id not in self.now_playing:
            return None
        song = self.now_playing[guild_id]
        
        import time
        elapsed = 0.0
        is_paused = False
        if guild_id in self.start_time:
            if self.start_time[guild_id] is not None:
                elapsed = self.accumulated_time.get(guild_id, 0.0) + (time.time() - self.start_time[guild_id])
            else:
                elapsed = self.accumulated_time.get(guild_id, 0.0)
                is_paused = True
        
        elapsed = int(elapsed)
        duration = song['duration']
        
        elapsed_mins = elapsed // 60
        elapsed_secs = elapsed % 60
        duration_mins = duration // 60
        duration_secs = duration % 60
        
        elapsed_str = f"{elapsed_mins}:{elapsed_secs:02d}"
        duration_str = f"{duration_mins}:{duration_secs:02d}"
        
        bar_length = 15
        if duration > 0:
            ratio = elapsed / duration
            if ratio > 1: ratio = 1
            if ratio < 0: ratio = 0
            filled = int(ratio * bar_length)
            bar = "▬" * filled + "🔘" + "▬" * (bar_length - filled - 1)
        else:
            bar = "🔘" + "▬" * (bar_length - 1)
            
        progress_str = f"`{elapsed_str}` {bar} `{duration_str}`"
        
        status_line = ""
        if is_paused:
            status_line += "⏸️ **Paused**  "
        else:
            status_line += "▶️ **Playing**  "
            
        loop_mode = self.loop_mode.get(guild_id, 'off')
        loop_emojis = {'off': '', 'song': '🔂', 'queue': '🔁'}
        if loop_mode != 'off':
            status_line += f"{loop_emojis[loop_mode]} **Loop: {loop_mode}**  "
            
        if self.autoplay.get(guild_id, False):
            status_line += "📻 **Autoplay**  "
            
        vol = int(self.volume_level.get(guild_id, 1.0) * 100)
        status_line += f"🔊 **{vol}%**"
        
        embed = discord.Embed(
            description=f"**[{song['title']}]({song['url']})**\n\n{progress_str}\n\n{status_line}",
            color=discord.Color.green()
        )
        embed.set_author(name="Now Playing", icon_url="https://i.imgur.com/L8D5e9V.gif")
        embed.add_field(name="Uploader", value=song['uploader'], inline=True)
        embed.add_field(name="Views", value=f"{song['views']:,}", inline=True)
        
        if song['thumbnail']:
            embed.set_thumbnail(url=song['thumbnail'])
            
        queue_length = len(self.queue.get(guild_id, []))
        embed.set_footer(text=f"Songs in queue: {queue_length}")
        
        return embed

    # =========================
    # HYBRID COMMANDS START HERE
    # =========================

    @commands.hybrid_command(name='search', description="Search for up to 5 songs on YouTube")
    @app_commands.describe(query="The song name to search for")
    async def search(self, ctx: commands.Context, *, query: str):
        """Search for up to 5 songs on YouTube"""
        await ctx.defer()
        
        songs = await self.search_multiple_songs(query, limit=5)
        if not songs:
            await ctx.send("❌ No songs found!")
            return
        
        guild_id = ctx.guild.id
        self.search_results[guild_id] = songs
        
        embed = discord.Embed(
            title=f"🔍 Search Results for: {query}",
            description="Use `/select <number>` to play one of the songs.",
            color=discord.Color.blue()
        )
        
        for i, song in enumerate(songs, 1):
            duration = f"{song['duration']//60}:{song['duration']%60:02d}"
            embed.add_field(
                name=f"{i}. {song['title'][:60]}",
                value=f"Duration: `{duration}` | Uploader: {song['uploader']}",
                inline=False
            )
            
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='select', description="Play a song from the last search results")
    @app_commands.describe(index="The number (1-5) of the song to select")
    async def select(self, ctx: commands.Context, index: int):
        """Play a song from the last search results"""
        await ctx.defer()
        
        guild_id = ctx.guild.id
        if guild_id not in self.search_results or not self.search_results[guild_id]:
            await ctx.send("❌ No search results found! Use `/search` first.")
            return
        
        songs = self.search_results[guild_id]
        if not (1 <= index <= len(songs)):
            await ctx.send(f"❌ Invalid choice! Choose a number between 1 and {len(songs)}.")
            return
            
        song = songs[index - 1]
        
        if not await self.ensure_voice(ctx):
            return
            
        if guild_id not in self.queue:
            self.queue[guild_id] = deque()
            self.loop_mode[guild_id] = 'off'
            self.volume_level[guild_id] = 1.0
            
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
            guild_id = ctx.guild.id
            if guild_id in self.start_time and self.start_time[guild_id] is not None:
                import time
                self.accumulated_time[guild_id] += time.time() - self.start_time[guild_id]
                self.start_time[guild_id] = None
            await ctx.send("⏸️ **Paused**")
        else:
            await ctx.send("❌ Nothing is playing!")
    
    @commands.hybrid_command(name='resume', description="Resume the paused song")
    async def resume(self, ctx: commands.Context):
        """Resume the paused song"""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            guild_id = ctx.guild.id
            import time
            self.start_time[guild_id] = time.time()
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
            await ctx.voice_client.disconnect()
            self.cleanup_guild(guild_id)
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
        
        queue_len = len(self.queue[guild_id])
        if queue_len > 10:
            view = QueueView(self, guild_id, ctx.author.id)
            embed = view.get_page_embed()
            return await ctx.send(embed=embed, view=view)
            
        queue_list = ""
        total_duration = 0
        
        for i, song in enumerate(self.queue[guild_id], 1):
            duration = song['duration']
            total_duration += duration
            
            mins = duration // 60
            secs = duration % 60
            
            queue_list += f"`{i}.` **{song['title'][:50]}** `[{mins}:{secs:02d}]`\n"
        
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
            value=f"📊 Total Songs: **{queue_len}**\n"
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
        
        embed = self.get_now_playing_embed(guild_id)
        view = NowPlayingView(self, ctx)
        await ctx.send(embed=embed, view=view)
    
    @commands.hybrid_command(name='lyrics', description="Show lyrics of the currently playing song")
    async def lyrics(self, ctx: commands.Context):
        """Show lyrics of the currently playing song"""
        await ctx.defer()
        try:
            guild_id = ctx.guild.id
            
            if guild_id not in self.now_playing:
                return await ctx.send("❌ Nothing is currently playing!")
                
            song_title = self.now_playing[guild_id]['title']
            
            # Clean title to get better search results
            import re
            clean_title = song_title
            clean_title = re.sub(r'\s*[\(\[][^)]*?(?:official|music|video|lyric|audio|hd|hq|version|edit|remix|ft\.|feat\.)[^)]*?[\)\]]', '', clean_title, flags=re.IGNORECASE)
            clean_title = re.sub(r'\s*-\s*(?:official|music|video|lyric|audio|hd|hq|version|edit|remix|ft\.|feat\.).*$', '', clean_title, flags=re.IGNORECASE)
            
            # Remove Japanese/Chinese brackets and their contents
            clean_title = re.sub(r'【[^】]*】', '', clean_title)
            clean_title = re.sub(r'「[^」]*」', '', clean_title)
            clean_title = re.sub(r'『[^』]*』', '', clean_title)
            clean_title = re.sub(r'（[^）]*）', '', clean_title)
            clean_title = re.sub(r'［[^］]*］', '', clean_title)
            clean_title = clean_title.strip()
            
            # If cleaning results in empty string, fallback to original title
            if not clean_title:
                clean_title = song_title
                
            uploader = self.now_playing[guild_id].get('uploader', 'Unknown')
            
            # Build candidates
            candidates = []
            
            # 1. Try splitting the cleaned title by '-'
            parts = [p.strip() for p in re.split(r'\s*-\s*', clean_title)]
            if len(parts) >= 2:
                track, artist = parts[0], parts[1]
                candidates.append({"type": "get", "artist": artist, "track": track})
                candidates.append({"type": "get", "artist": track, "track": artist})
                candidates.append({"type": "search", "q": f"{track} {artist}"})
                candidates.append({"type": "search", "q": track})
                
            # 2. Try using clean uploader name and clean title
            clean_uploader = re.sub(r'\s*-\s*Topic|\s+Official\s*.*$', '', uploader, flags=re.IGNORECASE).strip()
            if clean_uploader and clean_uploader != "Unknown":
                candidates.append({"type": "get", "artist": clean_uploader, "track": clean_title})
                candidates.append({"type": "search", "q": f"{clean_title} {clean_uploader}"})
                
            # 3. Text search fallbacks
            candidates.append({"type": "search", "q": clean_title})
            candidates.append({"type": "search", "q": song_title})
            
            import urllib.parse
            headers = {"User-Agent": "KaelAbot-Discord-Bot/1.0.0 (https://github.com/AhmadF1kr1/Fiku-Bot)"}
            song_data = None
            
            for cand in candidates:
                try:
                    if cand["type"] == "get":
                        url = f"https://lrclib.net/api/get?artist_name={urllib.parse.quote(cand['artist'])}&track_name={urllib.parse.quote(cand['track'])}"
                    else:
                        url = f"https://lrclib.net/api/search?q={urllib.parse.quote(cand['q'])}"
                        
                    async with self.session.get(url, headers=headers, timeout=5) as response:
                        if response.status == 200:
                            res_data = await response.json()
                            if cand["type"] == "get":
                                if res_data and res_data.get('plainLyrics'):
                                    song_data = res_data
                                    break
                            else:
                                if res_data:
                                    for item in res_data:
                                        if item.get('plainLyrics'):
                                            song_data = item
                                            break
                                    if not song_data and len(res_data) > 0:
                                        song_data = res_data[0]
                                    if song_data:
                                        break
                except Exception as e:
                    print(f"Lyrics candidate fetch error: {e}")
                    
            if not song_data:
                return await ctx.send(f"❌ Could not find lyrics for **{song_title}**.")
                
            lyrics_text = song_data.get('plainLyrics')
            if not lyrics_text:
                return await ctx.send(f"❌ Could not find lyrics for **{song_title}**.")
            is_romanized = False
            
            # Auto-detect if lyrics contain Japanese characters to romanize
            has_japanese = any(
                0x3040 <= ord(char) <= 0x309F or  # Hiragana
                0x30A0 <= ord(char) <= 0x30FF or  # Katakana
                0x4E00 <= ord(char) <= 0x9FFF     # Kanji
                for char in lyrics_text
            )
            
            if has_japanese:
                try:
                    lines = []
                    for line in lyrics_text.splitlines():
                        if not line.strip():
                            lines.append("")
                            continue
                        converted = self.kks.convert(line)
                        line_romaji = " ".join(item['hepburn'] for item in converted)
                        lines.append(line_romaji)
                    lyrics_text = "\n".join(lines).strip()
                    is_romanized = True
                except Exception as e:
                    print(f"Failed to romanize lyrics via pykakasi: {e}")
    
            # Prepare embed
            title = song_data.get('trackName', song_title)
            artist = song_data.get('artistName', 'Unknown Artist')
            
            # Handle length limits
            if len(lyrics_text) > 4000:
                lyrics_text = lyrics_text[:3990] + "\n\n... (truncated)"
                
            embed = discord.Embed(
                title=f"🎶 Lyrics for: {title}" + (" (Romaji/Romanized)" if is_romanized else ""),
                description=f"**Artist:** {artist}\n\n{lyrics_text}",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Lyrics provided by LRCLIB" + (" | Romanized via pykakasi" if is_romanized else ""))
            return await ctx.send(embed=embed)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Lyrics fetch error: {e}")
            return await ctx.send("❌ An error occurred while fetching the lyrics.")
    
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
                voice_client = member.guild.voice_client # Refresh
                if voice_client and voice_client.channel and len(voice_client.channel.members) == 1:
                    await voice_client.disconnect()
                    guild_id = member.guild.id
                    self.cleanup_guild(guild_id)

async def setup(bot):
    await bot.add_cog(Music(bot))
    print('🎵 Music cog loaded!')