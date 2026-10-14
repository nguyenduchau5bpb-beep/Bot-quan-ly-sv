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

# --- 1. WEB SERVER FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Discord V6 Full Option đang hoạt động 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- 2. DATABASE SQLITE ---
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

class UltimateBotV6(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🔥 Đã đồng bộ toàn bộ Slash Commands V6 Full Option!")

bot = UltimateBotV6()

@bot.event
async def on_ready():
    print(f"🚀 Bot V6 {bot.user} đã sẵn sàng càn quét mọi mặt trận!")
    await bot.change_presence(activity=discord.Game(name="/menu | Kho Lệnh Đầy Đủ"))

# --- 4. GIAO DIỆN PHÍM BẤM NHANH (UI BUTTONS) ---
class QuickPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎁 Điểm Danh (+2k Xu)", style=discord.ButtonStyle.green, custom_id="v6_daily")
    async def daily_btn(self, interaction: discord.Interaction, button: Button):
        u = get_user(interaction.user.id)
        u["xu"] += 2000
        update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
        await interaction.response.send_message(f"🎉 Bút thành công **2,000 Xu**! (Tổng: {u['xu']:,} Xu)", ephemeral=True)

    @discord.ui.button(label="📊 Xem Hồ Sơ", style=discord.ButtonStyle.blurple, custom_id="v6_rank")
    async def rank_btn(self, interaction: discord.Interaction, button: Button):
        u = get_user(interaction.user.id)
        embed = discord.Embed(title=f"📊 HỒ SƠ: {interaction.user.name}", color=discord.Color.dark_blue())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="🎖️ Danh hiệu", value=u["title"], inline=False)
        embed.add_field(name="⭐ Level", value=str(u["level"]), inline=True)
        embed.add_field(name="💰 Tài sản", value=f"{u['xu']:,} Xu", inline=True)
        embed.add_field(name="⚠️ Vi phạm", value=f"{u['warns']} lần", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🏦 Vay Nóng", style=discord.ButtonStyle.red, custom_id="v6_loan")
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

    u = get_user(message.author.id)
    xp = u["xp"] + random.randint(15, 30)
    level = u["level"]
    if xp >= level * 100:
        level += 1
        xp = 0
        await message.channel.send(f"⚡ Ghê đấy {message.author.mention}, vừa cày lên **Level {level}**!")

    update_user(message.author.id, u["xu"], u["warns"], xp, level, u["title"])
    await bot.process_commands(message)

# --- 6. HỆ THỐNG NHẠC ---
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

@bot.tree.command(name="play", description="Phát nhạc từ YouTube vào Voice")
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

# --- 7. TẤT CẢ CÁC LỆNH MENU, QUẢN TRỊ, SÒNG BÀI ---

@bot.tree.command(name="menu", description="Xem danh sách toàn bộ lệnh")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📂 KHO LỆNH TOÀN NĂNG BOT V6",
        description="Đầy đủ tính năng quản trị, sòng bài, rank và phím bấm!",
        color=discord.Color.purple()
    )
    embed.add_field(name="🎮 Giao Diện & Điểm Danh", value="`/panel`, `/daily`, `/rank`, `/loan`, `/pay`", inline=False)
    embed.add_field(name="⚙️ Quản Lý Server", value="`/setwelcome`, `/setgoodbye`, `/setautorole`, `/badword`, `/togglelink`", inline=False)
    embed.add_field(name="🛡️ Kỷ Luật & Trảm Sát", value="`/warn`, `/mute`, `/unmute`, `/kick`, `/ban`, `/clean`", inline=False)
    embed.add_field(name="🎰 Sòng Bạc Casino Toàn Tập", value="`/taixiu`, `/daga`, `/baucua`, `/roulette`, `/blackjack`, `/slots`, `/coinflip`", inline=False)
    embed.add_field(name="🏆 Xếp Hạng & Nhạc", value="`/toprich`, `/toplevel`, `/play`, `/stop`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="panel", description="Mở bảng điều khiển nút bấm nhanh")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(title="🎮 BẢNG ĐIỀU KHIỂN NHANH V6", description="Bấm nút bên dưới để thao tác ngay lập tức!", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, view=QuickPanelView())

@bot.tree.command(name="setwelcome", description="Cài đặt kênh chào mừng")
@app_commands.checks.has_permissions(administrator=True)
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel):
    update_config(interaction.guild.id, "welcome_channel", channel.id)
    await interaction.response.send_message(f"✅ Đã chọn kênh {channel.mention} làm trạm chào mừng!")

