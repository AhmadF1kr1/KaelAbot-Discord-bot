"""
Discord Fiku-Bot
Features: Music, Welcome/Goodbye, RPG Text
Author: Fik-_-
Version: 1.0.0
"""

import discord
from discord.ext import commands
from discord import app_commands
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
            command_prefix=os.getenv("PREFIX", "!"),
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
            'cogs.rpg_game',
            'cogs.role_select'
        ]
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f'✅ Successfully loaded: {ext}')
            except Exception as e:
                print(f'❌ Failed to load {ext}: {e}')
    
    async def on_message(self, message):
        """Handle messages"""
        # Ignore bot's own messages
        if message.author.bot:
            return
        
        # Process commands
        await self.process_commands(message)

# Create bot instance
bot = MultipurposeBot()

@bot.event
async def on_ready():
    """Triggered when bot is ready"""
    print('='*50)
    print(f'🤖 Bot Name: {bot.user.name}')
    print(f'🆔 Bot ID: {bot.user.id}')
    print(f'📊 Discord.py Version: {discord.__version__}')
    print(f'📈 Serving {len(bot.guilds)} servers')
    print('='*50)
    
    # Set bot status
    prefix = os.getenv("PREFIX", "!")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f'{prefix}help | Music & RPG'
        ),
        status=discord.Status.online
    )
    
    # Sync slash commands
    try:
        await bot.tree.sync()
        print('✅ Slash commands synced globally via @bot.event')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')

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
            description="Multi-purpose Discord Bot with Music, Welcome System, RPG Game, and Role Select!\n\n"
                       "Use `!help <category>` for detailed commands:\n"
                       "`!help music` - Music commands\n"
                       "`!help welcome` - Welcome system commands\n"
                       "`!help rpg` - RPG game commands\n"
                       "`!help rolemenu` - Role menu creation commands",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Bot Version {bot.bot_version} | Made with ❤️")
        
    elif category.lower() == 'music':
        embed = discord.Embed(
            title="🎵 Music Commands",
            color=discord.Color.purple()
        )
        embed.add_field(name="!play <song> or /play", value="Play a song from YouTube", inline=False)
        embed.add_field(name="!pause or /pause", value="Pause current song", inline=False)
        embed.add_field(name="!resume or /resume", value="Resume paused song", inline=False)
        embed.add_field(name="!skip or /skip", value="Skip to next song", inline=False)
        embed.add_field(name="!volume <0-200> or /volume", value="Set/check volume level", inline=False)
        embed.add_field(name="!queue or /queue", value="Show current queue", inline=False)
        embed.add_field(name="!shuffle or /shuffle", value="Shuffle the queue", inline=False)
        embed.add_field(name="!loop <off/song/queue> or /loop", value="Set loop mode", inline=False)
        embed.add_field(name="!stop or /stop", value="Stop music and disconnect", inline=False)
        embed.add_field(name="!nowplaying or /nowplaying", value="Show currently playing song", inline=False)
        embed.add_field(name="!remove <index> or /remove", value="Remove a song from queue by index", inline=False)
        embed.add_field(name="!clearqueue or /clearqueue", value="Clear the entire queue", inline=False)
        
    elif category.lower() == 'welcome':
        embed = discord.Embed(
            title="👋 Welcome & Goodbye System Commands",
            color=discord.Color.green()
        )
        embed.add_field(name="!welcome set <channel> [message] or /welcome set", 
                       value="Set welcome channel and message\n"
                             "Variables: {member}, {member_name}, {server}, {member_count}", inline=False)
        embed.add_field(name="!welcome test or /welcome test", value="Test welcome message", inline=False)
        embed.add_field(name="!welcome settings or /welcome settings", value="View current welcome & goodbye settings", inline=False)
        embed.add_field(name="!welcome disable or /welcome disable", value="Disable welcome messages", inline=False)
        embed.add_field(name="!goodbye set <channel> [message] or /goodbye set", value="Set goodbye channel and message", inline=False)
        embed.add_field(name="!goodbye test or /goodbye test", value="Test goodbye message", inline=False)
        embed.add_field(name="!goodbye disable or /goodbye disable", value="Disable goodbye messages", inline=False)
        
    elif category.lower() == 'rpg':
        embed = discord.Embed(
            title="⚔️ RPG Game Commands",
            color=discord.Color.gold()
        )
        embed.add_field(name="!rpg start or /rpg start", value="Start your adventure", inline=False)
        embed.add_field(name="!rpg class <warrior/mage/archer/healer> or /rpg class", value="Choose your class", inline=False)
        embed.add_field(name="!rpg profile or /rpg profile", value="View your character stats", inline=False)
        embed.add_field(name="!rpg hunt or /rpg hunt", value="Hunt monsters for rewards", inline=False)
        embed.add_field(name="!rpg boss or /rpg boss", value="Fight a boss (1h cooldown)", inline=False)
        embed.add_field(name="!rpg shop or /rpg shop", value="Open the item shop", inline=False)
        embed.add_field(name="!rpg buy <item> or /rpg buy", value="Purchase an item", inline=False)
        embed.add_field(name="!rpg sell <item> or /rpg sell", value="Sell an item", inline=False)
        embed.add_field(name="!rpg use <item> or /rpg use", value="Use a consumable item", inline=False)
        embed.add_field(name="!rpg inventory or /rpg inventory", value="Check your items", inline=False)
        embed.add_field(name="!rpg equip <item> or /rpg equip", value="Equip an item", inline=False)
        embed.add_field(name="!rpg daily or /rpg daily", value="Claim daily reward", inline=False)
        embed.add_field(name="!rpg heal or /rpg heal", value="Heal for 30 gold", inline=False)
        embed.add_field(name="!rpg top or /rpg top", value="View leaderboard", inline=False)
        embed.add_field(name="!rpg duel @user or /rpg duel", value="Duel another player", inline=False)
        
    elif category.lower() == 'rolemenu':
        embed = discord.Embed(
            title="🎭 Role Menu Commands",
            color=discord.Color.blurple()
        )
        embed.add_field(name="!rolemenu", value="Show help on creating role menus", inline=False)
        embed.add_field(name="!rolemenu create button <title> | <emoji> @Role | ...", value="Create a role selection menu using buttons", inline=False)
        embed.add_field(name="!rolemenu create dropdown <title> | <emoji> @Role | ...", value="Create a role selection menu using a dropdown", inline=False)
        embed.add_field(name="!rolemenu auto <title> [description]", value="Create an automatic role menu for all manageable server roles", inline=False)
        
    else:
        embed = discord.Embed(
            title="❌ Category Not Found",
            description="Available categories: `music`, `welcome`, `rpg`, `rolemenu`",
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