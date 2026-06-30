"""
Discord Fiku-Bot
Features: Music, Welcome/Goodbye, RPG Text
Author: Fik-_-
Version: 1.0.0
"""

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

class MultipurposeBot(commands.Bot):
    def __init__(self):
        # Setup intents
        intents = discord.Intents.all()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        # Bot variables
        self.bot_version = "1.0.0"
        
    async def setup_hook(self):
        """Load all extensions/cogs"""
        extensions = [
            'cogs.music',
            'cogs.welcome', 
            'cogs.rpg_game'
        ]
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f'✅ Successfully loaded: {ext}')
            except Exception as e:
                print(f'❌ Failed to load {ext}: {e}')
        
        # Sync slash commands
        try:
            await self.tree.sync()
            print('✅ Slash commands synced globally')
        except Exception as e:
            print(f'❌ Failed to sync commands: {e}')
    
    async def on_ready(self):
        """Triggered when bot is ready"""
        print('='*50)
        print(f'🤖 Bot Name: {self.user.name}')
        print(f'🆔 Bot ID: {self.user.id}')
        print(f'📊 Discord.py Version: {discord.__version__}')
        print(f'📈 Serving {len(self.guilds)} servers')
        print('='*50)
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name='!help | Music & RPG'
            ),
            status=discord.Status.online
        )
    
    async def on_message(self, message):
        """Handle messages"""
        # Ignore bot's own messages
        if message.author.bot:
            return
        
        # Process commands
        await self.process_commands(message)

# Create bot instance
bot = MultipurposeBot()

# ============ BASIC COMMANDS ============

@bot.command(name='ping')
async def ping(ctx):
    """Check bot latency"""
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: `{round(bot.latency * 1000)}ms`",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='help')
async def help_command(ctx, category: str = None):
    """Show help menu"""
    
    if category is None:
        # Main help menu
        embed = discord.Embed(
            title="🤖 Bot Commands Help",
            description="Multi-purpose Discord Bot with Music, Welcome System, and RPG Game!\n\n"
                       "Use `!help <category>` for detailed commands:\n"
                       "`!help music` - Music commands\n"
                       "`!help welcome` - Welcome system commands\n"
                       "`!help rpg` - RPG game commands",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Bot Version {bot.bot_version} | Made with ❤️")
        
    elif category.lower() == 'music':
        embed = discord.Embed(
            title="🎵 Music Commands",
            color=discord.Color.purple()
        )
        embed.add_field(name="!play <song>", value="Play a song from YouTube", inline=False)
        embed.add_field(name="!pause", value="Pause current song", inline=False)
        embed.add_field(name="!resume", value="Resume paused song", inline=False)
        embed.add_field(name="!skip", value="Skip to next song", inline=False)
        embed.add_field(name="!volume <0-200>", value="Set volume level", inline=False)
        embed.add_field(name="!queue", value="Show current queue", inline=False)
        embed.add_field(name="!shuffle", value="Shuffle the queue", inline=False)
        embed.add_field(name="!loop <off/song/queue>", value="Set loop mode", inline=False)
        embed.add_field(name="!stop", value="Stop music and disconnect", inline=False)
        embed.add_field(name="!nowplaying", value="Show currently playing song", inline=False)
        
    elif category.lower() == 'welcome':
        embed = discord.Embed(
            title="👋 Welcome System Commands",
            color=discord.Color.green()
        )
        embed.add_field(name="!set_welcome <channel> <message>", 
                       value="Set welcome channel and message\n"
                             "Variables: {member}, {server}, {member_count}", inline=False)
        embed.add_field(name="!set_goodbye <channel> <message>", 
                       value="Set goodbye channel and message", inline=False)
        embed.add_field(name="!test_welcome", value="Test welcome message", inline=False)
        embed.add_field(name="!welcome_settings", value="View current settings", inline=False)
        
    elif category.lower() == 'rpg':
        embed = discord.Embed(
            title="⚔️ RPG Game Commands",
            color=discord.Color.gold()
        )
        embed.add_field(name="!rpg start", value="Start your adventure", inline=False)
        embed.add_field(name="!rpg class <warrior/mage/archer>", value="Choose your class", inline=False)
        embed.add_field(name="!rpg profile", value="View your character stats", inline=False)
        embed.add_field(name="!rpg hunt", value="Hunt monsters for rewards", inline=False)
        embed.add_field(name="!rpg boss", value="Fight a boss (1h cooldown)", inline=False)
        embed.add_field(name="!rpg shop", value="Open the item shop", inline=False)
        embed.add_field(name="!rpg buy <item>", value="Purchase an item", inline=False)
        embed.add_field(name="!rpg inventory", value="Check your items", inline=False)
        embed.add_field(name="!rpg daily", value="Claim daily reward", inline=False)
        embed.add_field(name="!rpg heal", value="Heal for 20 gold", inline=False)
        embed.add_field(name="!rpg top", value="View leaderboard", inline=False)
        
    else:
        embed = discord.Embed(
            title="❌ Category Not Found",
            description="Available categories: `music`, `welcome`, `rpg`",
            color=discord.Color.red()
        )
    
    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='info')
async def info(ctx):
    """Show bot information"""
    embed = discord.Embed(
        title="ℹ️ Bot Information",
        color=discord.Color.blue()
    )
    embed.add_field(name="Bot Name", value=bot.user.name, inline=True)
    embed.add_field(name="Version", value=bot.bot_version, inline=True)
    embed.add_field(name="Library", value=f"discord.py {discord.__version__}", inline=True)
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Prefix", value="!", inline=True)
    
    await ctx.send(embed=embed)

# ============ ERROR HANDLING ============

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ Command Not Found",
            description=f"Command `{ctx.message.content}` not found!\nUse `!help` for available commands.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="You don't have permission to use this command!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Missing Arguments",
            description=f"Missing required argument: `{error.param.name}`\nUse `!help` for command usage.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title="❌ Invalid Argument",
            description="Please provide valid arguments!\nUse `!help` for command usage.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
    else:
        # Log unexpected errors
        print(f'❌ Unexpected error: {error}')
        embed = discord.Embed(
            title="❌ Error",
            description="An unexpected error occurred. Please try again later.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# ============ RUN BOT ============

if __name__ == '__main__':
    # Get token from .env
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ ERROR: Discord token not found!")
        print("Please make sure you have a .env file with DISCORD_TOKEN")
        exit(1)
    
    print("🚀 Starting bot...")
    
    try:
        # Run bot
        bot.run(token)
    except discord.errors.LoginFailure:
        print("❌ ERROR: Invalid Discord token!")
        print("Please check your token in .env file")
        exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        exit(1)