@bot.tree.command(name="setgoodbye", description="Cài đặt kênh tiễn biệt")
@app_commands.checks.has_permissions(administrator=True)
async def setgoodbye(interaction: discord.Interaction, channel: discord.TextChannel):
    update_config(interaction.guild.id, "goodbye_channel", channel.id)
    await interaction.response.send_message(f"✅ Đã chọn kênh {channel.mention} làm trạm tiễn biệt!")

@bot.tree.command(name="setautorole", description="Cài đặt tự động cấp role")
@app_commands.checks.has_permissions(administrator=True)
async def setautorole(interaction: discord.Interaction, role: discord.Role):
    update_config(interaction.guild.id, "auto_role", role.id)
    await interaction.response.send_message(f"✅ Mem mới vào sẽ tự ăn Role: **{role.name}**!")

@bot.tree.command(name="badword", description="Thêm từ cấm")
@app_commands.checks.has_permissions(administrator=True)
async def badword(interaction: discord.Interaction, tu_cam: str):
    config = get_server_config(interaction.guild.id)
    words = config["badwords"]
    if tu_cam.lower() not in words:
        words.append(tu_cam.lower())
        update_config(interaction.guild.id, "badwords", ",".join(words))
    await interaction.response.send_message(f"🚫 Đã thêm từ `{tu_cam}` vào danh sách tử hình!")

@bot.tree.command(name="togglelink", description="Bật/Tắt chống gửi link (1: Bật, 0: Tắt)")
@app_commands.checks.has_permissions(administrator=True)
async def togglelink(interaction: discord.Interaction, trang_thai: int):
    if trang_thai not in [0, 1]:
        await interaction.response.send_message("❌ Chỉ chọn `1` hoặc `0`!", ephemeral=True)
        return
    update_config(interaction.guild.id, "antilink", trang_thai)
    st_text = "BẬT" if trang_thai == 1 else "TẮT"
    await interaction.response.send_message(f"🛡️ Đã **{st_text}** chống spam link!")

@bot.tree.command(name="warn", description="Cảnh cáo thành viên")
@app_commands.checks.has_permissions(kick_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, ly_do: str):
    u = get_user(member.id)
    u["warns"] += 1
    update_user(member.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message(f"⚠️ {member.mention} nhận thẻ vàng số **{u['warns']}/3**. Lý do: {ly_do}")
    if u["warns"] >= 3:
        await member.kick(reason="Quá 3 lần cảnh cáo")
        await interaction.channel.send(f"🔨 Đã đá {member.mention} khỏi server!")

@bot.tree.command(name="mute", description="Khóa mõm thành viên")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, member: discord.Member, phut: int, ly_do: str):
    duration = datetime.timedelta(minutes=phut)
    await member.timeout(duration, reason=ly_do)
    await interaction.response.send_message(f"🔇 Đã khóa mõm {member.mention} trong `{phut} phút`. Lý do: {ly_do}")

@bot.tree.command(name="unmute", description="Mở khóa mõm")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(f"🔊 Đã ân xá cho {member.mention}!")

@bot.tree.command(name="kick", description="Đuổi thành viên")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, ly_do: str):
    await member.kick(reason=ly_do)
    await interaction.response.send_message(f"👢 Đã sút {member.mention} ra đường! Lý do: {ly_do}")

@bot.tree.command(name="ban", description="Trục xuất vĩnh viễn")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, ly_do: str):
    await member.ban(reason=ly_do)
    await interaction.response.send_message(f"⚡ Đã cho {member.mention} bay màu vĩnh viễn! Lý do: {ly_do}")

@bot.tree.command(name="clean", description="Xóa nhanh tin nhắn rác")
@app_commands.checks.has_permissions(manage_messages=True)
async def clean(interaction: discord.Interaction, so_luong: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=so_luong)
    await interaction.followup.send(f"🧹 Đã xóa sạch {len(deleted)} tin nhắn rác!", ephemeral=True)

@bot.tree.command(name="daily", description="Điểm danh nhận xu hằng ngày")
async def daily(interaction: discord.Interaction):
    u = get_user(interaction.user.id)
    u["xu"] += 2000
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message(f"🎁 Nhận thành công **2,000 Xu**! (Ví: {u['xu']:,} Xu)")

