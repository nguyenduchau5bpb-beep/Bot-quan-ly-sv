import os
import threading
import sqlite3
import random
import datetime
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask

# --- WEB SERVER FLASK (GIỮ BOT SỐNG TRÊN RENDER) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Discord cấp độ tối cao đang hoạt động 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- DATABASE SQLITE ---
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
                        level INTEGER DEFAULT 1
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

def add_badword_db(guild_id, word):
    config = get_server_config(guild_id)
    words = config["badwords"]
    if word not in words:
        words.append(word)
        conn = sqlite3.connect(fn_db)
        cursor = conn.cursor()
        cursor.execute("UPDATE config SET badwords = ? WHERE guild_id = ?", (",".join(words), guild_id))
        conn.commit()
        conn.close()

def get_user(user_id):
    conn = sqlite3.connect(fn_db)
    cursor = conn.cursor()
    cursor.execute("SELECT xu, warns, xp, level FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, xu, warns, xp, level) VALUES (?, 1000, 0, 0, 1)", (user_id,))
        conn.commit()
        row = (1000, 0, 0, 1)
    conn.close()
    return {"xu": row[0], "warns": row[1], "xp": row[2], "level": row[3]}

def update_user(user_id, xu, warns, xp, level):
    conn = sqlite3.connect(fn_db)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET xu = ?, warns = ?, xp = ?, level = ? WHERE user_id = ?", (xu, warns, xp, level, user_id))
    conn.commit()
    conn.close()

# --- CORE BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class UltimateBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🔥 Đã nạp toàn bộ vũ khí hủy diệt vào Slash Commands!")

bot = UltimateBot()

@bot.event
async def on_ready():
    print(f"🚀 Bot {bot.user} đã thức tỉnh toàn bộ công lực!")
    await bot.change_presence(activity=discord.Game(name="/menu | Bố mày quản server"))

