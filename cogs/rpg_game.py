"""
RPG Game System Cog
A full RPG adventure game with classes, battles, and progression
(Supports Prefix & Slash Commands)
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os
import asyncio
from datetime import datetime, timedelta

class Player:
    """Player class for RPG game"""
    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name
        
        # Stats
        self.level = 1
        self.xp = 0
        self.hp = 100
        self.max_hp = 100
        self.mp = 50
        self.max_mp = 50
        self.attack = 10
        self.defense = 5
        self.magic = 8
        
        # Economy
        self.gold = 100
        self.gems = 0
        
        # Class
        self.class_type = 'Warrior'
        
        # Inventory
        self.inventory = []
        self.equipment = {
            'weapon': None,
            'armor': None,
            'accessory': None
        }
        
        # Progress
        self.monsters_killed = 0
        self.bosses_killed = 0
        self.quests_completed = 0
        self.deaths = 0
        
        # Timers
        self.last_daily = None
        self.last_boss = None
        self.last_hunt = None
        
        # Achievements
        self.achievements = []
        
    def to_dict(self):
        return self.__dict__
    
    @classmethod
    def from_dict(cls, data):
        player = cls(data['user_id'], data['name'])
        for key, value in data.items():
            setattr(player, key, value)
        return player
    
    def get_xp_needed(self):
        """Calculate XP needed for next level"""
        return int(100 * (1.5 ** (self.level - 1)))
    
    def is_max_level(self):
        """Check if player is at max level"""
        return self.level >= 100

class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        
        # Game data
        self.classes = {
            'warrior': {
                'name': 'Warrior',
                'description': 'A mighty fighter with high HP and defense',
                'emoji': '⚔️',
                'stats': {'hp': 120, 'mp': 30, 'attack': 15, 'defense': 10, 'magic': 3}
            },
            'mage': {
                'name': 'Mage',
                'description': 'A powerful spellcaster with devastating magic',
                'emoji': '🔮',
                'stats': {'hp': 70, 'mp': 120, 'attack': 5, 'defense': 3, 'magic': 20}
            },
            'archer': {
                'name': 'Archer',
                'description': 'A swift marksman with critical strikes',
                'emoji': '🏹',
                'stats': {'hp': 85, 'mp': 60, 'attack': 18, 'defense': 5, 'magic': 8}
            },
            'healer': {
                'name': 'Healer',
                'description': 'A support class that can heal and buff',
                'emoji': '💚',
                'stats': {'hp': 90, 'mp': 100, 'attack': 7, 'defense': 7, 'magic': 12}
            }
        }
        
        self.monsters = {
            'Slime': {'hp': 30, 'attack': 5, 'defense': 1, 'xp': 15, 'gold': 10, 'level': 1},
            'Rat': {'hp': 20, 'attack': 3, 'defense': 0, 'xp': 10, 'gold': 5, 'level': 1},
            'Bat': {'hp': 25, 'attack': 4, 'defense': 1, 'xp': 12, 'gold': 8, 'level': 2},
            'Goblin': {'hp': 50, 'attack': 10, 'defense': 5, 'xp': 35, 'gold': 25, 'level': 10},
            'Skeleton': {'hp': 65, 'attack': 12, 'defense': 7, 'xp': 45, 'gold': 35, 'level': 15},
            'Dark Mage': {'hp': 55, 'attack': 18, 'defense': 3, 'xp': 50, 'gold': 40, 'level': 18},
            'Orc': {'hp': 100, 'attack': 22, 'defense': 12, 'xp': 80, 'gold': 70, 'level': 25},
            'Wraith': {'hp': 85, 'attack': 28, 'defense': 5, 'xp': 90, 'gold': 85, 'level': 30},
            'Golem': {'hp': 150, 'attack': 18, 'defense': 20, 'xp': 100, 'gold': 95, 'level': 35},
            'Demon': {'hp': 200, 'attack': 35, 'defense': 15, 'xp': 150, 'gold': 150, 'level': 50},
            'Phoenix': {'hp': 180, 'attack': 40, 'defense': 10, 'xp': 170, 'gold': 180, 'level': 60},
            'Lich King': {'hp': 250, 'attack': 45, 'defense': 18, 'xp': 200, 'gold': 220, 'level': 70}
        }
        
        self.bosses = {
            'Dark Knight': {'hp': 300, 'attack': 30, 'defense': 20, 'xp': 300, 'gold': 300, 'gems': 5},
            'Dragon': {'hp': 500, 'attack': 45, 'defense': 25, 'xp': 500, 'gold': 500, 'gems': 10},
            'Ancient Lich': {'hp': 800, 'attack': 55, 'defense': 30, 'xp': 800, 'gold': 800, 'gems': 20},
            'Demon Lord': {'hp': 1200, 'attack': 70, 'defense': 40, 'xp': 1500, 'gold': 1500, 'gems': 50}
        }
        
        self.shop_items = {
            'health_potion': {'name': '❤️ Health Potion', 'price': 30, 'type': 'consumable', 'effect': {'heal': 50}},
            'mana_potion': {'name': '💎 Mana Potion', 'price': 25, 'type': 'consumable', 'effect': {'mana': 30}},
            'elixir': {'name': '🧪 Elixir', 'price': 100, 'type': 'consumable', 'effect': {'heal': 100, 'mana': 100}},
            'wooden_sword': {'name': '🗡️ Wooden Sword', 'price': 100, 'type': 'weapon', 'effect': {'attack': 5}},
            'iron_sword': {'name': '⚔️ Iron Sword', 'price': 300, 'type': 'weapon', 'effect': {'attack': 10}},
            'magic_staff': {'name': '🔮 Magic Staff', 'price': 400, 'type': 'weapon', 'effect': {'magic': 15}},
            'leather_armor': {'name': '🛡️ Leather Armor', 'price': 150, 'type': 'armor', 'effect': {'defense': 5}},
            'dragon_armor': {'name': '🐉 Dragon Armor', 'price': 1000, 'type': 'armor', 'effect': {'defense': 20}},
            'lucky_charm': {'name': '🍀 Lucky Charm', 'price': 500, 'type': 'accessory', 'effect': {'crit_chance': 10}}
        }
        
        self.load_data()
    
    def load_data(self):
        """Load player data from file"""
        try:
            if os.path.exists('data/rpg_data.json'):
                with open('data/rpg_data.json', 'r') as f:
                    data = json.load(f)
                    for user_id, player_data in data.items():
                        self.players[int(user_id)] = Player.from_dict(player_data)
                print(f'📁 Loaded {len(self.players)} RPG players')
        except Exception as e:
            print(f'Error loading RPG data: {e}')
    
    def save_data(self):
        """Save player data to file"""
        try:
            data = {}
            for user_id, player in self.players.items():
                data[user_id] = player.to_dict()
            
            with open('data/rpg_data.json', 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f'Error saving RPG data: {e}')
    
    def get_player(self, user_id, name=None):
        """Get or create player"""
        if user_id not in self.players:
            if name:
                self.players[user_id] = Player(user_id, name)
            else:
                return None
        return self.players[user_id]
    
    def format_hp_bar(self, current, maximum, length=20):
        """Create HP bar string"""
        if maximum == 0: return "[]"
        filled = int(length * max(0, current) / maximum)
        bar = '█' * filled + '░' * (length - filled)
        return f"[{bar}]"
    
    def calculate_damage(self, attacker_attack, defender_defense):
        """Calculate damage with some randomness"""
        base_damage = max(1, attacker_attack - defender_defense // 2)
        variation = random.randint(-3, 5)
        return max(1, base_damage + variation)
    
    # =========================
    # HYBRID GROUP START
    # =========================

    @commands.hybrid_group(name='rpg', invoke_without_command=True)
    async def rpg(self, ctx):
        """RPG Game main command"""
        embed = discord.Embed(
            title="⚔️ RPG Adventure Game",
            description="Embark on an epic adventure! Fight monsters, defeat bosses, and become the strongest hero!",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📋 Commands",
            value="""
            `/rpg start` - Begin your adventure
            `/rpg class <name>` - Choose your class
            `/rpg profile [@user]` - View character stats
            `/rpg hunt` - Hunt monsters
            `/rpg boss` - Fight a boss (1h cooldown)
            `/rpg shop` - Visit the shop
            `/rpg buy <item>` - Purchase an item
            `/rpg sell <item>` - Sell an item
            `/rpg use <item>` - Use a consumable item
            `/rpg inventory` - Check your items
            `/rpg equip <item>` - Equip an item
            `/rpg daily` - Claim daily reward
            `/rpg heal` - Heal for 30 gold
            `/rpg top` - Leaderboard
            `/rpg duel @user` - Duel another player
            """,
            inline=False
        )
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)
    
    @rpg.command(name='start')
    async def start_game(self, ctx):
        """Start your RPG adventure"""
        if ctx.author.id in self.players:
            return await ctx.send("❌ You already have a character! Use `/rpg profile` to view it.")
            
        player = self.get_player(ctx.author.id, ctx.author.name)
        
        embed = discord.Embed(
            title="🎮 Welcome to the RPG World!",
            description=f"**{ctx.author.name}**, your adventure begins now!\n\n"
                       f"Choose your class with `/rpg class <name>`\n"
                       f"Available classes: Warrior, Mage, Archer, Healer",
            color=discord.Color.green()
        )
        
        for class_id, class_info in self.classes.items():
            stats = class_info['stats']
            stats_text = f"❤️ HP: {stats['hp']} | 💎 MP: {stats['mp']}\n"
            stats_text += f"⚔️ ATK: {stats['attack']} | 🛡️ DEF: {stats['defense']} | 🔮 MAG: {stats['magic']}"
            embed.add_field(
                name=f"{class_info['emoji']} {class_info['name']}",
                value=f"{class_info['description']}\n{stats_text}",
                inline=True
            )
        
        await ctx.send(embed=embed)
        self.save_data()
    
    @rpg.command(name='class')
    @app_commands.describe(class_name="The class to choose")
    @app_commands.choices(class_name=[
        app_commands.Choice(name="Warrior", value="warrior"),
        app_commands.Choice(name="Mage", value="mage"),
        app_commands.Choice(name="Archer", value="archer"),
        app_commands.Choice(name="Healer", value="healer")
    ])
    async def select_class(self, ctx, *, class_name: str = None):
        """Choose your character class"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start your adventure first with `/rpg start`!")
        
        if not class_name:
            class_list = ', '.join([f"**{c['name']}**" for c in self.classes.values()])
            return await ctx.send(f"Available classes: {class_list}\nUse: `/rpg class <name>`")
        
        class_name = class_name.lower()
        if class_name not in self.classes:
            return await ctx.send("❌ Invalid class! Available: warrior, mage, archer, healer")
        
        selected_class = self.classes[class_name]
        stats = selected_class['stats']
        
        player.class_type = selected_class['name']
        player.max_hp = stats['hp']
        player.hp = stats['hp']
        player.max_mp = stats['mp']
        player.mp = stats['mp']
        player.attack = stats['attack']
        player.defense = stats['defense']
        player.magic = stats['magic']
        
        embed = discord.Embed(
            title=f"{selected_class['emoji']} Class Selected!",
            description=f"You are now a **{selected_class['name']}**!\n{selected_class['description']}",
            color=discord.Color.green()
        )
        embed.add_field(name="❤️ HP", value=player.max_hp, inline=True)
        embed.add_field(name="💎 MP", value=player.max_mp, inline=True)
        embed.add_field(name="⚔️ Attack", value=player.attack, inline=True)
        embed.add_field(name="🛡️ Defense", value=player.defense, inline=True)
        embed.add_field(name="🔮 Magic", value=player.magic, inline=True)
        
        await ctx.send(embed=embed)
        self.save_data()
    
    @rpg.command(name='profile')
    @app_commands.describe(member="The user to view profile of")
    async def profile(self, ctx, member: discord.Member = None):
        """View RPG profile"""
        if member is None:
            member = ctx.author
        
        player = self.get_player(member.id)
        
        if not player:
            if member == ctx.author:
                return await ctx.send("❌ You haven't started yet! Use `/rpg start`")
            else:
                return await ctx.send("❌ This player hasn't started their adventure!")
        
        xp_needed = player.get_xp_needed()
        xp_progress = int((player.xp / xp_needed) * 20) if not player.is_max_level() else 20
        xp_bar = '█' * xp_progress + '░' * (20 - xp_progress)
        
        embed = discord.Embed(
            title=f"📜 {member.name}'s Profile",
            description=f"**{self.classes[player.class_type.lower()]['emoji']} {player.class_type}**",
            color=discord.Color.blue()
        )
        
        if player.is_max_level():
            embed.add_field(name="⭐ Level", value="**MAX LEVEL (100)** 🔥", inline=False)
        else:
            embed.add_field(
                name="⭐ Level",
                value=f"Level **{player.level}**\n"
                      f"XP: {player.xp}/{xp_needed}\n"
                      f"{xp_bar}",
                inline=False
            )
        
        hp_bar = self.format_hp_bar(player.hp, player.max_hp, 10)
        mp_bar = self.format_hp_bar(player.mp, player.max_mp, 10)
        
        embed.add_field(name="❤️ HP", value=f"{player.hp}/{player.max_hp} {hp_bar}", inline=True)
        embed.add_field(name="💎 MP", value=f"{player.mp}/{player.max_mp} {mp_bar}", inline=True)
        embed.add_field(name="⚔️ ATK", value=player.attack, inline=True)
        embed.add_field(name="🛡️ DEF", value=player.defense, inline=True)
        embed.add_field(name="🔮 MAG", value=player.magic, inline=True)
        
        embed.add_field(name="💰 Gold", value=f"{player.gold:,}", inline=True)
        embed.add_field(name="💎 Gems", value=player.gems, inline=True)
        
        equip_text = ""
        for slot, item in player.equipment.items():
            emoji = {'weapon': '⚔️', 'armor': '🛡️', 'accessory': '💍'}
            item_name = self.shop_items[item]['name'] if item and item in self.shop_items else 'None'
            equip_text += f"{emoji[slot]} {slot.title()}: {item_name}\n"
        embed.add_field(name="🎒 Equipment", value=equip_text, inline=False)
        
        stats_text = f"🐉 Monsters Killed: {player.monsters_killed}\n"
        stats_text += f"💀 Bosses Defeated: {player.bosses_killed}\n"
        stats_text += f"☠️ Deaths: {player.deaths}"
        embed.add_field(name="📊 Stats", value=stats_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @rpg.command(name='hunt')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hunt(self, ctx):
        """Hunt monsters for XP and gold"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start with `/rpg start` first!")
        
        if player.hp <= 0:
            return await ctx.send("💀 You're dead! Use `/rpg heal` to revive.")
        
        available_monsters = {
            name: stats for name, stats in self.monsters.items()
            if stats['level'] <= player.level + 5
        }
        
        if not available_monsters:
            return await ctx.send("❌ No monsters available! You're too strong!")
        
        monster_name = random.choice(list(available_monsters.keys()))
        monster = available_monsters[monster_name]
        
        embed = discord.Embed(
            title=f"⚔️ Encounter: {monster_name}",
            description="A wild monster appears!",
            color=discord.Color.red()
        )
        
        player_damage = self.calculate_damage(player.attack, monster['defense'])
        monster_damage = self.calculate_damage(monster['attack'], player.defense)
        
        special_damage = 0
        if player.class_type == 'Mage' and player.mp >= 10:
            special_damage = player.magic * 2
            player.mp -= 10
            embed.add_field(name="🔮 Magic Attack!", value=f"Bonus {special_damage} damage!", inline=False)
        elif player.class_type == 'Archer' and random.random() < 0.3:
            special_damage = int(player_damage * 0.5)
            embed.add_field(name="🎯 Critical Hit!", value=f"Bonus {special_damage} damage!", inline=False)
        elif player.class_type == 'Healer' and player.hp < player.max_hp * 0.5:
            heal_amount = player.magic * 3
            player.hp = min(player.max_hp, player.hp + heal_amount)
            embed.add_field(name="💚 Self Heal!", value=f"Healed {heal_amount} HP!", inline=False)
        
        total_player_damage = player_damage + special_damage
        
        embed.add_field(
            name="🗡️ Your Attack",
            value=f"Dealt **{total_player_damage}** damage!",
            inline=True
        )
        embed.add_field(
            name="👊 Monster Attack",
            value=f"Received **{monster_damage}** damage!",
            inline=True
        )
        
        if total_player_damage >= monster['hp']:
            gold_earned = monster['gold'] + random.randint(-5, 10)
            xp_earned = monster['xp'] + random.randint(-5, 10)
            
            player.gold += gold_earned
            player.xp += xp_earned
            player.monsters_killed += 1
            
            embed.add_field(
                name="🎉 VICTORY!",
                value=f"Gained **{xp_earned}** XP and **{gold_earned}** gold!",
                inline=False
            )
            embed.color = discord.Color.green()
            
            level_up = await self.check_level_up(ctx, player)
            if level_up:
                embed.add_field(name="⭐ LEVEL UP!", value=level_up, inline=False)
            
            if random.random() < 0.15:
                loot = random.choice(list(self.shop_items.keys()))
                player.inventory.append(loot)
                embed.add_field(name="🎁 Item Drop!", value=f"Found: **{self.shop_items[loot]['name']}**", inline=False)
        else:
            player.hp -= monster_damage
            embed.add_field(name="💔 Battle Continues", value="The monster fights back!", inline=False)
        
        if player.hp <= 0:
            player.hp = 0
            player.deaths += 1
            embed.add_field(name="☠️ DEFEATED!", value="You were knocked out! Heal to continue.", inline=False)
        
        hp_bar = self.format_hp_bar(player.hp, player.max_hp, 10)
        embed.set_footer(text=f"❤️ HP: {player.hp}/{player.max_hp} {hp_bar} | ⭐ Level: {player.level}")
        await ctx.send(embed=embed)
        self.save_data()
    
    @rpg.command(name='boss')
    async def boss_fight(self, ctx):
        """Fight a boss (1 hour cooldown)"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start with `/rpg start` first!")
        
        if player.hp <= 0:
            return await ctx.send("💀 You're dead! Can't fight bosses.")
        
        if player.last_boss:
            last = datetime.fromisoformat(player.last_boss)
            cooldown = timedelta(hours=1)
            if datetime.now() - last < cooldown:
                remaining = cooldown - (datetime.now() - last)
                total_secs = int(remaining.total_seconds())
                hours = total_secs // 3600
                minutes = (total_secs % 3600) // 60
                return await ctx.send(f"⏰ Boss cooldown! Wait **{hours}h {minutes}m**.")
        
        if player.level < 25:
            boss_name = 'Dark Knight'
        elif player.level < 50:
            boss_name = 'Dragon'
        elif player.level < 75:
            boss_name = 'Ancient Lich'
        else:
            boss_name = 'Demon Lord'
        
        boss = self.bosses[boss_name].copy()
        boss_hp = boss['hp']
        
        boss_embed = discord.Embed(
            title=f"💀 BOSS BATTLE: {boss_name}",
            description="⚔️ Prepare for an epic battle!",
            color=discord.Color.dark_red()
        )
        boss_msg = await ctx.send(embed=boss_embed)
        
        await asyncio.sleep(1)
        
        battle_log = []
        player_original_hp = player.hp
        
        for phase in range(3):
            phase_messages = [
                "The ground shakes...",
                f"**{boss_name}** unleashes a powerful attack!",
                "⚡ The battle intensifies!"
            ]
            
            boss_embed.description = phase_messages[phase]
            await boss_msg.edit(embed=boss_embed)
            await asyncio.sleep(1)
            
            player_damage = self.calculate_damage(player.attack, boss['defense'])
            boss_damage = self.calculate_damage(boss['attack'], player.defense)
            
            if player.class_type == 'Warrior':
                player_damage = int(player_damage * 1.3)
            elif player.class_type == 'Mage' and player.mp >= 20:
                player_damage += player.magic * 2
                player.mp -= 20
            
            boss_hp -= player_damage
            player.hp -= boss_damage
            
            battle_log.append(f"Phase {phase+1}: You dealt {player_damage}, took {boss_damage}")
            
            if player.hp <= 0 or boss_hp <= 0:
                break
        
        if player.hp > 0 and boss_hp <= 0:
            gold_reward = boss['gold']
            xp_reward = boss['xp']
            gems_reward = boss['gems']
            
            player.gold += gold_reward
            player.xp += xp_reward
            player.gems += gems_reward
            player.bosses_killed += 1
            player.last_boss = datetime.now().isoformat()
            
            result_embed = discord.Embed(
                title="👑 BOSS DEFEATED!",
                description=f"You have slain the mighty **{boss_name}**!",
                color=discord.Color.gold()
            )
            result_embed.add_field(name="💰 Gold", value=f"+{gold_reward}", inline=True)
            result_embed.add_field(name="⭐ XP", value=f"+{xp_reward}", inline=True)
            result_embed.add_field(name="💎 Gems", value=f"+{gems_reward}", inline=True)
            
            level_up = await self.check_level_up(ctx, player)
            if level_up:
                result_embed.add_field(name="⭐ LEVEL UP!", value=level_up, inline=False)
            
            if random.random() < 0.5:
                rare_items = ['dragon_armor', 'magic_staff', 'elixir']
                rare_item = random.choice(rare_items)
                player.inventory.append(rare_item)
                result_embed.add_field(
                    name="🌟 LEGENDARY DROP!",
                    value=f"You found: **{self.shop_items[rare_item]['name']}**",
                    inline=False
                )
            
            await ctx.send(embed=result_embed)
        else:
            player.hp = max(0, player_original_hp - 50)
            player.deaths += 1
            player.last_boss = datetime.now().isoformat()
            
            defeat_embed = discord.Embed(
                title="💔 BOSS DEFEATED YOU",
                description=f"The **{boss_name}** was too powerful!",
                color=discord.Color.dark_gray()
            )
            defeat_embed.add_field(name="💀 Status", value="You survived but lost 50 HP", inline=False)
            await ctx.send(embed=defeat_embed)
        
        self.save_data()
    
    async def check_level_up(self, ctx, player):
        """Check and process level up"""
        if player.is_max_level():
            return None
        
        xp_needed = player.get_xp_needed()
        if player.xp >= xp_needed:
            player.xp -= xp_needed
            player.level += 1
            
            hp_boost = 15
            mp_boost = 8
            atk_boost = 3
            def_boost = 2
            
            player.max_hp += hp_boost
            player.hp = player.max_hp
            player.max_mp += mp_boost
            player.mp = player.max_mp
            player.attack += atk_boost
            player.defense += def_boost
            
            return f"Now Level {player.level}!\n" \
                   f"❤️ HP +{hp_boost} | 💎 MP +{mp_boost}\n" \
                   f"⚔️ ATK +{atk_boost} | 🛡️ DEF +{def_boost}"
        
        return None
    
    @rpg.command(name='shop')
    async def shop(self, ctx):
        """View the item shop"""
        embed = discord.Embed(
            title="🏪 RPG Item Shop",
            description="Buy items with `/rpg buy <item>`\nSell items with `/rpg sell <item>`",
            color=discord.Color.green()
        )
        
        consumables = []
        weapons = []
        armors = []
        accessories = []
        
        for item_id, item in self.shop_items.items():
            if item['type'] == 'consumable':
                consumables.append((item_id, item))
            elif item['type'] == 'weapon':
                weapons.append((item_id, item))
            elif item['type'] == 'armor':
                armors.append((item_id, item))
            elif item['type'] == 'accessory':
                accessories.append((item_id, item))
        
        if consumables:
            text = ""
            for item_id, item in consumables:
                text += f"{item['name']} - 💰 {item['price']}g (`{item_id}`)\n"
            embed.add_field(name="🧪 Consumables", value=text, inline=False)
        
        if weapons:
            text = ""
            for item_id, item in weapons:
                text += f"{item['name']} - 💰 {item['price']}g (`{item_id}`)\n"
            embed.add_field(name="⚔️ Weapons", value=text, inline=False)
        
        if armors:
            text = ""
            for item_id, item in armors:
                text += f"{item['name']} - 💰 {item['price']}g (`{item_id}`)\n"
            embed.add_field(name="🛡️ Armors", value=text, inline=False)
        
        if accessories:
            text = ""
            for item_id, item in accessories:
                text += f"{item['name']} - 💰 {item['price']}g (`{item_id}`)\n"
            embed.add_field(name="💍 Accessories", value=text, inline=False)
        
        await ctx.send(embed=embed)
    
    @rpg.command(name='buy')
    @app_commands.describe(item_name="The item ID to buy")
    async def buy_item(self, ctx, *, item_name: str):
        """Buy an item from the shop"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start with `/rpg start` first!")
        
        item_name = item_name.lower().replace(' ', '_')
        
        if item_name not in self.shop_items:
            return await ctx.send("❌ Item not found! Check `/rpg shop` for available items.")
        
        item = self.shop_items[item_name]
        
        if player.gold < item['price']:
            return await ctx.send(f"❌ Not enough gold! You need **{item['price']}g**, you have **{player.gold}g**.")
        
        player.gold -= item['price']
        player.inventory.append(item_name)
        
        await ctx.send(f"✅ Purchased **{item['name']}**! Check your `/rpg inventory`.")
        self.save_data()

    @rpg.command(name='sell')
    @app_commands.describe(item_name="The item ID to sell")
    async def sell_item(self, ctx, *, item_name: str):
        """Sell an item from your inventory"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start with `/rpg start` first!")
        
        item_name = item_name.lower().replace(' ', '_')
        
        if item_name not in player.inventory:
            return await ctx.send("❌ You don't have this item!")
        
        if item_name not in self.shop_items:
            return await ctx.send("❌ This item cannot be sold!")
        
        item = self.shop_items[item_name]
        sell_price = item['price'] // 2
        
        player.gold += sell_price
        player.inventory.remove(item_name)
        
        await ctx.send(f"✅ Sold **{item['name']}** for **{sell_price}g**!")
        self.save_data()

    @rpg.command(name='use')
    @app_commands.describe(item_name="The consumable item ID to use")
    async def use_item(self, ctx, *, item_name: str):
        """Use a consumable item"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start with `/rpg start` first!")
        
        item_name = item_name.lower().replace(' ', '_')
        
        if item_name not in player.inventory:
            return await ctx.send("❌ You don't have this item!")
        
        item = self.shop_items.get(item_name)
        if not item or item['type'] != 'consumable':
            return await ctx.send("❌ This item is not a consumable!")
            
        effects = item['effect']
        healed = 0
        mana_restored = 0
        
        if 'heal' in effects:
            healed = min(player.max_hp - player.hp, effects['heal'])
            player.hp += healed
        if 'mana' in effects:
            mana_restored = min(player.max_mp - player.mp, effects['mana'])
            player.mp += mana_restored
            
        player.inventory.remove(item_name)
        await ctx.send(f"✅ Used **{item['name']}**! Restored {healed} HP and {mana_restored} MP.")
        self.save_data()
    
    @rpg.command(name='inventory')
    async def inventory(self, ctx):
        """View your inventory"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start with `/rpg start` first!")
        
        if not player.inventory:
            return await ctx.send("🎒 Your inventory is empty!")
        
        items_count = {}
        for item in player.inventory:
            items_count[item] = items_count.get(item, 0) + 1
        
        embed = discord.Embed(
            title="🎒 Your Inventory",
            color=discord.Color.purple()
        )
        
        for item_id, count in items_count.items():
            item_name = self.shop_items.get(item_id, {}).get('name', item_id)
            item_type = self.shop_items.get(item_id, {}).get('type', 'unknown')
            action = "equip" if item_type != 'consumable' else "use"
            
            embed.add_field(
                name=f"{item_name}",
                value=f"Quantity: **{count}**\nUse `/rpg {action} {item_id}`",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @rpg.command(name='equip')
    @app_commands.describe(item_name="The item ID to equip")
    async def equip_item(self, ctx, *, item_name: str):
        """Equip an item from inventory"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start with `/rpg start` first!")
        
        item_name = item_name.lower().replace(' ', '_')
        
        if item_name not in player.inventory:
            return await ctx.send("❌ You don't have this item!")
        
        if item_name not in self.shop_items:
            return await ctx.send("❌ This item cannot be equipped!")
        
        item = self.shop_items[item_name]
        
        if item['type'] == 'consumable':
            return await ctx.send("❌ Consumables cannot be equipped! Use `/rpg use` instead.")
        
        slot = item['type']
        old_item = player.equipment[slot]
        
        # Remove old item stats (FIXED BUG)
        if old_item and old_item in self.shop_items:
            old_effects = self.shop_items[old_item]['effect']
            if 'attack' in old_effects: player.attack -= old_effects['attack']
            if 'magic' in old_effects: player.magic -= old_effects['magic']
            if 'defense' in old_effects: player.defense -= old_effects['defense']
        
        player.equipment[slot] = item_name
        player.inventory.remove(item_name)
        
        if old_item:
            player.inventory.append(old_item)
        
        effects = item['effect']
        if 'attack' in effects:
            player.attack += effects['attack']
        if 'magic' in effects:
            player.magic += effects['magic']
        if 'defense' in effects:
            player.defense += effects['defense']
        
        await ctx.send(f"✅ Equipped **{item['name']}**!")
        self.save_data()
    
    @rpg.command(name='daily')
    async def daily_reward(self, ctx):
        """Claim daily reward"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start with `/rpg start` first!")
        
        if player.last_daily:
            last = datetime.fromisoformat(player.last_daily)
            cooldown = timedelta(hours=24)
            if datetime.now() - last < cooldown:
                remaining = cooldown - (datetime.now() - last)
                total_secs = int(remaining.total_seconds())
                hours = total_secs // 3600
                minutes = (total_secs % 3600) // 60
                return await ctx.send(f"⏰ Daily reward in **{hours}h {minutes}m**")
        
        gold_reward = 50 + (player.level * 15)
        xp_reward = 25 + (player.level * 10)
        gems_reward = 1 if player.level >= 20 else 0
        
        player.gold += gold_reward
        player.xp += xp_reward
        if gems_reward:
            player.gems += gems_reward
        player.last_daily = datetime.now().isoformat()
        
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Gold", value=f"+{gold_reward}", inline=True)
        embed.add_field(name="⭐ XP", value=f"+{xp_reward}", inline=True)
        if gems_reward:
            embed.add_field(name="💎 Gems", value=f"+{gems_reward}", inline=True)
        
        level_up = await self.check_level_up(ctx, player)
        if level_up:
            embed.add_field(name="⭐ LEVEL UP!", value=level_up, inline=False)
        
        await ctx.send(embed=embed)
        self.save_data()
    
    @rpg.command(name='heal')
    async def heal(self, ctx):
        """Heal your character"""
        player = self.get_player(ctx.author.id)
        
        if not player:
            return await ctx.send("❌ Start with `/rpg start` first!")
        
        if player.hp >= player.max_hp and player.mp >= player.max_mp:
            return await ctx.send("❤️ You're already at full HP and MP!")
        
        cost = 30
        if player.gold < cost:
            return await ctx.send(f"❌ Not enough gold! You need {cost}g.")
        
        player.gold -= cost
        player.hp = player.max_hp
        player.mp = player.max_mp
        
        await ctx.send(f"💖 Fully healed! HP and MP restored. (-{cost}g)")
        self.save_data()
    
    @rpg.command(name='top')
    async def leaderboard(self, ctx):
        """View the RPG leaderboard"""
        if not self.players:
            return await ctx.send("📊 No players yet!")
        
        sorted_players = sorted(
            self.players.values(),
            key=lambda p: (p.level, p.xp, p.gold),
            reverse=True
        )[:10]
        
        embed = discord.Embed(
            title="🏆 RPG Leaderboard",
            description="Top 10 Adventurers",
            color=discord.Color.gold()
        )
        
        medals = ['🥇', '🥈', '🥉'] + ['👑'] * 7
        
        for i, player in enumerate(sorted_players):
            medal = medals[i] if i < len(medals) else '⭐'
            
            try:
                user = await self.bot.fetch_user(player.user_id)
                name = user.name
            except:
                name = player.name
            
            embed.add_field(
                name=f"{medal} #{i+1} - {name}",
                value=f"{player.class_type} | Level {player.level}\n"
                      f"❤️ {player.max_hp} | ⚔️ {player.attack} | 💰 {player.gold:,}g",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @rpg.command(name='duel')
    @app_commands.describe(opponent="The user to duel")
    async def duel(self, ctx, opponent: discord.Member):
        """Challenge another player to a duel"""
        if opponent.bot or opponent == ctx.author:
            return await ctx.send("❌ You can't duel bots or yourself!")
        
        player = self.get_player(ctx.author.id)
        opp_player = self.get_player(opponent.id)
        
        if not player:
            return await ctx.send("❌ Start your adventure first!")
        if not opp_player:
            return await ctx.send("❌ Your opponent hasn't started their adventure!")
        
        if player.hp <= 0:
            return await ctx.send("💀 You can't duel while dead!")
        if opp_player.hp <= 0:
            return await ctx.send("💀 Your opponent is dead!")
        
        duel_msg = await ctx.send(
            f"⚔️ **{opponent.mention}**, {ctx.author.mention} challenges you to a duel!\n"
            f"React with ⚔️ to accept!"
        )
        await duel_msg.add_reaction('⚔️')
        
        def check(reaction, user):
            return user == opponent and str(reaction.emoji) == '⚔️'
        
        try:
            await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("⏰ Duel request timed out!")
        
        battle_log = []
        
        # FIXED BUG: Stop duel if someone dies
        for round_num in range(3):
            if player.hp <= 0 or opp_player.hp <= 0:
                break
                
            p1_dmg = self.calculate_damage(player.attack, opp_player.defense)
            p2_dmg = self.calculate_damage(opp_player.attack, player.defense)
            
            opp_player.hp -= p1_dmg
            player.hp -= p2_dmg
            
            battle_log.append(f"Round {round_num+1}: {ctx.author.name} dealt {p1_dmg}, took {p2_dmg}")
        
        # Determine winner properly
        if player.hp > 0 and opp_player.hp <= 0:
            winner, loser = ctx.author, opponent
        elif opp_player.hp > 0 and player.hp <= 0:
            winner, loser = opponent, ctx.author
        elif player.hp > opp_player.hp:
            winner, loser = ctx.author, opponent
        elif opp_player.hp > player.hp:
            winner, loser = opponent, ctx.author
        else:
            return await ctx.send("⚔️ It's a draw!")
            
        gold_reward = random.randint(20, 50)
        winner_player = self.get_player(winner.id)
        winner_player.gold += gold_reward
        
        embed = discord.Embed(
            title="⚔️ DUEL RESULT",
            description=f"🏆 **{winner.name}** wins the duel!\n"
                       f"💰 Earned {gold_reward} gold!",
            color=discord.Color.gold()
        )
        
        for log in battle_log:
            embed.add_field(name="Battle Log", value=log, inline=False)
        
        await ctx.send(embed=embed)
        self.save_data()

async def setup(bot):
    await bot.add_cog(RPG(bot))
    print('⚔️ RPG cog loaded!')