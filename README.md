# 🤖 KaelAbot - Discord Bot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0+-green.svg)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

KaelAbot adalah bot Discord serbaguna (*multipurpose*) yang dirancang menggunakan pustaka **discord.py** (v2.0+). Bot ini dilengkapi dengan berbagai fitur menarik seperti sistem musik interaktif, sistem penyambutan (*welcome & goodbye*) dengan kartu gambar dinamis, game RPG berbasis teks yang mendalam, dan menu pemilihan peran (*role menu*) interaktif menggunakan tombol (*button*) atau dropdown.

Semua perintah bot dapat dipanggil menggunakan awalan prefix klasik (default: `!`) maupun fitur **Slash Commands** (`/`) modern Discord secara penuh.

---

## ✨ Fitur Utama

### 🎵 1. Music System
Sistem pemutar musik tangguh yang terintegrasi dengan YouTube menggunakan `yt-dlp` dan `discord.py` voice.
- **Pencarian Pintar:** Cari lagu langsung dari judul atau tautan URL YouTube.
- **Manajemen Antrean:** Dilengkapi fitur *shuffle*, *loop* (tunggal/antrean), hapus lagu, dan bersihkan antrean.
- **Kontrol Volume:** Atur kekerasan suara dari 0% hingga 200%.
- **Auto Leave:** Bot otomatis keluar dari voice channel jika tidak ada pengguna lain di dalamnya untuk menghemat bandwidth.

### 👋 2. Welcome & Goodbye System
Sambut anggota baru dan berikan salam perpisahan yang berkesan secara otomatis.
- **Kartu Selamat Datang (Welcome Card):** Membuat gambar selamat datang secara dinamis menggunakan modul `Pillow` yang menampilkan avatar dan nama pengguna baru.
- **Pesan Kustom:** Pesan selamat datang dan perpisahan dapat dikonfigurasi secara fleksibel per server.
- **Variabel Dinamis:** Gunakan `{member}`, `{member_name}`, `{server}`, dan `{member_count}` dalam pesan Anda.

### 🎭 3. Role Select Menu (Self-Assignable Roles)
Memudahkan admin untuk membuat menu pemilihan role agar anggota dapat mengambil peran mereka sendiri tanpa perlu bantuan staff.
- **Tipe Menu Fleksibel:** Buat menu pilihan role dalam bentuk tombol (*Buttons*) atau menu tarik-turun (*Dropdown*).
- **Interactive Picker:** Gunakan pembuat interaktif berbasis menu Discord untuk menyusun pilihan role Anda dengan mudah.
- **Otomatisasi:** Mendukung pembuatan menu otomatis (*pagination*) untuk seluruh role yang dapat dikelola di server.

### ⚔️ 4. Text-Based RPG Game
Mulai petualangan RPG berbasis teks langsung di server Discord Anda!
- **Pilihan Class:** Pilih salah satu dari 4 class unik: `Warrior`, `Mage`, `Archer`, atau `Healer`.
- **Hunting & Leveling:** Berburu monster dengan tingkat kesulitan yang menyesuaikan dengan level Anda untuk mendapatkan Gold dan EXP.
- **Boss Raid:** Hadapi boss epik setiap 1 jam sekali untuk tantangan dan hadiah yang lebih besar.
- **Ekonomi & Inventaris:** Kumpulkan Gold untuk membeli perlengkapan (*equipment*) seperti senjata dan armor di toko, atau jual kembali item Anda.
- **Sistem PVP:** Tantang pemain lain dalam duel PvP interaktif.
- **Leaderboard:** Bersaing untuk menjadi pemain terkuat di server melalui papan peringkat (*leaderboard*).

---

## 🛠️ Persyaratan Sistem (Prerequisites)

Sebelum menjalankan bot, pastikan server atau komputer Anda telah memiliki:
1. **Python 3.8 atau versi lebih tinggi**
2. **FFmpeg** (Wajib diinstal dan masuk ke dalam PATH sistem agar fitur musik dapat berfungsi)
3. **Discord Bot Token** dengan izin **Privileged Gateway Intents** diaktifkan pada Discord Developer Portal:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent

---

## 🚀 Panduan Instalasi & Menjalankan Bot

### 1. Clone Repository & Masuk ke Direktori
```bash
git clone https://github.com/AhmadF1kr1/KaelAbot-Discord-bot.git
cd KaelAbot-Discord-Bot
```

### 2. Buat Virtual Environment (Sangat Direkomendasikan)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instal Dependensi
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment (`.env`)
Buat file bernama `.env` pada direktori utama proyek dan lengkapi konfigurasi berikut:
```env
DISCORD_TOKEN=TOKEN_BOT_DISCORD_ANDA
PREFIX=!
```

### 5. Jalankan Bot
```bash
python main.py
```

---

## 📋 Daftar Perintah (Commands)

### Perintah Umum & Dasar
| Prefix Command | Slash Command | Deskripsi | Izin Diperlukan |
| :--- | :--- | :--- | :--- |
| `!help [kategori]` | `/help [kategori]` | Menampilkan menu bantuan perintah | Semua |
| `!ping` | `/ping` | Memeriksa latensi respon bot ke server Discord | Semua |
| `!info` | `/info` | Menampilkan informasi teknis tentang bot | Semua |

