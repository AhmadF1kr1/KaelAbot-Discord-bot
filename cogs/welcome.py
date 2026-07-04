"""
Welcome & Goodbye System Cog
Handles member join/leave events with custom messages
(Supports Prefix & Slash Commands)
"""

import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import io
import requests
import json
import os

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_config = {} # {guild_id: {channel_id, message}}
        self.goodbye_config = {} # {guild_id: {channel_id, message}}
        self.load_config()

    def load_config(self):
        """Load configuration from file"""
        try:
            # FIX BUG: Pastikan folder data ada sebelum membaca file
            os.makedirs('data', exist_ok=True)
            if os.path.exists('data/welcome_config.json'):
                with open('data/welcome_config.json', 'r') as f:
                    data = json.load(f)
                    self.welcome_config = {int(k): v for k, v in data.get('welcome', {}).items()}
                    self.goodbye_config = {int(k): v for k, v in data.get('goodbye', {}).items()}
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        """Save configuration to file"""
        try:
            # FIX BUG: Pastikan folder data ada sebelum menyimpan file
            os.makedirs('data', exist_ok=True)
            data = {
                'welcome': {str(k): v for k, v in self.welcome_config.items()},
                'goodbye': {str(k): v for k, v in self.goodbye_config.items()}
            }
            with open('data/welcome_config.json', 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    async def create_welcome_card(self, member):
        """Create a beautiful welcome image card"""
        try:
            width, height = 800, 300
            img = Image.new('RGB', (width, height), color=(44, 47, 51))
            draw = ImageDraw.Draw(img)

            for i in range(height):
                color = (44 + i // 6, 47 + i // 8, 51 + i // 4)
                draw.line([(0, i), (width, i)], fill=color)

            draw.rectangle([0, 0, width, 5], fill=(114, 137, 218))
            draw.rectangle([0, height-5, width, height], fill=(114, 137, 218))

            try:
                avatar_url = member.display_avatar.url
                avatar_response = requests.get(avatar_url)
                avatar = Image.open(io.BytesIO(avatar_response.content)).resize((150, 150))

                mask = Image.new('L', (150, 150), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 150, 150), fill=255)

                border = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
                ImageDraw.Draw(border).ellipse((0, 0, 160, 160), outline=(114, 137, 218), width=5)

                img.paste(border, (45, 70), border)
                img.paste(avatar, (50, 75), mask)
            except:
                draw.ellipse([50, 75, 200, 225], fill=(114, 137, 218))

            try:
                font_title = ImageFont.truetype("arial.ttf", 45)
                font_name = ImageFont.truetype("arial.ttf", 35)
                font_stats = ImageFont.truetype("arial.ttf", 25)
            except:
                font_title = ImageFont.load_default()
                font_name = ImageFont.load_default()
                font_stats = ImageFont.load_default()

            draw.text((230, 80), "WELCOME!", fill=(255, 255, 255), font=font_title)
            draw.text((230, 135), f"{member.name}", fill=(114, 137, 218), font=font_name)
            draw.text((230, 190), f"to {member.guild.name}", fill=(200, 200, 200), font=font_stats)
            draw.text((230, 225), f"Member #{member.guild.member_count}", fill=(150, 150, 150), font=font_stats)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            return discord.File(img_bytes, filename='welcome.png')

        except Exception as e:
            print(f"Error creating welcome card: {e}")
            return None

    # =========================
    # HYBRID COMMANDS START HERE
    # =========================

    @commands.hybrid_group(name='welcome', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome_group(self, ctx):
        """Welcome system commands"""
        embed = discord.Embed(
            title="👋 Welcome System",
            description="Customize welcome messages for new members!",
            color=discord.Color.blue()
        )
        # FIX BUG: Mengganti 'n' dengan '\n' yang benar
        embed.add_field(
            name="Commands",
            value="`/welcome set <#channel> [message]` - Set welcome channel\n"
                  "`/welcome test` - Test welcome message\n"
                  "`/welcome settings` - View current settings\n"
                  "`/welcome disable` - Disable welcome messages\n\n"
                  "**Variables:** {member}, {member_name}, {server}, {member_count}",
            inline=False
        )
        await ctx.send(embed=embed)

    @welcome_group.command(name='set')
    @app_commands.describe(channel="The channel to send welcome messages", message="Custom message (leave empty for default)")
    async def set_welcome(self, ctx, channel: discord.TextChannel = None, *, message: str = None):
        """Set welcome channel and custom message"""
        if not channel:
            return await ctx.send("❌ Please specify a channel!\nExample: `/welcome set #welcome Welcome {member}!`")

        guild_id = ctx.guild.id

        # FIX BUG: Menggunakan string biasa, bukan f-string dengan quadruple curly braces
        if message is None:
            message = "Welcome {member} to {server}! 🎉"

        self.welcome_config[guild_id] = {
            'channel_id': channel.id,
            'message': message
        }
        self.save_config()

        embed = discord.Embed(
            title="✅ Welcome Channel Set",
            description=f"New members will be welcomed in {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Message Preview", value=message, inline=False)
        embed.set_footer(text="Use /welcome test to test the message")

        await ctx.send(embed=embed)

    @welcome_group.command(name='test')
    async def test_welcome(self, ctx):
        """Test welcome message"""
        guild_id = ctx.guild.id

        if guild_id not in self.welcome_config:
            return await ctx.send("❌ Welcome system not configured!\nUse `/welcome set` first.")

        config = self.welcome_config[guild_id]
        message = config['message']
        
        message = message.replace('{member.mention}', ctx.author.mention)
        message = message.replace('{member}', ctx.author.mention)
        message = message.replace('{member_name}', ctx.author.name)
        message = message.replace('{server}', ctx.guild.name)
        message = message.replace('{member_count}', str(ctx.guild.member_count))

        welcome_card = await self.create_welcome_card(ctx.author)

        if welcome_card:
            await ctx.send(message, file=welcome_card)
        else:
            await ctx.send(message)

    @welcome_group.command(name='settings')
    async def show_settings(self, ctx):
        """Show current welcome settings"""
        guild_id = ctx.guild.id

        embed = discord.Embed(title="⚙️ Welcome & Goodbye Settings", color=discord.Color.blue())

        if guild_id in self.welcome_config:
            config = self.welcome_config[guild_id]
            channel = ctx.guild.get_channel(config['channel_id'])
            embed.add_field(
                name="👋 Welcome",
                value=f"Channel: {channel.mention if channel else 'Not found'}\nMessage: `{config['message']}`",
                inline=False
            )
        else:
            embed.add_field(name="👋 Welcome", value="Not configured", inline=False)

        if guild_id in self.goodbye_config:
            config = self.goodbye_config[guild_id]
            channel = ctx.guild.get_channel(config['channel_id'])
            embed.add_field(
                name="👋 Goodbye",
                value=f"Channel: {channel.mention if channel else 'Not found'}\nMessage: `{config['message']}`",
                inline=False
            )
        else:
            embed.add_field(name="👋 Goodbye", value="Not configured", inline=False)

        await ctx.send(embed=embed)

    @welcome_group.command(name='disable')
    async def disable_welcome(self, ctx):
        """Disable welcome messages"""
        guild_id = ctx.guild.id

        if guild_id in self.welcome_config:
            del self.welcome_config[guild_id]
            self.save_config()
            await ctx.send("✅ Welcome messages disabled!")
        else:
            await ctx.send("❌ Welcome system is not enabled!")

    # ===== GOODBYE COMMANDS =====

    @commands.hybrid_group(name='goodbye', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def goodbye_group(self, ctx):
        """Goodbye system commands"""
        embed = discord.Embed(
            title="👋 Goodbye System",
            description="Customize goodbye messages for leaving members!",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Commands",
            value="`/goodbye set <#channel> [message]` - Set goodbye channel\n"
                  "`/goodbye test` - Test goodbye message\n"
                  "`/goodbye disable` - Disable goodbye messages\n\n"
                  "**Variables:** {member}, {member_name}, {server}, {member_count}",
            inline=False
        )
        await ctx.send(embed=embed)

    @goodbye_group.command(name='set')
    @app_commands.describe(channel="The channel to send goodbye messages", message="Custom message (leave empty for default)")
    async def set_goodbye(self, ctx, channel: discord.TextChannel = None, *, message: str = None):
        """Set goodbye channel and message"""
        if not channel:
            return await ctx.send("❌ Please specify a channel!")

        guild_id = ctx.guild.id

        if message is None:
            message = "Goodbye {member_name}! We'll miss you 😢"

        self.goodbye_config[guild_id] = {
            'channel_id': channel.id,
            'message': message
        }
        self.save_config()

        await ctx.send(f"✅ Goodbye channel set to {channel.mention}")

    @goodbye_group.command(name='test')
    async def test_goodbye(self, ctx):
        """Test goodbye message"""
        guild_id = ctx.guild.id

        if guild_id not in self.goodbye_config:
            return await ctx.send("❌ Goodbye system not configured!")

        config = self.goodbye_config[guild_id]
        message = config['message']
        
        # FIX: Gunakan <@ID> untuk {member} agar Discord merender nama user
        message = message.replace('{member}', f"<@{ctx.author.id}>")
        message = message.replace('{member_name}', ctx.author.name)
        message = message.replace('{server}', ctx.guild.name)
        message = message.replace('{member_count}', str(ctx.guild.member_count)) # FIX: Tambahkan ini

        await ctx.send(f"🔍 **Preview Pesan Goodbye:**\n{message}")

    @goodbye_group.command(name='disable')
    async def disable_goodbye(self, ctx):
        """Disable goodbye messages"""
        guild_id = ctx.guild.id

        if guild_id in self.goodbye_config:
            del self.goodbye_config[guild_id]
            self.save_config()
            await ctx.send("✅ Goodbye messages disabled!")
        else:
            await ctx.send("❌ Goodbye system is not enabled!")

    # ===== EVENT LISTENERS =====

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join event"""
        guild_id = member.guild.id

        if guild_id not in self.welcome_config:
            return

        config = self.welcome_config[guild_id]
        channel = member.guild.get_channel(config['channel_id'])

        if not channel:
            return

        message = config['message']
        message = message.replace('{member.mention}', member.mention)
        message = message.replace('{member}', member.mention)
        message = message.replace('{member_name}', member.name)
        message = message.replace('{server}', member.guild.name)
        message = message.replace('{member_count}', str(member.guild.member_count))

        welcome_card = await self.create_welcome_card(member)

        try:
            if welcome_card:
                await channel.send(message, file=welcome_card)
            else:
                await channel.send(message)
        except Exception as e:
            print(f"Error sending welcome message: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leave event"""
        guild_id = member.guild.id

        if guild_id not in self.goodbye_config:
            return

        config = self.goodbye_config[guild_id]
        channel = member.guild.get_channel(config['channel_id'])

        if not channel:
            return

        message = config['message']
        
        # FIX: Gunakan <@ID> untuk {member} agar Discord merender nama user yang sudah keluar
        message = message.replace('{member.mention}', f"<@{member.id}>")
        message = message.replace('{member}', f"<@{member.id}>")
        message = message.replace('{member_name}', member.name)
        message = message.replace('{server}', member.guild.name)
        message = message.replace('{member_count}', str(member.guild.member_count))

        try:
            await channel.send(message)
        except Exception as e:
            print(f"Error sending goodbye message: {e}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
    print('👋 Welcome cog loaded!')