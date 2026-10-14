import os
import threading
import sqlite3
import random
import datetime
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select
from flask import Flask
import yt_dlp

# --- 1. WEB SERVER FLASK TỐI ƯU ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Discord V5 Ultimate đang càn quét 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- 2. DATABASE SQLITE GỌN GÀNG ---
fn_db = "bot_database.db"

def init_db():
    conn = sqlite3.connect(fn_db)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS config (
                        guild_id INTEGER PRIMARY KEY,
                        welcome_channel INTEGER,
                        goodbye_channel INTEGER,
                        auto_role INTEGER,
                        badwords TEXT,
                        antilink INTEGER DEFAULT 1
                      )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        xu INTEGER DEFAULT 1000,
                        warns INTEGER DEFAULT 0,
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        title TEXT DEFAULT 'Dân Thường'
                      )''')
    conn.commit()
    conn.close()

init_db()

def get_server_config(guild_id):
    conn = sqlite3.connect(fn_db)
    cursor = conn.cursor()
    cursor.execute("SELECT welcome_channel, goodbye_channel, auto_role, badwords, antilink FROM config WHERE guild_id = ?", (guild_id,))
    row = cursor.fetchone()
    if not row:
        default_badwords = "dm,vl,vcl,cc,ngu,loz,cac"
        cursor.execute("INSERT INTO config (guild_id, badwords, antilink) VALUES (?, ?, 1)", (guild_id, default_badwords))
        conn.commit()
        row = (None, None, None, default_badwords, 1)
    conn.close()
    return {"welcome_channel": row[0], "goodbye_channel": row[1], "auto_role": row[2], "badwords": row[3].split(","), "antilink": row[4]}

def update_config(guild_id, key, value):
    conn = sqlite3.connect(fn_db)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE config SET {key} = ? WHERE guild_id = ?", (value, guild_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(fn_db)
    cursor = conn.cursor()
    cursor.execute("SELECT xu, warns, xp, level, title FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, xu, warns, xp, level, title) VALUES (?, 1000, 0, 0, 1, 'Dân Thường')", (user_id,))
        conn.commit()
        row = (1000, 0, 0, 1, 'Dân Thường')
    conn.close()
    return {"xu": row[0], "warns": row[1], "xp": row[2], "level": row[3], "title": row[4]}

def update_user(user_id, xu, warns, xp, level, title):
    conn = sqlite3.connect(fn_db)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET xu = ?, warns = ?, xp = ?, level = ?, title = ? WHERE user_id = ?", (xu, warns, xp, level, title, user_id))
    conn.commit()
    conn.close()

# --- 3. CORE BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

class UltimateBotV5(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🔥 Đã đồng bộ Slash Commands phiên bản V5!")

bot = UltimateBotV5()

@bot.event
async def on_ready():
    print(f"🚀 Bot V5 {bot.user} đã sẵn sàng càn quét server!")
    await bot.change_presence(activity=discord.Game(name="/panel | Giao Diện Nút Bấm VIP"))

# --- 4. GIAO DIỆN PHÍM BẤM NHANH (UI BUTTONS) ---
class QuickPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎁 Điểm Danh (+2k Xu)", style=discord.ButtonStyle.green, custom_id="v5_daily")
    async def daily_btn(self, interaction: discord.Interaction, button: Button):
        u = get_user(interaction.user.id)
        u["xu"] += 2000
        update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
        await interaction.response.send_message(f"🎉 Bút thành công **2,000 Xu**! (Tổng: {u['xu']:,} Xu)", ephemeral=True)

    @discord.ui.button(label="📊 Xem Hồ Sơ", style=discord.ButtonStyle.blurple, custom_id="v5_rank")
    async def rank_btn(self, interaction: discord.Interaction, button: Button):
        u = get_user(interaction.user.id)
        embed = discord.Embed(title=f"📊 HỒ SƠ: {interaction.user.name}", color=discord.Color.dark_blue())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="🎖️ Danh hiệu", value=u["title"], inline=False)
        embed.add_field(name="⭐ Level", value=str(u["level"]), inline=True)
        embed.add_field(name="💰 Tài sản", value=f"{u['xu']:,} Xu", inline=True)
        embed.add_field(name="⚠️ Vi phạm", value=f"{u['warns']} lần", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🏦 Vay Nóng", style=discord.ButtonStyle.red, custom_id="v5_loan")
    async def loan_btn(self, interaction: discord.Interaction, button: Button):
        u = get_user(interaction.user.id)
        if u["xu"] >= 200:
            await interaction.response.send_message("❌ Mày vẫn còn tiền, cút đi không cho vay!", ephemeral=True)
            return
        u["xu"] += 500
        update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
        await interaction.response.send_message("🏦 Đã bơm nóng **500 Xu** cứu đói vào ví!", ephemeral=True)

# --- 5. BỘ LỌC TỰ ĐỘNG & XP ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    config = get_server_config(message.guild.id)
    content = message.content.lower()

    if config["antilink"] == 1 and ("http://" in content or "https://" in content or "discord.gg/" in content):
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            await message.timeout(datetime.timedelta(minutes=10), reason="Spam link")
            await message.channel.send(f"🚨 {message.author.mention} quăng link bậy nên đã bị khóa mõm 10 phút!", delete_after=5)
            return

    for word in config["badwords"]:
        if word and word in content:
            await message.delete()
            u = get_user(message.author.id)
            u["warns"] += 1
            update_user(message.author.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
            await message.channel.send(f"⚠️ {message.author.mention}, mồm mép láo toét! Phạt 1 thẻ vàng ({u['warns']}/3)", delete_after=5)
            if u["warns"] >= 3:
                try:
                    await message.author.kick(reason="Chửi tục quá 3 lần")
                except:
                    pass
            return

    # Tăng XP cày level tự động
    u = get_user(message.author.id)
    xp = u["xp"] + random.randint(15, 30)
    level = u["level"]
    if xp >= level * 100:
        level += 1
        xp = 0
        await message.channel.send(f"⚡ Ghê đấy {message.author.mention}, vừa cày lên **Level {level}**!")

    update_user(message.author.id, u["xu"], u["warns"], xp, level, u["title"])
    await bot.process_commands(message)

# --- 6. HỆ THỐNG NHẠC VOICE (YT-DLP & FFMPEG) ---
ytdl_format_options = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
ffmpeg_options = {'options': '-vn'}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.title = data.get('title')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.tree.command(name="play", description="Phát nhạc từ YouTube vào Voice Channel")
async def play(interaction: discord.Interaction, tu_khoa: str):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Mày phải chui vào Voice Channel trước!", ephemeral=True)
        return
    channel = interaction.user.voice.channel
    if interaction.guild.voice_client is None:
        await channel.connect()
    
    await interaction.response.defer()
    try:
        player = await YTDLSource.from_url(tu_khoa, loop=bot.loop)
        interaction.guild.voice_client.play(player)
        await interaction.followup.send(f"🎶 Đang quẩy bài: **{player.title}**")
    except Exception as e:
        await interaction.followup.send(f"❌ Lỗi phát nhạc: {e}")

@bot.tree.command(name="stop", description="Dừng nhạc và đuổi bot ra khỏi phòng")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ Đã dừng nhạc và cút khỏi phòng!")
    else:
        await interaction.response.send_message("❌ Bot có ở trong phòng đâu?", ephemeral=True)

# --- 7. SÒNG BÀI & CÁC LỆNH CƠ BẢN ---
@bot.tree.command(name="panel", description="Mở bảng điều khiển nút bấm nhanh")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(title="🎮 BẢNG ĐIỀU KHIỂN NHANH V5", description="Bấm nút bên dưới để thao tác ngay lập tức!", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, view=QuickPanelView())

@bot.tree.command(name="taixiu", description="Chơi tài xỉu kiếm xu")
async def taixiu(interaction: discord.Interaction, cuoc: int, luachon: str):
    u = get_user(interaction.user.id)
    if cuoc <= 0 or cuoc > u["xu"]:
        await interaction.response.send_message("❌ Không đủ xu hoặc cược láo!", ephemeral=True)
        return
    luachon = luachon.lower()
    if luachon not in ["tai", "xiu"]:
        await interaction.response.send_message("❌ Chỉ chọn `tai` hoặc `xiu`!", ephemeral=True)
        return
    xuc_xac = [random.randint(1, 6) for _ in range(3)]
    tong = sum(xuc_xac)
    kq = "tai" if tong >= 11 else "xiu"
    if luachon == kq:
        u["xu"] += cuoc
        msg = f"🎲 Xúc xắc: {xuc_xac} (Tổng: {tong} - **{kq.upper()}**)\n🎉 Thắng lớn! Cộng **+{cuoc} Xu**."
    else:
        u["xu"] -= cuoc
        msg = f"🎲 Xúc xắc: {xuc_xac} (Tổng: {tong} - **{kq.upper()}**)\n😭 Thua sạch! Trừ **-{cuoc} Xu**."
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message(msg)

@bot.tree.command(name="toprich", description="Bảng xếp hạng đại gia xu")
async def toprich(interaction: discord.Interaction):
    conn = sqlite3.connect(fn_db)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, xu, title FROM users ORDER BY xu DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    embed = discord.Embed(title="🏆 TOP 5 ĐẠI GIA LẮM XU", color=discord.Color.gold())
    for idx, (uid, xu, title) in enumerate(rows, 1):
        user = interaction.guild.get_member(uid)
        name = user.name if user else f"User ID: {uid}"
        embed.add_field(name=f"Top {idx}: {name} [{title}]", value=f"💰 {xu:,} Xu", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clean", description="Xóa nhanh tin nhắn rác")
@app_commands.checks.has_permissions(manage_messages=True)
async def clean(interaction: discord.Interaction, so_luong: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=so_luong)
    await interaction.followup.send(f"🧹 Đã xóa sạch {len(deleted)} tin nhắn rác!", ephemeral=True)

# --- KHỞI CHẠY ---
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Lỗi: Thiếu DISCORD_TOKEN!")
 
