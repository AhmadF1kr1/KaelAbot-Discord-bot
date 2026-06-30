import discord
from discord.ext import commands
import json
import os
import re
import random
from typing import List, Set


# View for Button-based Role Assignment
class RoleButtonView(discord.ui.View):
    def __init__(self, bot, message_id: int, roles_data: list):
        # timeout=None makes it persistent
        super().__init__(timeout=None)
        self.bot = bot
        self.message_id = message_id
        
        for role_info in roles_data:
            custom_id = f"role_btn:{message_id}:{role_info['role_id']}"
            button = discord.ui.Button(
                label=role_info.get('label', f"Role {role_info['role_id']}"),
                emoji=role_info.get('emoji'),
                style=discord.ButtonStyle.secondary,
                custom_id=custom_id
            )
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        # Extract role_id from custom_id: "role_btn:{message_id}:{role_id}"
        parts = interaction.data['custom_id'].split(':')
        role_id = int(parts[2])
        
        guild = interaction.guild
        role = guild.get_role(role_id)
        
        if not role:
            return await interaction.response.send_message(
                "❌ Role tidak ditemukan atau telah dihapus.", 
                ephemeral=True
            )
            
        member = interaction.user
        
        # Check bot permissions
        if guild.me.top_role <= role:
            return await interaction.response.send_message(
                f"❌ Bot tidak memiliki izin untuk mengelola role **{role.name}** (Posisi role bot harus di atas role tersebut).",
                ephemeral=True
            )

        try:
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message(
                    f"✅ Role **{role.name}** telah dihapus dari profil Anda.",
                    ephemeral=True
                )
            else:
                await member.add_roles(role)
                await interaction.response.send_message(
                    f"✅ Role **{role.name}** telah ditambahkan ke profil Anda.",
                    ephemeral=True
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Gagal memperbarui role Anda. Pastikan bot memiliki izin `Manage Roles`.",
                ephemeral=True
            )


# Dropdown Component
class RoleDropdown(discord.ui.Select):
    def __init__(self, message_id: int, roles_data: list):
        options = []
        self.roles_data = roles_data
        
        for r in roles_data:
            options.append(discord.SelectOption(
                label=r.get('label', f"Role {r['role_id']}"),
                value=str(r['role_id']),
                emoji=r.get('emoji')
            ))
            
        super().__init__(
            placeholder="Pilih role Anda di sini...",
            min_values=0,
            max_values=len(roles_data),
            options=options,
            custom_id=f"role_select:{message_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        
        selected_ids = [int(val) for val in self.values]
        all_menu_ids = [r['role_id'] for r in self.roles_data]
        
        # Roles to add (selected but user doesn't have)
        # Roles to remove (not selected but user has)
        roles_to_add = []
        roles_to_remove = []
        
        for r_id in all_menu_ids:
            role = guild.get_role(r_id)
            if not role:
                continue
                
            if guild.me.top_role <= role:
                # Skip roles bot cannot manage
                continue
                
            if r_id in selected_ids:
                if role not in member.roles:
                    roles_to_add.append(role)
            else:
                if role in member.roles:
                    roles_to_remove.append(role)
                    
        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add)
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
                
            added_names = ", ".join([f"**{r.name}**" for r in roles_to_add])
            removed_names = ", ".join([f"**{r.name}**" for r in roles_to_remove])
            
            msg_parts = []
            if roles_to_add:
                msg_parts.append(f"Ditambahkan: {added_names}")
            if roles_to_remove:
                msg_parts.append(f"Dihapus: {removed_names}")
                
            if not msg_parts:
                await interaction.response.send_message(
                    "Tidak ada perubahan role.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Perubahan role berhasil!\n" + "\n".join(msg_parts),
                    ephemeral=True
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Gagal mengubah role. Pastikan bot memiliki izin `Manage Roles`.",
                ephemeral=True
            )


# View wrapper for Dropdown
class RoleDropdownView(discord.ui.View):
    def __init__(self, bot, message_id: int, roles_data: list):
        super().__init__(timeout=None)
        self.bot = bot
        self.message_id = message_id
        self.add_item(RoleDropdown(message_id, roles_data))