@bot.event
async def on_member_join(member):
    config = get_server_config(member.guild.id)
    if config["auto_role"]:
        role = member.guild.get_role(config["auto_role"])
        if role:
            try:
                await member.add_roles(role)
            except Exception as e:
                print(f"Lỗi cấp role: {e}")

    if config["welcome_channel"]:
        channel = member.guild.get_channel(config["welcome_channel"])
        if channel:
            embed = discord.Embed(
                title="🎉 CÓ CON GÀ MỚI ĐỔ BỘ!",
                description=f"Chào mừng {member.mention} đã lạc vào **{member.guild.name}**!\nLo mà sống cho đúng luật, đừng để tao phải ra tay.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    config = get_server_config(member.guild.id)
    if config["goodbye_channel"]:
        channel = member.guild.get_channel(config["goodbye_channel"])
        if channel:
            embed = discord.Embed(
                title="👋 MỘT THẰNG NỮA ĐÃ CÚT",
                description=f"Tạm biệt {member.name} ({member.mention}). Bớt đi một đứa báo đời cho sạch server!",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    config = get_server_config(message.guild.id)
    content = message.content.lower()

    # 1. Antilink tự động trảm
    if config["antilink"] == 1 and ("http://" in content or "https://" in content or "discord.gg/" in content):
        if not message.author.guild_permissions.manage_messages:
            await message.delete()
            await message.timeout(datetime.timedelta(minutes=10), reason="Spam link bậy bạ")
            await message.channel.send(f"🚨 {message.author.mention} vừa quăng link bậy nên đã bị khóa mõm 10 phút!", delete_after=5)
            return

    # 2. Lọc từ cấm siêu tốc
    for word in config["badwords"]:
        if word and word in content:
            await message.delete()
            u = get_user(message.author.id)
            u["warns"] += 1
            update_user(message.author.id, u["xu"], u["warns"], u["xp"], u["level"])
            
            await message.channel.send(f"⚠️ {message.author.mention}, mồm mép láo toét! Đã xóa tin nhắn và cộng 1 thẻ vàng (Tổng: {u['warns']}/3)", delete_after=5)
            
            if u["warns"] >= 3:
                try:
                    await message.author.kick(reason="Chửi tục quá 3 lần")
                    await message.channel.send(f"🔨 Đã tự động sút {message.author.mention} ra khỏi server vì tích đủ 3 thẻ vàng chửi tục!")
                except:
                    pass
            return

    # 3. XP & Level tự động cày cuốc
    u = get_user(message.author.id)
    xp = u["xp"] + random.randint(15, 35)
    level = u["level"]
    
    if xp >= level * 100:
        level += 1
        xp = 0
        await message.channel.send(f"⚡ Ghê đấy {message.author.mention}, đã cày lên **Level {level}** rồi cơ à!")

    update_user(message.author.id, u["xu"], u["warns"], xp, level)
    await bot.process_commands(message)

# --- SLASH COMMANDS TOÀN NĂNG ---

@bot.tree.command(name="menu", description="Bảng điều khiển tối tân của bot")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💀 HỆ THỐNG QUẢN LÝ TỐI CAO",
        description="Vũ khí hạng nặng - Tự động trảm sát 100%",
        color=discord.Color.dark_red()
    )
    embed.add_field(name="⚙️ Cấu Hình Server", value="`/setwelcome`, `/setgoodbye`, `/setautorole`, `/badword`, `/togglelink`", inline=False)
    embed.add_field(name="🛡️ Kỷ Luật & Trảm Sát", value="`/warn`, `/mute`, `/unmute`, `/kick`, `/ban`, `/clean`", inline=False)
    embed.add_field(name="🎮 Tương Tác & Kinh Tế", value="`/daily`, `/rank`, `/pay`, `/taixiu`", inline=False)
    embed.set_footer(text="Không khoan nhượng cho bất kỳ thành viên nào báo đời.")
    await interaction.response.send_message(embed=embed)

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

@bot.tree.command(name="setautorole", description="Cài đặt tự động cấp role khi có mem mới")
@app_commands.checks.has_permissions(administrator=True)
async def setautorole(interaction: discord.Interaction, role: discord.Role):
    update_config(interaction.guild.id, "auto_role", role.id)
    await interaction.response.send_message(f"✅ Từ giờ mem mới vào sẽ tự ăn ngay Role: **{role.name}**!")

@bot.tree.command(name="badword", description="Thêm từ cấm vào danh sách tử hình")
@app_commands.checks.has_permissions(administrator=True)
async def badword(interaction: discord.Interaction, tu_cam: str):
    add_badword_db(interaction.guild.id, tu_cam.lower())
    await interaction.response.send_message(f"🚫 Đã nạp từ `{tu_cam}` vào danh sách tử hình!")

@bot.tree.command(name="togglelink", description="Bật/Tắt chống gửi link (1: Bật, 0: Tắt)")
@app_commands.checks.has_permissions(administrator=True)
async def togglelink(interaction: discord.Interaction, trang_thai: int):
    if trang_thai not in [0, 1]:
        await interaction.response.send_message("❌ Chỉ chọn `1` hoặc `0`!", ephemeral=True)
        return
    update_config(interaction.guild.id, "antilink", trang_thai)
    st_text = "BẬT" if trang_thai == 1 else "TẮT"
    await interaction.response.send_message(f"🛡️ Đã **{st_text}** hệ thống chống spam link tự động khóa mõm!")

@bot.tree.command(name="warn", description="Cảnh cáo thành viên")
@app_commands.checks.has_permissions(kick_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, ly_do: str):
    u = get_user(member.id)
    u["warns"] += 1
    update_user(member.id, u["xu"], u["warns"], u["xp"], u["level"])
    
    await interaction.response.send_message(f"⚠️ {member.mention} đã nhận thẻ vàng số **{u['warns']}/3**. Lý do: {ly_do}")
    if u["warns"] >= 3:
        await member.kick(reason="Quá 3 lần cảnh cáo")
        await interaction.channel.send(f"🔨 Đã đá đít {member.mention} ra khỏi server vì đủ combo 3 cáo trạng!")

@bot.tree.command(name="mute", description="Khóa mõm thành viên ngứa đòn")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, member: discord.Member, phut: int, ly_do: str):
    duration = datetime.timedelta(minutes=phut)
    await member.timeout(duration, reason=ly_do)
    await interaction.response.send_message(f"🔇 Đã nhốt {member.mention} vào ngục tối trong `{phut} phút`. Lý do: {ly_do}")