@bot.tree.command(name="pay", description="Chuyển xu cho người khác")
async def pay(interaction: discord.Interaction, member: discord.Member, so_xu: int):
    if so_xu <= 0 or member.id == interaction.user.id:
        await interaction.response.send_message("❌ Số xu không hợp lệ!", ephemeral=True)
        return
    sender = get_user(interaction.user.id)
    if sender["xu"] < so_xu:
        await interaction.response.send_message("❌ Không đủ xu để chuyển!", ephemeral=True)
        return
    receiver = get_user(member.id)
    update_user(interaction.user.id, sender["xu"] - so_xu, sender["warns"], sender["xp"], sender["level"], sender["title"])
    update_user(member.id, receiver["xu"] + so_xu, receiver["warns"], receiver["xp"], receiver["level"], receiver["title"])
    await interaction.response.send_message(f"💸 Đã chuyển thành công **{so_xu:,} Xu** cho {member.mention}!")

@bot.tree.command(name="loan", description="Vay nóng 500 Xu cứu đói")
async def loan(interaction: discord.Interaction):
    u = get_user(interaction.user.id)
    if u["xu"] >= 200:
        await interaction.response.send_message("❌ Vẫn còn tiền, không cho vay!", ephemeral=True)
        return
    u["xu"] += 500
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message("🏦 Bơm nóng **500 Xu** cứu đói thành công!")

@bot.tree.command(name="taixiu", description="Chơi tài xỉu")
async def taixiu(interaction: discord.Interaction, cuoc: int, luachon: str):
    u = get_user(interaction.user.id)
    if cuoc <= 0 or cuoc > u["xu"]:
        await interaction.response.send_message("❌ Không đủ xu!", ephemeral=True)
        return
    luachon = luachon.lower()
    if luachon not in ["tai", "xiu"]:
        await interaction.response.send_message("❌ Chọn `tai` hoặc `xiu`!", ephemeral=True)
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

@bot.tree.command(name="daga", description="Đá gà cựa sắt (do/xanh)")
async def daga(interaction: discord.Interaction, cuoc: int, phe: str):
    u = get_user(interaction.user.id)
    if cuoc <= 0 or cuoc > u["xu"]:
        await interaction.response.send_message("❌ Không đủ xu!", ephemeral=True)
        return
    phe = phe.lower()
    if phe not in ["do", "xanh"]:
        await interaction.response.send_message("❌ Chọn `do` hoặc `xanh`!", ephemeral=True)
        return
    win = random.choice(["do", "xanh"])
    if phe == win:
        u["xu"] += cuoc
        msg = f"🐓 Gà **{win.upper()}** thắng! Bú **+{cuoc} Xu**."
    else:
        u["xu"] -= cuoc
        msg = f"🐓 Gà **{win.upper()}** thắng! Gà mày ngỏm, mất **-{cuoc} Xu**."
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message(msg)

@bot.tree.command(name="baucua", description="Bầu cua tôm cá")
async def baucua(interaction: discord.Interaction, cuoc: int, cua_dat: str):
    u = get_user(interaction.user.id)
    if cuoc <= 0 or cuoc > u["xu"]:
        await interaction.response.send_message("❌ Không đủ xu!", ephemeral=True)
        return
    dict_bc = {"bau": "Bầu", "cua": "Cua", "tom": "Tôm", "ca": "Cá", "ga": "Gà", "nai": "Nai"}
    cua_dat = cua_dat.lower()
    if cua_dat not in dict_bc:
        await interaction.response.send_message("❌ Chọn: `bau`, `cua`, `tom`, `ca`, `ga`, `nai`!", ephemeral=True)
        return
    ket_qua = [random.choice(list(dict_bc.keys())) for _ in range(3)]
    count = ket_qua.count(cua_dat)
    if count > 0:
        thang = cuoc * count
        u["xu"] += thang
        msg = f"🎲 Ra: {', '.join([dict_bc[k] for k in ket_qua])}\n🎉 Trúng {count} con, húp **+{thang} Xu**!"
    else:
        u["xu"] -= cuoc
        msg = f"🎲 Ra: {', '.join([dict_bc[k] for k in ket_qua])}\n😭 Trượt, mất **-{cuoc} Xu**."
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message(msg)

@bot.tree.command(name="roulette", description="Vòng quay Roulette")
async def roulette(interaction: discord.Interaction, cuoc: int, o_dat: str):
    u = get_user(interaction.user.id)
    if cuoc <= 0 or cuoc > u["xu"]:
        await interaction.response.send_message("❌ Không đủ xu!", ephemeral=True)
        return
    so_quay = random.randint(0, 36)
    mau = "do" if so_quay % 2 == 1 else "den"
    o_dat = o_dat.lower()
    thang = 0
    if o_dat in ["do", "den"] and o_dat == mau:
        thang = cuoc
    elif o_dat.isdigit() and int(o_dat) == so_quay:
        thang = cuoc * 35
    if thang > 0:
        u["xu"] += thang
        msg = f"🎡 Ra số {so_quay} ({mau.upper()})! Thắng lớn **+{thang} Xu**!"
    else:
        u["xu"] -= cuoc
        msg = f"🎡 Ra số {so_quay} ({mau.upper()})! Mất **-{cuoc} Xu**."
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message(msg)

