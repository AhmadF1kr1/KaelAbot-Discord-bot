"""
Discord KaelAbot
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
        """Load all extensions/cogs and sync tree"""
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
        
        # Sync tree di setup_hook (lebih efisien)
        try:
            synced = await self.tree.sync()
            print(f'✅ Synced {len(synced)} slash commands globally')
        except Exception as e:
            print(f'❌ Failed to sync commands: {e}')
    
    async def on_message(self, message):
        """Handle messages"""
        if message.author.bot:
            return
        
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
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name='KaelAbot Online! | type !help'
        ),
        status=discord.Status.online
    )

# ============ HYBRID COMMANDS ============

@bot.hybrid_command(name='ping')
async def ping(ctx):
    """Check bot latency"""
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: `{round(bot.latency * 1000)}ms`",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.hybrid_command(name='help')
@app_commands.describe(category="Pilih kategori command yang ingin dilihat")
@app_commands.choices(category=[
    app_commands.Choice(name="Music", value="music"),
    app_commands.Choice(name="Welcome", value="welcome"),
    app_commands.Choice(name="RPG", value="rpg"),
    app_commands.Choice(name="RoleMenu", value="rolemenu")
])
async def help_command(ctx, category: str = None):
    """Show help menu"""
    # Gunakan ctx.prefix agar dinamis
    p = ctx.prefix
    
    if category is None:
        embed = discord.Embed(
            title="🤖 Bot Commands Help",
            description="Multi-purpose Discord Bot with Music, Welcome System, RPG Game, and Role Select!\n\n"
                       f"Use `{p}help <category>` for detailed commands:\n"
                       f"`{p}help music` - Music commands\n"
                       f"`{p}help welcome` - Welcome system commands\n"
                       f"`{p}help rpg` - RPG game commands\n"
                       f"`{p}help rolemenu` - Role menu creation commands\n\n"
                       "💡 **Tip:** All commands also support **Slash Commands** (`/`)!",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Bot Version {bot.bot_version} | Made with ❤️")
        
    elif category.lower() == 'music':
        embed = discord.Embed(
            title="🎵 Music Commands",
            color=discord.Color.purple()
        )
        embed.add_field(name=f"{p}play <song> or /play", value="Play a song from YouTube", inline=False)
        embed.add_field(name=f"{p}search <query> or /search", value="Search for up to 5 songs on YouTube", inline=False)
        embed.add_field(name=f"{p}select <index> or /select", value="Play a song from the last search results", inline=False)
        embed.add_field(name=f"{p}pause or /pause", value="Pause current song", inline=False)
        embed.add_field(name=f"{p}resume or /resume", value="Resume paused song", inline=False)
        embed.add_field(name=f"{p}skip or /skip", value="Skip to next song", inline=False)
        embed.add_field(name=f"{p}volume <0-200> or /volume", value="Set/check volume level", inline=False)
        embed.add_field(name=f"{p}queue or /queue", value="Show current queue", inline=False)
        embed.add_field(name=f"{p}shuffle or /shuffle", value="Shuffle the queue", inline=False)
        embed.add_field(name=f"{p}loop <off/song/queue> or /loop", value="Set loop mode", inline=False)
        embed.add_field(name=f"{p}stop or /stop", value="Stop music and disconnect", inline=False)
        embed.add_field(name=f"{p}nowplaying or /nowplaying", value="Show currently playing song", inline=False)
        embed.add_field(name=f"{p}lyrics or /lyrics", value="Show lyrics of the currently playing song", inline=False)
        embed.add_field(name=f"{p}remove <index> or /remove", value="Remove a song from queue by index", inline=False)
        embed.add_field(name=f"{p}clearqueue or /clearqueue", value="Clear the entire queue", inline=False)
        
    elif category.lower() == 'welcome':
        embed = discord.Embed(
            title="👋 Welcome & Goodbye System Commands",
            color=discord.Color.green()
        )
        embed.add_field(name=f"{p}welcome set <channel> [message] or /welcome set", 
                       value="Set welcome channel and message\n"
                             "Variables: {member}, {member_name}, {server}, {member_count}", inline=False)
        embed.add_field(name=f"{p}welcome test or /welcome test", value="Test welcome message", inline=False)
        embed.add_field(name=f"{p}welcome settings or /welcome settings", value="View current welcome & goodbye settings", inline=False)
        embed.add_field(name=f"{p}welcome disable or /welcome disable", value="Disable welcome messages", inline=False)
        embed.add_field(name=f"{p}goodbye set <channel> [message] or /goodbye set", value="Set goodbye channel and message", inline=False)
        embed.add_field(name=f"{p}goodbye test or /goodbye test", value="Test goodbye message", inline=False)
        embed.add_field(name=f"{p}goodbye disable or /goodbye disable", value="Disable goodbye messages", inline=False)
        
    elif category.lower() == 'rpg':
        embed = discord.Embed(
            title="⚔️ RPG Game Commands",
            color=discord.Color.gold()
        )
        embed.add_field(name=f"{p}rpg start or /rpg start", value="Start your adventure", inline=False)
        embed.add_field(name=f"{p}rpg class <warrior/mage/archer/healer> or /rpg class", value="Choose your class", inline=False)
        embed.add_field(name=f"{p}rpg profile or /rpg profile", value="View your character stats", inline=False)
        embed.add_field(name=f"{p}rpg hunt or /rpg hunt", value="Hunt monsters for rewards", inline=False)
        embed.add_field(name=f"{p}rpg boss or /rpg boss", value="Fight a boss (1h cooldown)", inline=False)
        embed.add_field(name=f"{p}rpg shop or /rpg shop", value="Open the item shop", inline=False)
        embed.add_field(name=f"{p}rpg buy <item> or /rpg buy", value="Purchase an item", inline=False)
        embed.add_field(name=f"{p}rpg sell <item> or /rpg sell", value="Sell an item", inline=False)
        embed.add_field(name=f"{p}rpg use <item> or /rpg use", value="Use a consumable item", inline=False)
        embed.add_field(name=f"{p}rpg inventory or /rpg inventory", value="Check your items", inline=False)
        embed.add_field(name=f"{p}rpg equip <item> or /rpg equip", value="Equip an item", inline=False)
        embed.add_field(name=f"{p}rpg daily or /rpg daily", value="Claim daily reward", inline=False)
        embed.add_field(name=f"{p}rpg heal or /rpg heal", value="Heal for 30 gold", inline=False)
        embed.add_field(name=f"{p}rpg top or /rpg top", value="View leaderboard", inline=False)
        embed.add_field(name=f"{p}rpg duel @user or /rpg duel", value="Duel another player", inline=False)
        
    elif category.lower() == 'rolemenu':
        embed = discord.Embed(
            title="🎭 Role Menu Commands",
            color=discord.Color.blurple()
        )
        embed.add_field(name=f"{p}rolemenu", value="Show help on creating role menus", inline=False)
        embed.add_field(name=f"{p}rolemenu create button <title> | <emoji> @Role | ...", value="Create a role selection menu using buttons", inline=False)
        embed.add_field(name=f"{p}rolemenu create dropdown <title> | <emoji> @Role | ...", value="Create a role selection menu using a dropdown", inline=False)
        embed.add_field(name=f"{p}rolemenu auto <title> [description]", value="Create an automatic role menu for all manageable server roles", inline=False)
        
    else:
        embed = discord.Embed(
            title="❌ Category Not Found",
            description="Available categories: `music`, `welcome`, `rpg`, `rolemenu`",
            color=discord.Color.red()
        )
    
    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.hybrid_command(name='info')
async def info(ctx):
    """Show bot information"""
    # Gunakan command_prefix dinamis
    current_prefix = bot.command_prefix
    if callable(current_prefix):
        current_prefix = "!"  # fallback
    
    embed = discord.Embed(
        title="ℹ️ Bot Information",
        color=discord.Color.blue()
    )
    embed.add_field(name="Bot Name", value=bot.user.name, inline=True)
    embed.add_field(name="Version", value=bot.bot_version, inline=True)
    embed.add_field(name="Library", value=f"discord.py {discord.__version__}", inline=True)
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Prefix", value=f"`{current_prefix}` or `/`", inline=True)
    
    await ctx.send(embed=embed)

# ============ ERROR HANDLING ============

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for PREFIX commands"""
    
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ Command Not Found",
            description=f"Command `{ctx.message.content}` not found!\nUse `{ctx.prefix}help` for available commands.",
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
            description=f"Missing required argument: `{error.param.name}`\nUse `{ctx.prefix}help` for command usage.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title="❌ Invalid Argument",
            description="Please provide valid arguments!\nUse `{ctx.prefix}help` for command usage.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    elif isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏰ Cooldown Active",
            description=f"Please wait **{error.retry_after:.1f} seconds** before using this command again.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    
    elif isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            title="❌ Check Failed",
            description="You don't meet the requirements to use this command!",
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

# Error handler untuk SLASH COMMANDS
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for SLASH commands"""
    
    # Helper function untuk mengirim error response
    async def send_error(title, description, color=discord.Color.red()):
        embed = discord.Embed(title=title, description=description, color=color)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    if isinstance(error, app_commands.CommandOnCooldown):
        await send_error(
            "⏰ Cooldown Active",
            f"Please wait **{error.retry_after:.1f} seconds** before using this command again.",
            discord.Color.orange()
        )
    
    elif isinstance(error, app_commands.MissingPermissions):
        await send_error(
            "❌ Missing Permissions",
            "You don't have permission to use this command!"
        )
    
    elif isinstance(error, app_commands.CommandInvokeError):
        # Log the actual error for debugging
        print(f'❌ Slash command error: {error.original}')
        await send_error(
            "❌ Command Error",
            "An error occurred while executing this command."
        )
    
    elif isinstance(error, app_commands.CheckFailure):
        await send_error(
            "❌ Check Failed",
            "You don't meet the requirements to use this command!"
        )
    
    else:
        print(f'❌ Unexpected slash command error: {error}')
        await send_error(
            "❌ Error",
            "An unexpected error occurred. Please try again later."
        )

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