@bot.tree.command(name="unmute", description="Thả tự do cho thành viên")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(f"🔊 Đã ân xá, thả tự do cho cái mồm của {member.mention}!")

@bot.tree.command(name="kick", description="Sút cổ một đứa ra khỏi server")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, ly_do: str):
    await member.kick(reason=ly_do)
    await interaction.response.send_message(f"👢 Đã sút thành công {member.mention} ra đường! Lý do: {ly_do}")

@bot.tree.command(name="ban", description="Vĩnh viễn trục xuất một đứa ra khỏi server")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, ly_do: str):
    await member.ban(reason=ly_do)
    await interaction.response.send_message(f"⚡ Đã cho {member.mention} bay màu vĩnh viễn khỏi server! Lý do: {ly_do}")

@bot.tree.command(name="clean", description="Xóa rác hàng loạt tin nhắn")
@app_commands.checks.has_permissions(manage_messages=True)
async def clean(interaction: discord.Interaction, so_luong: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=so_luong)
    await interaction.followup.send(f"🧹 Đã thiêu hủy sạch sẽ {len(deleted)} tin nhắn rác!", ephemeral=True)

@bot.tree.command(name="daily", description="Điểm danh nhận xu hằng ngày")
async def daily(interaction: discord.Interaction):
    u = get_user(interaction.user.id)
    u["xu"] += 2000
    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"])
    await interaction.response.send_message(f"🎁 {interaction.user.mention} vừa đút túi **2,000 Xu** điểm danh! (Tổng tài sản: {u['xu']} Xu)")

@bot.tree.command(name="pay", description="Chuyển xu cho người khác")
async def pay(interaction: discord.Interaction, member: discord.Member, so_xu: int):
    if so_xu <= 0 or member.id == interaction.user.id:
        await interaction.response.send_message("❌ Số xu không hợp lệ hoặc tự chuyển cho chính mình!", ephemeral=True)
        return

    sender = get_user(interaction.user.id)
    if sender["xu"] < so_xu:
        await interaction.response.send_message("❌ Nghèo rớt mồng tơi mà đòi làm từ thiện! Không đủ xu.", ephemeral=True)
        return

    receiver = get_user(member.id)
    update_user(interaction.user.id, sender["xu"] - so_xu, sender["warns"], sender["xp"], sender["level"])
    update_user(member.id, receiver["xu"] + so_xu, receiver["warns"], receiver["xp"], receiver["level"])

    await interaction.response.send_message(f"💸 {interaction.user.mention} đã chuyển thành công **{so_xu} Xu** cho {member.mention}!")

@bot.tree.command(name="rank", description="Xem cấp độ và tài sản chiến binh")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    u = get_user(target.id)
    
    embed = discord.Embed(title=f"📊 HỒ SƠ CHIẾN BINH: {target.name}", color=discord.Color.blue())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="⭐ Level", value=str(u["level"]), inline=True)
    embed.add_field(name="📈 XP", value=f"{u['xp']} / {u['level'] * 100}", inline=True)
    embed.add_field(name="💰 Tài sản", value=f"{u['xu']} Xu", inline=True)
    embed.add_field(name="⚠️ Vi phạm", value=f"{u['warns']} lần", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="taixiu", description="Khô máu với game tài xỉu")
async def taixiu(interaction: discord.Interaction, cuoc: int, luachon: str):
    u = get_user(interaction.user.id)
    if cuoc <= 0 or cuoc > u["xu"]:
        await interaction.response.send_message("❌ Cược láo hoặc không đủ xu mà đòi chơi lớn à?", ephemeral=True)
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
        msg = f"🎲 Xúc xắc: {xuc_xac} (Tổng: {tong} - **{kq.upper()}**)\n🎉 Húp trọn **+{cuoc} Xu**!"
    else:
        u["xu"] -= cuoc
        msg = f"🎲 Xúc xắc: {xuc_xac} (Tổng: {tong} - **{kq.upper()}**)\n😭 Sạch túi! Mất **-{cuoc} Xu**."

    update_user(interaction.user.id, u["xu"], u["warns"], u["xp"], u["level"])
    await interaction.response.send_message(msg)

# --- KHỞI CHẠY ---
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Lỗi: Thiếu DISCORD_TOKEN!")