### 🎵 Fitur Musik
| Prefix Command | Slash Command | Deskripsi | Aliases |
| :--- | :--- | :--- | :--- |
| `!play <judul/URL>` | `/play <judul/URL>` | Memutar lagu dari YouTube ke Voice Channel | `!p` |
| `!pause` | `/pause` | Menjeda musik yang sedang diputar | - |
| `!resume` | `/resume` | Melanjutkan musik yang dijeda | - |
| `!skip` | `/skip` | Melewati lagu saat ini ke lagu berikutnya | `!s` |
| `!stop` | `/stop` | Menghentikan pemutaran musik dan keluar dari Voice Channel | - |
| `!volume <0-200>` | `/volume <volume>` | Mengatur volume suara pemutaran musik | `!vol` |
| `!queue` | `/queue` | Menampilkan daftar antrean lagu saat ini | `!q` |
| `!nowplaying` | `/nowplaying` | Menampilkan informasi lagu yang sedang diputar | `!np` |
| `!shuffle` | `/shuffle` | Mengacak urutan antrean lagu | - |
| `!loop <off/song/queue>`| `/loop <mode>` | Mengatur mode pengulangan lagu | `!repeat` |
| `!remove <index>` | `/remove <index>` | Menghapus lagu dari antrean berdasarkan nomor indeks | - |
| `!clearqueue` | `/clearqueue` | Mengosongkan seluruh antrean lagu | `!cq` |

### 👋 Sistem Welcome & Goodbye
*Catatan: Semua perintah di bawah ini membutuhkan izin **Administrator**.*

| Prefix Command | Slash Command | Deskripsi |
| :--- | :--- | :--- |
| `!welcome` | `/welcome` | Menampilkan menu bantuan konfigurasi Welcome |
| `!welcome set <#channel> [pesan]` | `/welcome set <channel> [message]` | Mengatur channel dan pesan kustom untuk menyambut anggota baru |
| `!welcome test` | `/welcome test` | Mengirimkan simulasi kartu & pesan welcome untuk diuji coba |
| `!welcome settings` | `/welcome settings` | Menampilkan konfigurasi welcome & goodbye saat ini di server |
| `!welcome disable` | `/welcome disable` | Menonaktifkan fitur selamat datang otomatis |
| `!goodbye` | `/goodbye` | Menampilkan menu bantuan konfigurasi Goodbye |
| `!goodbye set <#channel> [pesan]` | `/goodbye set <channel> [message]` | Mengatur channel dan pesan kustom ketika anggota keluar |
| `!goodbye test` | `/goodbye test` | Menampilkan preview pesan perpisahan (goodbye) |
| `!goodbye disable` | `/goodbye disable` | Menonaktifkan fitur salam perpisahan otomatis |

### 🎭 Pilihan Role (Role Menu)
*Catatan: Semua perintah di bawah ini membutuhkan izin **Administrator**.*

| Prefix Command | Slash Command | Deskripsi |
| :--- | :--- | :--- |
| `!rolemenu` | `/rolemenu` | Menampilkan menu panduan format pembuatan role menu |
| `!rolemenu create <type> <args>` | `/rolemenu create <menu_type> <args>` | Membuat menu peran kustom. Tipe: `button` atau `dropdown`. Format argumen: `Judul \| 🎮 @Role1 \| 🎨 @Role2` |
| `!rolemenu listroles` | `/rolemenu listroles` | Menampilkan daftar role server yang dapat dikelola oleh bot |
| `!rolemenu quickcreate <type> <args>`| `/rolemenu quickcreate <menu_type> <args>`| Membuat menu cepat. Format argumen: `Judul \| all` atau `Judul \| filter <keyword>` |
| `!rolemenu selectroles <type> <judul>`| `/rolemenu selectroles <menu_type> <title>`| Membuat menu peran menggunakan picker interaktif untuk memilih role |
| `!rolemenu auto [judul] [deskripsi]`| `/rolemenu auto [title] [description]` | Membuat tombol menu peran otomatis (dengan pagination) untuk semua role |

### ⚔️ Game RPG Teks
| Prefix Command | Slash Command | Deskripsi |
| :--- | :--- | :--- |
| `!rpg start` | `/rpg start` | Memulai perjalanan karakter RPG baru Anda |
| `!rpg class <nama_class>`| `/rpg class <class_name>` | Memilih kelas karakter (`warrior`, `mage`, `archer`, `healer`) |
| `!rpg profile [@user]` | `/rpg profile [member]` | Menampilkan profil, status, dan perlengkapan karakter Anda/orang lain |
| `!rpg hunt` | `/rpg hunt` | Berburu monster untuk memperoleh Gold dan EXP |
| `!rpg boss` | `/rpg boss` | Melawan Boss Raid (Cooldown: 1 jam) |
| `!rpg inventory` | `/rpg inventory` | Memeriksa isi kantong penyimpanan barang Anda |
| `!rpg shop` | `/rpg shop` | Membuka toko barang dan perlengkapan |
| `!rpg buy <item>` | `/rpg buy <item_name>` | Membeli barang atau perlengkapan dari toko |
| `!rpg sell <item>` | `/rpg sell <item_name>` | Menjual barang atau perlengkapan ke toko |
| `!rpg equip <item>` | `/rpg equip <item_name>` | Menggunakan senjata atau pelindung tubuh ke tubuh karakter |
| `!rpg use <item>` | `/rpg use <item_name>` | Mengonsumsi item pemulihan (misal: Potion) |
| `!rpg heal` | `/rpg heal` | Memulihkan HP karakter Anda secara instan seharga 30 Gold |
| `!rpg daily` | `/rpg daily` | Mengklaim hadiah harian berupa Gold koin |
| `!rpg top` | `/rpg top` | Menampilkan leaderboard tingkat level tertinggi pemain di server |
| `!rpg duel <@user>` | `/rpg duel <opponent>` | Menantang pemain lain untuk bertarung satu lawan satu (PVP) |

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah **MIT License**. Silakan gunakan, modifikasi, dan distribusikan proyek ini secara bebas.