class AutoRoleMainView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Pilih Role",
        style=discord.ButtonStyle.primary,
        custom_id="autorole:main_btn",
        emoji="🎭"
    )
    async def select_roles_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        
        cog = self.bot.get_cog("RoleSelect")
        if not cog:
            return await interaction.response.send_message("❌ Sistem role tidak aktif.", ephemeral=True)
            
        roles = cog._get_available_roles(interaction)
        if not roles:
            return await interaction.response.send_message("❌ Tidak ada role yang tersedia untuk dipilih di server ini.", ephemeral=True)
            
        view = AutoRoleSelectionView(self.bot, member, roles, cog)
        await interaction.response.send_message(
            "Silakan pilih/ubah role Anda melalui menu dropdown di bawah ini:",
            view=view,
            ephemeral=True
        )


class RoleToggleButton(discord.ui.Button):
    def __init__(self, role: discord.Role, is_selected: bool, cog):
        self.role = role
        self.cog = cog
        emoji = cog._auto_emoji(role.name)
        style = discord.ButtonStyle.success if is_selected else discord.ButtonStyle.secondary
        label = role.name[:80]
        super().__init__(
            label=label,
            emoji=emoji,
            style=style
        )

    async def callback(self, interaction: discord.Interaction):
        # Toggle selection
        if self.role.id in self.view.selected_ids:
            self.view.selected_ids.remove(self.role.id)
            self.style = discord.ButtonStyle.secondary
        else:
            self.view.selected_ids.add(self.role.id)
            self.style = discord.ButtonStyle.success
        
        # Update view
        await interaction.response.edit_message(view=self.view)


class AutoRoleSelectionView(discord.ui.View):
    def __init__(self, bot, member: discord.Member, roles: List[discord.Role], cog):
        super().__init__(timeout=180)
        self.bot = bot
        self.member = member
        self.roles = roles
        self.cog = cog
        
        # Load user's current roles as selected
        member_role_ids = {r.id for r in member.roles}
        self.selected_ids = {r.id for r in roles if r.id in member_role_ids}
        
        self.current_page = 0
        self.per_page = 15
        self.load_page()

    def load_page(self):
        self.clear_items()
        
        # Get roles for current page
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_roles = self.roles[start:end]
        
        # Add toggle button for each role
        for idx, role in enumerate(page_roles):
            row = idx // 5
            is_selected = role.id in self.selected_ids
            self.add_item(RoleToggleButton(role, is_selected, self.cog))
            
        # Add navigation buttons if total roles > 15
        total_pages = (len(self.roles) - 1) // self.per_page + 1
        if total_pages > 1:
            prev_btn = discord.ui.Button(
                label=f"◀️ Hal. {self.current_page}",
                style=discord.ButtonStyle.primary,
                disabled=(self.current_page == 0),
                row=3
            )
            async def prev_callback(interaction: discord.Interaction):
                self.current_page -= 1
                self.load_page()
                await interaction.response.edit_message(view=self)
            prev_btn.callback = prev_callback
            self.add_item(prev_btn)
            
            next_btn = discord.ui.Button(
                label=f"Hal. {self.current_page+2} ▶️",
                style=discord.ButtonStyle.primary,
                disabled=(self.current_page >= total_pages - 1),
                row=3
            )
            async def next_callback(interaction: discord.Interaction):
                self.current_page += 1
                self.load_page()
                await interaction.response.edit_message(view=self)
            next_btn.callback = next_callback
            self.add_item(next_btn)
            
        # Add action buttons
        save_btn = discord.ui.Button(
            label="💾 Simpan Perubahan",
            style=discord.ButtonStyle.success,
            row=4
        )
        save_btn.callback = self.save_changes
        self.add_item(save_btn)
        
        cancel_btn = discord.ui.Button(
            label="❌ Batal",
            style=discord.ButtonStyle.danger,
            row=4
        )
        cancel_btn.callback = self.cancel_changes
        self.add_item(cancel_btn)

    async def save_changes(self, interaction: discord.Interaction):
        member = interaction.user
        
        roles_to_add = []
        roles_to_remove = []
        
        for role in self.roles:
            if role.id in self.selected_ids:
                if role not in member.roles:
                    roles_to_add.append(role)
            else:
                if role in member.roles:
                    roles_to_remove.append(role)
                    
        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add)
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
                
            added_names = ", ".join([f"**{r.name}**" for r in roles_to_add])
            removed_names = ", ".join([f"**{r.name}**" for r in roles_to_remove])
            
            msg_parts = []
            if roles_to_add:
                msg_parts.append(f"Ditambahkan: {added_names}")
            if roles_to_remove:
                msg_parts.append(f"Dihapus: {removed_names}")
                
            if not msg_parts:
                await interaction.response.send_message(
                    "Tidak ada perubahan role.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Perubahan role berhasil disimpan!\n" + "\n".join(msg_parts),
                    ephemeral=True
                )
            self.stop()
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Gagal memperbarui role. Pastikan bot memiliki izin `Manage Roles` dan posisinya di atas role yang dipilih.",
                ephemeral=True
            )

    async def cancel_changes(self, interaction: discord.Interaction):
        await interaction.response.send_message("❌ Perubahan dibatalkan.", ephemeral=True)
        self.stop()