@bot.tree.command(name="blackjack", description="Xì dách 21 điểm")
async def blackjack(interaction: discord.Interaction, cuoc: int):
    u = get_user(interaction.user.id)
    if cuoc <= 0 or cuoc > u["xu"]:
        await interaction.response.send_message("❌ Không đủ xu!", ephemeral=True)
        return
    p_score = random.randint(15, 23)
    b_score = random.randint(16, 22)
    msg = f"🃏 Mày: {p_score}đ | Nhà Cái: {b_score}đ\n"
    if p_score > 21:
        u["xu"] -= cuoc
        msg += f"Quắc! Mất **-{cuoc} Xu**."
    elif b_score > 21 or p_score > b_score:
        u["xu"] += cuoc
        msg += f"Thắng nhà cái! Bú **+{cuoc} Xu**."
    elif p_score < b_score:
        u["xu"] -= cuoc
        msg += f"Nhà cái cao điểm hơn! Mất **-{cuoc} Xu**."
    else:
        msg += "Hòa tiền!"
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message(msg)

@bot.tree.command(name="slots", description="Quay hũ máy xèng 777")
async def slots(interaction: discord.Interaction, cuoc: int):
    u = get_user(interaction.user.id)
    if cuoc <= 0 or cuoc > u["xu"]:
        await interaction.response.send_message("❌ Không đủ xu!", ephemeral=True)
        return
    fruits = ["🍒", "🍋", "🍊", "🔔", "⭐", "💎", "7️⃣"]
    roll = [random.choice(fruits) for _ in range(3)]
    msg = f"🎰 | {roll[0]} | {roll[1]} | {roll[2]} |\n"
    if roll[0] == roll[1] == roll[2]:
        thang = cuoc * 10
        u["xu"] += thang
        msg += f"JACKPOT! Húp **+{thang} Xu**!"
    elif roll[0] == roll[1] or roll[1] == roll[2] or roll[0] == roll[2]:
        thang = cuoc * 2
        u["xu"] += thang
        msg += f"Trúng cặp! Nhận **+{thang} Xu**."
    else:
        u["xu"] -= cuoc
        msg += f"Trượt, mất **-{cuoc} Xu**."
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message(msg)

@bot.tree.command(name="coinflip", description="Tung đồng xu (ngửa / sấp)")
async def coinflip(interaction: discord.Interaction, cuoc: int, luachon: str):
    u = get_user(interaction.user.id)
    if cuoc <= 0 or cuoc > u["xu"]:
        await interaction.response.send_message("❌ Không đủ xu!", ephemeral=True)
        return
    luachon = luachon.lower()
    if luachon not in ["ngua", "sap"]:
        await interaction.response.send_message("❌ Chọn `ngua` hoặc `sap`!", ephemeral=True)
        return
    kq = random.choice(["ngua", "sap"])
    if luachon == kq:
        u["xu"] += cuoc
        msg = f"🪙 Ra: **{kq.upper()}** -> Thắng **+{cuoc} Xu**."
    else:
        u["xu"] -= cuoc
        msg = f"🪙 Ra: **{kq.upper()}** -> Thua **-{cuoc} Xu**."
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"], u["title"])
    await interaction.response.send_message(msg)

@bot.tree.command(name="toprich", description="Top đại gia lắm xu")
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

@bot.tree.command(name="toplevel", description="Top cao thủ cày level")
async def toplevel(interaction: discord.Interaction):
    conn = sqlite3.connect(fn_db)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    embed = discord.Embed(title="⚡ TOP 5 CAO THỦ CÀY LEVEL", color=discord.Color.purple())
    for idx, (uid, lvl, xp) in enumerate(rows, 1):
        user = interaction.guild.get_member(uid)
        name = user.name if user else f"User ID: {uid}"
        embed.add_field(name=f"Top {idx}: {name}", value=f"⭐ Level {lvl} ({xp} XP)", inline=False)
    await interaction.response.send_message(embed=embed)

# --- KHỞI CHẠY ---
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Lỗi: Thiếu DISCORD_TOKEN!")
