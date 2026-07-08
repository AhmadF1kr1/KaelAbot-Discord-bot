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
from difflib import SequenceMatcher
import os
import re
import time
import urllib.parse
from pathlib import Path

try:
    import lyricsgenius
except ImportError:
    lyricsgenius = None

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
        self.download_tasks = {}  # Active audio downloads by song URL
        self.lyrics_cache = {}    # Cached LRCLIB results by song identity
        self.cache_dir = Path("data") / "music_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.prefetch_limit = 2
        self.lyrics_headers = {"User-Agent": "KaelAbot-Discord-Bot/1.0.0 (https://github.com/AhmadF1kr1/Fiku-Bot)"}
        self.genius_token = os.getenv("GENIUS_ACCESS_TOKEN") or os.getenv("GENIUS_TOKEN")
        self.genius = None
        if lyricsgenius and self.genius_token:
            try:
                self.genius = lyricsgenius.Genius(
                    self.genius_token,
                    timeout=8,
                    retries=1,
                    remove_section_headers=True,
                    skip_non_songs=True
                )
            except Exception as e:
                print(f"Genius lyrics provider disabled: {e}")
        self.metadata_noise_re = re.compile(
            r'\s*[\(\[][^)]*?(?:official|music|video|lyric|audio|hd|hq|version|edit|remix|ft\.|feat\.|mv|pv|short|anime|tv|size|full|lyrics)[^)]*?[\)\]]',
            re.IGNORECASE
        )
        self.metadata_suffix_re = re.compile(
            r'\s*-\s*(?:official|music|video|lyric|audio|hd|hq|version|edit|remix|ft\.|feat\.|mv|pv|short|anime|tv|size|full|lyrics).*$',
            re.IGNORECASE
        )
        self.metadata_keyword_re = re.compile(
            r'\b(?:official|music|video|lyric|lyrics|audio|hd|hq|version|edit|remix|mv|pv|short|anime|tv|size|full)\b',
            re.IGNORECASE
        )
        self.uploader_noise_re = re.compile(r'\s*-\s*Topic|\s+Official\s*.*$', re.IGNORECASE)
        self.whitespace_re = re.compile(r'\s+')
        self.title_split_re = re.compile(r'\s*-\s*')
        self.paren_re = re.compile(r'\(([^)]+)\)')
        self.japanese_re = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
        self.non_word_re = re.compile(r'[^\w\s]', re.UNICODE)
        self.synced_timestamp_re = re.compile(r'\[\d{1,2}:\d{2}(?:\.\d{1,3})?\]')
        self.genius_embed_suffix_re = re.compile(r'\d*Embed\s*$', re.IGNORECASE)
        self.genius_lyrics_header_re = re.compile(r'^.*?Lyrics\s*', re.IGNORECASE)
        self.max_lyrics_candidates = 18
        self.lyrics_negative_cache_ttl = 300
        
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

        self.download_ydl_opts = {
            **self.ydl_opts,
            'default_search': None,
            'noplaylist': True,
            'outtmpl': str(self.cache_dir / '%(id)s.%(ext)s'),
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
        for task in self.download_tasks.values():
            if not task.done():
                task.cancel()

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

    def has_japanese(self, text):
        return bool(text and self.japanese_re.search(text))

    def clean_lyrics_query_text(self, text):
        """Remove common YouTube metadata noise before querying LRCLIB."""
        if not text:
            return ""

        text = self.metadata_noise_re.sub('', text)
        text = self.metadata_suffix_re.sub('', text)
        for open_bracket, close_bracket in (('【', '】'), ('「', '」'), ('『', '』'), ('（', '）'), ('［', '］')):
            text = re.sub(f'{re.escape(open_bracket)}[^{re.escape(close_bracket)}]*{re.escape(close_bracket)}', '', text)
        return text.strip()

    def romanize_text(self, text, compact=False, preserve_lines=False):
        if not text:
            return ""

        def convert_line(line):
            converted = self.kks.convert(line)
            romaji = " ".join(item['hepburn'] for item in converted)
            romaji = self.whitespace_re.sub(' ', romaji).strip()
            return self.whitespace_re.sub('', romaji) if compact else romaji

        if preserve_lines:
            return "\n".join(convert_line(line) if line.strip() else "" for line in text.splitlines()).strip()

        return convert_line(text)

    def unique_non_empty(self, values):
        seen = set()
        result = []
        for value in values:
            value = value.strip() if value else ""
            key = value.lower()
            if value and key not in seen:
                seen.add(key)
                result.append(value)
        return result

    def normalize_lyrics_match_text(self, text):
        if not text:
            return ""
        text = self.clean_lyrics_query_text(text).lower()
        text = self.non_word_re.sub(' ', text)
        return self.whitespace_re.sub(' ', text).strip()

    def text_similarity(self, left, right):
        left = self.normalize_lyrics_match_text(left)
        right = self.normalize_lyrics_match_text(right)
        if not left or not right:
            return 0.0
        if left == right:
            return 1.0

        left_tokens = set(left.split())
        right_tokens = set(right.split())
        token_score = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
        sequence_score = SequenceMatcher(None, left, right).ratio()
        return max(token_score, sequence_score)

    def synced_lyrics_to_plain(self, synced_lyrics):
        if not synced_lyrics:
            return ""

        lines = []
        for line in synced_lyrics.splitlines():
            line = self.synced_timestamp_re.sub('', line).strip()
            if line:
                lines.append(line)
        return "\n".join(lines).strip()

    def get_lyrics_text(self, song_data):
        if not isinstance(song_data, dict):
            return ""
        return (song_data.get('plainLyrics') or self.synced_lyrics_to_plain(song_data.get('syncedLyrics'))).strip()

    def clean_genius_lyrics(self, lyrics):
        if not lyrics:
            return ""

        lyrics = lyrics.replace('\r\n', '\n').replace('\r', '\n').strip()
        lyrics = self.genius_embed_suffix_re.sub('', lyrics).strip()

        lines = lyrics.splitlines()
        if lines and lines[0].lower().endswith("lyrics"):
            lines = lines[1:]
        lyrics = "\n".join(lines).strip()

        lyrics = lyrics.replace("You might also like", "").strip()
        return lyrics

    def score_lyrics_result(self, item, candidate, song):
        if not isinstance(item, dict) or not self.get_lyrics_text(item):
            return 0.0

        song_title = song.get('title', '')
        song_uploader = song.get('uploader', '')
        song_duration = song.get('duration') or 0
        item_title = item.get('trackName') or item.get('name') or ''
        item_artist = item.get('artistName') or ''

        score = 0.0
        if candidate["type"] == "get":
            score += self.text_similarity(candidate.get('track', ''), item_title) * 0.45
            score += self.text_similarity(candidate.get('artist', ''), item_artist) * 0.35
        else:
            score += self.text_similarity(candidate.get('q', ''), f"{item_title} {item_artist}") * 0.35

        score += self.text_similarity(song_title, item_title) * 0.35
        score += self.text_similarity(song_uploader, item_artist) * 0.15

        item_duration = item.get('duration') or 0
        if song_duration and item_duration:
            diff = abs(float(song_duration) - float(item_duration))
            if diff <= 2:
                score += 0.25
            elif diff <= 8:
                score += 0.15
            elif diff <= 20:
                score += 0.05

        if item.get('plainLyrics'):
            score += 0.05

        return score

    def choose_best_lyrics_result(self, items, candidate, song):
        if not isinstance(items, list):
            return None

        scored = [
            (self.score_lyrics_result(item, candidate, song), item)
            for item in items
            if isinstance(item, dict) and self.get_lyrics_text(item)
        ]
        if not scored:
            return None

        scored.sort(key=lambda pair: pair[0], reverse=True)
        best_score, best_item = scored[0]
        return best_item if best_score >= 0.45 else None

    def build_genius_candidates(self, song):
        candidates = []
        seen = set()

        def add(title, artist=None):
            title = title.strip() if title else ""
            artist = artist.strip() if artist else None
            key = (title.lower(), artist.lower() if artist else "")
            if title and key not in seen:
                seen.add(key)
                candidates.append((title, artist))

        song_title = song.get('title', '')
        clean_title = self.clean_lyrics_query_text(song_title) or song_title
        uploader = song.get('uploader', '')
        clean_uploader = self.clean_lyrics_query_text(self.uploader_noise_re.sub('', uploader).strip())
        if clean_uploader == "Unknown":
            clean_uploader = ""

        title_parts = [part.strip() for part in self.title_split_re.split(clean_title, maxsplit=1)]
        if len(title_parts) == 2:
            possible_artist, possible_title = title_parts
            add(possible_title, possible_artist)
            add(possible_title, clean_uploader)
            add(f"{possible_title} {possible_artist}")

        add(clean_title, clean_uploader)
        add(clean_title)
        add(song_title, clean_uploader)
        add(song_title)

        for match in self.paren_re.findall(song_title):
            if not self.metadata_keyword_re.search(match):
                add(match, clean_uploader)
                add(match)

        return candidates[:8]

    def score_genius_result(self, genius_song, title_query, artist_query, song):
        result_title = getattr(genius_song, 'title', '') or ''
        result_artist = getattr(genius_song, 'artist', '') or ''
        score = self.text_similarity(title_query, result_title) * 0.55
        score += self.text_similarity(song.get('title', ''), result_title) * 0.25
        if artist_query:
            score += self.text_similarity(artist_query, result_artist) * 0.25
        else:
            score += self.text_similarity(song.get('uploader', ''), result_artist) * 0.15
        return score

    async def find_genius_lyrics(self, song):
        if not self.genius:
            return None

        loop = asyncio.get_running_loop()

        for title_query, artist_query in self.build_genius_candidates(song):
            try:
                def search():
                    return self.genius.search_song(title_query, artist=artist_query)

                genius_song = await loop.run_in_executor(None, search)
                if not genius_song:
                    continue

                lyrics_text = self.clean_genius_lyrics(getattr(genius_song, 'lyrics', ''))
                if not lyrics_text:
                    continue

                if self.score_genius_result(genius_song, title_query, artist_query, song) < 0.35:
                    continue

                return {
                    'trackName': getattr(genius_song, 'title', title_query),
                    'artistName': getattr(genius_song, 'artist', artist_query or 'Unknown Artist'),
                    'plainLyrics': lyrics_text,
                    'provider': 'Genius',
                    'url': getattr(genius_song, 'url', '')
                }
            except Exception:
                continue

        return None

    def build_lyrics_candidates(self, song):
        song_title = song.get('title', 'Unknown Title')
        clean_title = self.clean_lyrics_query_text(song_title) or song_title
        uploader = song.get('uploader', 'Unknown')
        clean_uploader = self.clean_lyrics_query_text(self.uploader_noise_re.sub('', uploader).strip())
        if clean_uploader == "Unknown":
            clean_uploader = ""

        titles_to_try = [clean_title, song_title]
        artists_to_try = [clean_uploader] if clean_uploader else []

        if self.has_japanese(clean_title):
            try:
                titles_to_try.extend([self.romanize_text(clean_title), self.romanize_text(clean_title, compact=True)])
            except Exception as e:
                print(f"Romaji title conversion error: {e}")

        if self.has_japanese(clean_uploader):
            try:
                artists_to_try.append(self.romanize_text(clean_uploader))
            except Exception as e:
                print(f"Romaji uploader conversion error: {e}")

        for match in self.paren_re.findall(song_title):
            if self.metadata_keyword_re.search(match):
                continue
            titles_to_try.append(match)
            if self.has_japanese(match):
                try:
                    titles_to_try.extend([self.romanize_text(match), self.romanize_text(match, compact=True)])
                except Exception as e:
                    print(f"Romaji title conversion error: {e}")

        title_parts = [part.strip() for part in self.title_split_re.split(clean_title, maxsplit=1)]
        if len(title_parts) == 2:
            possible_artist, possible_title = title_parts
            artists_to_try = [possible_artist, *artists_to_try, possible_title]
            titles_to_try = [possible_title, clean_title, song_title, possible_artist, *titles_to_try]

        titles_to_try = self.unique_non_empty(titles_to_try)
        artists_to_try = self.unique_non_empty(artists_to_try)

        candidates = []
        seen = set()

        def add_candidate(candidate):
            if candidate["type"] == "get":
                key = f"get:{candidate['artist'].lower()}:{candidate['track'].lower()}"
            else:
                key = f"search:{candidate['q'].lower()}"
            if key not in seen and len(candidates) < self.max_lyrics_candidates:
                seen.add(key)
                candidates.append(candidate)

        for track in titles_to_try[:3]:
            add_candidate({"type": "search", "q": track})

        if len(title_parts) == 2:
            first, second = title_parts
            if first.lower() != second.lower():
                add_candidate({"type": "get", "artist": first, "track": second})
                add_candidate({"type": "get", "artist": second, "track": first})
                add_candidate({"type": "search", "q": f"{first} {second}"})
                add_candidate({"type": "search", "q": f"{second} {first}"})

        for artist in artists_to_try[:3]:
            for track in titles_to_try[:4]:
                if track.lower() != artist.lower():
                    add_candidate({"type": "get", "artist": artist, "track": track})

        for artist in artists_to_try[:2]:
            for track in titles_to_try[:4]:
                if track.lower() != artist.lower():
                    add_candidate({"type": "search", "q": f"{track} {artist}"})

        for track in titles_to_try[:5]:
            add_candidate({"type": "search", "q": track})

        return candidates

    async def fetch_lyrics_candidate(self, candidate, song):
        if candidate["type"] == "get":
            url = (
                "https://lrclib.net/api/get?"
                f"artist_name={urllib.parse.quote(candidate['artist'])}&"
                f"track_name={urllib.parse.quote(candidate['track'])}"
            )
        else:
            url = f"https://lrclib.net/api/search?q={urllib.parse.quote(candidate['q'])}"

        async with self.session.get(url, headers=self.lyrics_headers, timeout=4) as response:
            if response.status != 200:
                return None

            try:
                data = await response.json(content_type=None)
            except Exception:
                return None

            if candidate["type"] == "get":
                return data if isinstance(data, dict) and self.get_lyrics_text(data) else None

            if not isinstance(data, list) or not data:
                return None
            return self.choose_best_lyrics_result(data, candidate, song)

    async def find_lyrics(self, song):
        cache_key = song.get('url') or f"{song.get('title', '')}:{song.get('uploader', '')}"
        if cache_key in self.lyrics_cache:
            cached = self.lyrics_cache[cache_key]
            if cached is not None:
                return cached
            miss_time = song.get('lyrics_miss_time')
            if miss_time and time.time() - miss_time < self.lyrics_negative_cache_ttl:
                return None
            self.lyrics_cache.pop(cache_key, None)

        genius_data = await self.find_genius_lyrics(song)
        if genius_data and self.get_lyrics_text(genius_data):
            self.lyrics_cache[cache_key] = genius_data
            if len(self.lyrics_cache) > 100:
                self.lyrics_cache.pop(next(iter(self.lyrics_cache)))
            return genius_data

        for candidate in self.build_lyrics_candidates(song):
            try:
                song_data = await self.fetch_lyrics_candidate(candidate, song)
                if song_data and self.get_lyrics_text(song_data):
                    song_data['provider'] = 'LRCLIB'
                    self.lyrics_cache[cache_key] = song_data
                    if len(self.lyrics_cache) > 100:
                        self.lyrics_cache.pop(next(iter(self.lyrics_cache)))
                    return song_data
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue
            except Exception:
                continue

        song['lyrics_miss_time'] = time.time()
        self.lyrics_cache[cache_key] = None
        return None

    def get_cached_audio_path(self, song):
        """Return an existing cached file for a song if one is available."""
        file_path = song.get('file_path')
        if file_path and Path(file_path).exists():
            return file_path

        song_id = song.get('id')
        if song_id:
            matches = list(self.cache_dir.glob(f"{song_id}.*"))
            if matches:
                path = str(matches[0])
                song['file_path'] = path
                return path

        return None

    async def ensure_song_downloaded(self, song):
        """Download a song completely before it is played."""
        cached_path = self.get_cached_audio_path(song)
        if cached_path:
            return cached_path

        song_url = song.get('url') or song.get('source')
        if not song_url:
            return None

        existing_task = self.download_tasks.get(song_url)
        if existing_task:
            return await existing_task

        loop = asyncio.get_running_loop()

        def download():
            with yt_dlp.YoutubeDL(self.download_ydl_opts) as ydl:
                info = ydl.extract_info(song_url, download=True)
                if 'entries' in info:
                    info = next((entry for entry in info['entries'] if entry), None)
                if not info:
                    return None

                filename = ydl.prepare_filename(info)
                path = Path(filename)
                if not path.exists():
                    matches = list(self.cache_dir.glob(f"{info.get('id')}.*"))
                    path = matches[0] if matches else path

                song['id'] = info.get('id', song.get('id'))
                song['file_path'] = str(path)
                return str(path)

        task = asyncio.ensure_future(loop.run_in_executor(None, download))
        self.download_tasks[song_url] = task
        try:
            return await task
        finally:
            self.download_tasks.pop(song_url, None)

    def prefetch_queue(self, guild_id):
        """Start downloading the next few queued songs without blocking playback."""
        queue = self.queue.get(guild_id)
        if not queue:
            return

        for song in list(queue)[:self.prefetch_limit]:
            if self.get_cached_audio_path(song):
                continue

            song_url = song.get('url') or song.get('source')
            if not song_url or song_url in self.download_tasks:
                continue

            task = asyncio.create_task(self.ensure_song_downloaded(song))

            def log_prefetch_error(done_task):
                if done_task.cancelled():
                    return
                error = done_task.exception()
                if error:
                    print(f"Prefetch error: {error}")

            task.add_done_callback(log_prefetch_error)
    
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
                'id': info.get('id', ''),
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
                    'id': entry.get('id', ''),
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
            song = old_song
        elif self.queue.get(guild_id) and len(self.queue[guild_id]) > 0:
            if old_song:
                self.history.setdefault(guild_id, []).append(old_song)
                if len(self.history[guild_id]) > 20:
                    self.history[guild_id].pop(0)
            song = self.queue[guild_id].popleft()
            self.now_playing[guild_id] = song
            
            if self.loop_mode.get(guild_id) == 'queue':
                self.queue[guild_id].append(song)
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
                song = autoplay_song
            else:
                self.now_playing.pop(guild_id, None)
                song = None
        else:
            if old_song:
                self.history.setdefault(guild_id, []).append(old_song)
                if len(self.history[guild_id]) > 20:
                    self.history[guild_id].pop(0)
            self.now_playing.pop(guild_id, None)
            song = None
        
        if not song:
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
        
        if song and ctx.voice_client:
            status_msg = None
            try:
                status_msg = await ctx.send("📥 **Sedang mengunduh lagu, tunggu sebentar...**")
                source = await self.ensure_song_downloaded(song)
                if not source:
                    await status_msg.edit(content=f"❌ Gagal mengunduh **{song['title']}**, melewati lagu ini...")
                    await asyncio.sleep(2)
                    await self.play_next(ctx)
                    return
                
                audio_source = discord.FFmpegPCMAudio(
                    source,
                    options='-vn'
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
                self.prefetch_queue(guild_id)
                
                try:
                    await status_msg.delete()
                except:
                    pass
                
            except Exception as e:
                print(f"Playback error: {e}")
                if status_msg:
                    try:
                        await status_msg.edit(content=f"❌ Error playing song: {e}")
                    except:
                        await ctx.send(f"❌ Error playing song: {e}")
                else:
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
            self.prefetch_queue(guild_id)
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
            self.prefetch_queue(guild_id)
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
                
            song = self.now_playing[guild_id]
            song_title = song['title']
            song_data = await self.find_lyrics(song)
                    
            if not song_data:
                return await ctx.send(f"❌ Could not find lyrics for **{song_title}**.")
                
            lyrics_text = self.get_lyrics_text(song_data)
            if not lyrics_text:
                return await ctx.send(f"❌ Could not find lyrics for **{song_title}**.")
            is_romanized = False
            
            if self.has_japanese(lyrics_text):
                try:
                    lyrics_text = self.romanize_text(lyrics_text, preserve_lines=True)
                    is_romanized = True
                except Exception as e:
                    print(f"Failed to romanize lyrics via pykakasi: {e}")
    
            # Prepare embed
            title = song_data.get('trackName', song_title)
            artist = song_data.get('artistName', 'Unknown Artist')[:300]
            
            description_prefix = f"**Artist:** {artist}\n\n"
            max_lyrics_length = 4096 - len(description_prefix)
            if len(lyrics_text) > max_lyrics_length:
                lyrics_text = lyrics_text[:max_lyrics_length - 18].rstrip() + "\n\n... (truncated)"
                
            embed = discord.Embed(
                title=(f"🎶 Lyrics for: {title}" + (" (Romaji/Romanized)" if is_romanized else ""))[:256],
                description=f"{description_prefix}{lyrics_text}",
                color=discord.Color.blue()
            )
            provider = song_data.get('provider', 'Lyrics provider')
            embed.set_footer(text=f"Lyrics provided by {provider}" + (" | Romanized via pykakasi" if is_romanized else ""))
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