class RoleSelect(commands.Cog):
    EMOJI_MAP = {
        'game': '🎮', 'gamer': '🎮', 'gaming': '🎮', 'valorant': '🔫',
        'minecraft': '⛏️', 'genshin': '🌸', 'fps': '🎯', 'rpg': '⚔️',
        'art': '🎨', 'artist': '🎨', 'design': '✏️', 'music': '🎵',
        'python': '🐍', 'javascript': '📘', 'java': '☕', 'rust': '🦀',
        'coding': '💻', 'programmer': '💻', 'dev': '💻',
        'admin': '👑', 'mod': '🛡️', 'vip': '💎', 'premium': '⭐',
        'red': '🔴', 'blue': '🔵', 'green': '🟢', 'purple': '🟣',
        'pink': '💗', 'orange': '🟠', 'yellow': '🟡', 'white': '⚪',
        'laki': '♂️', 'pria': '♂️', 'cowok': '♂️', 'cewek': '♀️',
        'perempuan': '♀️', 'wanita': '♀️', 'announce': '📢',
        'event': '🎉', 'giveaway': '🎁', 'notif': '🔔', 'voice': '🎤'
    }

    def _auto_emoji(self, name: str) -> str:
        """Map role name to emoji"""
        n = name.lower()
        for k, v in self.EMOJI_MAP.items():
            if k in n: return v
        return random.choice(['🔹','🔸','🔷','🔶','💠','🌀'])

    def _get_available_roles(self, ctx) -> List[discord.Role]:
        """Get manageable roles from server"""
        bot_top = ctx.guild.me.top_role
        return [r for r in ctx.guild.roles 
                if r.name != '@everyone' 
                and r != bot_top 
                and r.position < bot_top.position 
                and not r.managed]

    def __init__(self, bot):
        self.bot = bot
        self.config_path = "data/role_select_config.json"
        self.config = {}
        self.load_config()
        
    def load_config(self):
        """Load role configs from file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"❌ Error loading role_select_config: {e}")
                self.config = {}
        else:
            self.config = {}

    def save_config(self):
        """Save configurations to file"""
        # Ensure data folder exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ok=False)
        except Exception as e:
            print(f"❌ Error saving role_select_config: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Register persistent views on bot start"""
        # Register the global auto role view
        self.bot.add_view(AutoRoleMainView(self.bot))
        
        count = 1
        for guild_id_str, messages in self.config.items():
            for msg_id_str, data in messages.items():
                msg_id = int(msg_id_str)
                menu_type = data.get("type", "button")
                roles = data.get("roles", [])
                
                if menu_type == "button":
                    view = RoleButtonView(self.bot, msg_id, roles)
                elif menu_type == "auto":
                    view = AutoRoleMainView(self.bot)
                else:
                    view = RoleDropdownView(self.bot, msg_id, roles)
                    
                self.bot.add_view(view)
                count += 1
        print(f"✅ Registered {count} persistent role select views.")

    @commands.hybrid_group(name="rolemenu", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def rolemenu_group(self, ctx):
        """Role menu configuration commands"""
        embed = discord.Embed(
            title="⚙️ Konfigurasi Role Menu",
            description="Buat tombol atau dropdown pilihan role untuk server Anda!",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="Format Perintah",
            value="`!rolemenu create <button|dropdown> <judul_embed> | <emoji1> <Role1> | <emoji2> <Role2> ...`\n\n"
                  "**Contoh Button:**\n"
                  "`!rolemenu create button Pilihan Role Hobi | 🎮 @Gamer | 🎨 @Artist`\n\n"
                  "**Contoh Dropdown:**\n"
                  "`!rolemenu create dropdown Pilih Gender Anda | ♂️ @Laki-laki | ♀️ @Perempuan`\n\n"
                  "**Contoh Otomatis (Semua Role):**\n"
                  "`!rolemenu auto [Judul] [Deskripsi]`",
            inline=False
        )
        embed.set_footer(text="Catatan: Pastikan role bot berada di atas role yang ingin dibagikan.")
        await ctx.send(embed=embed)

    @rolemenu_group.command(name="create")
    @commands.has_permissions(administrator=True)
    async def create_menu(self, ctx, menu_type: str, *, args: str):
        """Create a new role selection menu"""
        if menu_type.lower() not in ["button", "dropdown"]:
            return await ctx.send("❌ Tipe menu harus berupa `button` atau `dropdown`!")

        # Parse arguments: title | emoji1 @Role1 | emoji2 @Role2
        parts = args.split("|")
        title = parts[0].strip()
        
        if len(parts) < 2:
            return await ctx.send("❌ Anda harus memasukkan minimal satu role!\nFormat: `<judul> | <emoji> @Role`")

        roles_data = []
        for part in parts[1:]:
            part = part.strip()
            if not part:
                continue
                
            # Regex to find emoji and role mention or ID
            # Matches custom emoji (<a:name:id> or <:name:id>) or unicode emojis
            # Followed by a role mention (<@&id>) or role ID
            match = re.match(r"(<a?:\w+:\d+>|[\u2600-\u27BF]|[\U00010000-\U0010ffff]|\w+)\s+(<@&\d+>|\d+)", part)
            if not match:
                # Try fallback matching without emoji
                role_match = re.search(r"(<@&\d+>|\d+)", part)
                if role_match:
                    role_ref = role_match.group(1)
                    emoji = None
                else:
                    continue
            else:
                emoji = match.group(1)
                role_ref = match.group(2)

            # Resolve role ID
            role_id_str = re.sub(r"[<@&>]", "", role_ref)
            try:
                role_id = int(role_id_str)
            except ValueError:
                continue

            role = ctx.guild.get_role(role_id)
            if not role:
                continue

            roles_data.append({
                "role_id": role.id,
                "label": role.name,
                "emoji": emoji
            })

        if not roles_data:
            return await ctx.send("❌ Tidak ada role valid yang ditemukan untuk dimasukkan ke menu.")

        # Create temporary response to get message object
        embed = discord.Embed(
            title=title,
            description="Silakan berinteraksi dengan menu di bawah ini untuk mengambil atau menghapus role:",
            color=discord.Color.green()
        )

        # We need a placeholder message to get message_id
        msg = await ctx.send(embed=embed)
        
        # Now create the actual view with the correct message_id
        if menu_type.lower() == "button":
            view = RoleButtonView(self.bot, msg.id, roles_data)
        else:
            view = RoleDropdownView(self.bot, msg.id, roles_data)

        # Edit message to add the view
        await msg.edit(view=view)

        # Save to config
        guild_id_str = str(ctx.guild.id)
        msg_id_str = str(msg.id)
        
        if guild_id_str not in self.config:
            self.config[guild_id_str] = {}
            
        self.config[guild_id_str][msg_id_str] = {
            "type": menu_type.lower(),
            "roles": roles_data
        }
        self.save_config()

        # Register view dynamically so it stays active without restarting the bot
        self.bot.add_view(view)

        # Send confirmation
        if ctx.message:
            try:
                await ctx.message.delete(delay=2)
            except (discord.HTTPException, AttributeError):
                pass

    async def _create_menu_message(self, ctx, menu_type: str, title: str, roles_data: list):
        """Reusable menu creation logic"""
        embed = discord.Embed(title=title, 
                             description=f"**{len(roles_data)} roles** available\nSelect below:", 
                             color=0x2ecc71)
        
        if isinstance(ctx, discord.Interaction):
            msg = await ctx.channel.send(embed=embed)
        else:
            msg = await ctx.send(embed=embed)

        view = RoleButtonView(self.bot, msg.id, roles_data) if menu_type == "button" \
               else RoleDropdownView(self.bot, msg.id, roles_data)
        await msg.edit(view=view)
        
        # Save config
        gid = str(ctx.guild.id)
        self.config.setdefault(gid, {})[str(msg.id)] = {"type": menu_type, "roles": roles_data}
        self.save_config()
        self.bot.add_view(view)
        
        if not isinstance(ctx, discord.Interaction) and hasattr(ctx, 'message') and ctx.message:
            try:
                await ctx.message.delete(delay=3)
            except (discord.HTTPException, AttributeError):
                pass
        return msg

    # ========== COMMAND 1: LIST AVAILABLE ROLES ==========
    @rolemenu_group.command(name="listroles")
    @commands.has_permissions(administrator=True)
    async def list_roles(self, ctx):
        """Display all server roles available for menu"""
        roles = self._get_available_roles(ctx)
        if not roles: return await ctx.send("❌ No roles available!")
        
        embed = discord.Embed(title="📋 Available Server Roles", 
                             description=f"Found **{len(roles)}** roles\nUse `/rolemenu quickcreate` or `/rolemenu selectroles`",
                             color=0x3498db)
        
        chunks = [roles[i:i+25] for i in range(0, len(roles), 25)]
        for i, chunk in enumerate(chunks[:3]):  # Max 3 fields
            text = "\n".join([f"{self._auto_emoji(r.name)} **{r.name}** `ID:{r.id}`" for r in chunk])
            embed.add_field(name=f"Page {i+1} ({len(chunk)} roles)", value=text[:1024], inline=False)
        
        await ctx.send(embed=embed)

    # ========== COMMAND 2: QUICK AUTO-CREATE ==========
    @rolemenu_group.command(name="quickcreate")
    @commands.has_permissions(administrator=True)
    async def quick_create(self, ctx, menu_type: str, *, args: str):
        """Auto-create menu: /rolemenu quickcreate button Title | all|filter keyword
        
        Examples:
        /rolemenu quickcreate dropdown Game Roles | all
        /rolemenu quickcreate button Colors | filter red
        /rolemenu quickcreate dropdown Notifications | all
        """
        if menu_type not in ("button", "dropdown"): 
            return await ctx.send("❌ Type: `button` or `dropdown`")
        
        parts = args.split("|")
        if len(parts) < 2: 
            return await ctx.send("❌ Format: `Title | all` or `Title | filter keyword`")
        
        title = parts[0].strip()
        filter_cmd = parts[1].strip().lower()
        keyword = parts[2].strip().lower() if len(parts) > 2 else None
        
        roles = self._get_available_roles(ctx)
        
        # Apply filter
        if filter_cmd == 'all':
            selected = roles
        elif filter_cmd == 'filter' and keyword:
            selected = [r for r in roles if keyword in r.name.lower()]
        else:
            return await ctx.send("❌ Use: `all` or `filter <keyword>`")
        
        if not selected: return await ctx.send("❌ No matching roles!")
        if len(selected) > 25: 
            return await ctx.send(f"❌ Too many ({len(selected)}). Max 25. Use filter or `/rolemenu selectroles`")
        
        # Build roles_data
        roles_data = [{"role_id": r.id, "label": r.name, "emoji": self._auto_emoji(r.name)} for r in selected]
        
        # Create menu
        return await self._create_menu_message(ctx, menu_type, title, roles_data)

    # ========== COMMAND 3: INTERACTIVE SELECTION ==========
    @rolemenu_group.command(name="selectroles")
    @commands.has_permissions(administrator=True)
    async def select_roles(self, ctx, menu_type: str, *, title: str):
        """Interactive role picker: /rolemenu selectroles dropdown Title"""
        if menu_type not in ("button", "dropdown"): 
            return await ctx.send("❌ Type: `button` or `dropdown`")
        
        roles = self._get_available_roles(ctx)
        if not roles: return await ctx.send("❌ No roles available!")
        
        view = InteractiveRolePicker(self, ctx.author.id, roles, menu_type, title)
        await ctx.send(f"🎨 Select roles for **{title}**\n✅ Confirm when done", view=view)

    # ========== COMMAND 4: AUTO ROLE MENU ==========
    @rolemenu_group.command(name="auto")
    @commands.has_permissions(administrator=True)
    async def auto_menu(self, ctx, title: str = "Pilih Role Anda", *, description: str = "Klik tombol di bawah ini untuk menampilkan menu pilihan role."):
        """Create an automatic role menu using a single button"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple()
        )
        
        view = AutoRoleMainView(self.bot)
        msg = await ctx.send(embed=embed, view=view)
        
        # Save to config
        guild_id_str = str(ctx.guild.id)
        msg_id_str = str(msg.id)
        
        if guild_id_str not in self.config:
            self.config[guild_id_str] = {}
            
        self.config[guild_id_str][msg_id_str] = {
            "type": "auto",
            "roles": []
        }
        self.save_config()
        
        if ctx.message:
            try:
                await ctx.message.delete(delay=2)
            except (discord.HTTPException, AttributeError):
                pass


# ========== INTERACTIVE PICKER VIEW ==========
class InteractiveRolePicker(discord.ui.View):
    def __init__(self, cog, author_id: int, roles: List[discord.Role], menu_type: str, title: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.author_id = author_id
        self.roles = roles
        self.menu_type = menu_type
        self.title = title
        self.selected: Set[int] = set()
        
        # Add role select dropdown (max 25 per dropdown)
        for i in range(0, len(roles), 25):
            self.add_item(RolePickerDropdown(roles[i:i+25], self.selected))
    
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success, row=1)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id: 
            return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
        if not self.selected: 
            return await interaction.response.send_message("❌ Select at least 1 role!", ephemeral=True)
        
        selected_roles = [r for r in self.roles if r.id in self.selected]
        roles_data = [{"role_id": r.id, "label": r.name, "emoji": self.cog._auto_emoji(r.name)} 
                     for r in selected_roles]
        
        await self.cog._create_menu_message(interaction, self.menu_type, self.title, roles_data)
        await interaction.response.send_message(f"✅ Created with {len(roles_data)} roles!", ephemeral=True)
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.author_id:
            await interaction.response.send_message("❌ Cancelled", ephemeral=True)
            self.stop()


class RolePickerDropdown(discord.ui.Select):
    def __init__(self, roles: List[discord.Role], selected_set: Set[int]):
        self.roles = roles
        self.selected_set = selected_set
        options = [discord.SelectOption(label=r.name[:100], value=str(r.id), 
                   emoji='✅' if r.id in selected_set else '⬜') for r in roles]
        super().__init__(placeholder=f"Select roles... ({len(selected_set)} chosen)", 
                        min_values=0, max_values=len(options), options=options)
    
    async def callback(self, interaction: discord.Interaction):
        picked = {int(v) for v in self.values}
        for r in self.roles:
            (self.selected_set.add, self.selected_set.discard)[r.id not in picked](r.id)
        
        # Update options display
        self.placeholder = f"Selected: {len(self.selected_set)} roles"
        for opt in self.options:
            opt.emoji = '✅' if int(opt.value) in self.selected_set else '⬜'
        
        await interaction.response.edit_message(view=self.view)


async def setup(bot):
    await bot.add_cog(RoleSelect(bot))
    print("🎭 RoleSelect cog loaded!")

