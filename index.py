from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from discord.ui import Button, View
from discord.ext import commands
import aiohttp
import json
import re
import io
import asyncio
import datetime
from datetime import timedelta
import aiofiles
import random
import psutil
import platform
import time
import subprocess
import requests
import socket
import ssl
import google.generativeai as genai  # Import thư viện Gemini

# Lưu thời gian bot khởi động
start_time = time.time()

# Tải biến môi trường từ file .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Lấy API Key của OpenAI từ .env
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Lấy API Key của Google từ .env
FILE_PATH = "data.json"

# Danh sách user ID được phép sử dụng lệnh này (admin ID)
ADMIN_IDS = ["1173048293048197170"]

# Cấu hình Gemini API
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')  # Chọn model Gemini

# Tải dữ liệu từ file JSON
def load_data():
    try:
        if not os.path.exists(FILE_PATH):
            return {}
        with open(FILE_PATH, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    except FileNotFoundError:
        return {}

# Lưu dữ liệu vào file JSON
def save_data(data):
    with open(FILE_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

# Hàm lấy dữ liệu
def get_data(key, default=None):
    data = load_data()
    return data.get(key, default)

# Hàm set dữ liệu
def set_data(key, value):
    data = load_data()
    data[key] = value
    save_data(data)

# Danh sách kênh hợp lệ
ALLOWED_CHANNEL_IDS = get_data("allowed_channels", [])

# Tạo bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Đăng ký lệnh slash và lưu thông tin kênh
@bot.event
async def on_ready():
    try:
        await bot.change_presence(activity=discord.Game("COMMANDS BOT | /help"))
        synced = await bot.tree.sync()
        print(f"✅ Bot đã sẵn sàng. Đăng nhập dưới dạng {bot.user}")
        print(f"✅ Đã đồng bộ {len(synced)} lệnh slashcommand !")
    except Exception as e:
        print(f"❌ Lỗi đồng bộ lệnh slash: {e}")

    # Lấy tất cả kênh
    all_channels = {}
    for guild in bot.guilds:
        for channel in guild.text_channels:
            all_channels[channel.id] = {
              "id": channel.id,
              "name": channel.name,
              "guild_id": guild.id,
              "guild_name": guild.name
            }

    # Lưu thông tin tất cả kênh vào file data.json
    set_data("all_channels", all_channels)

# Lệnh thêm kênh
@bot.tree.command(name="add-channel", description="Thêm kênh vào danh sách kênh được phép")
@app_commands.describe(channel_id="ID của kênh")
async def add_channel(interaction: discord.Interaction, channel_id: str):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này.", ephemeral=True)
        return

    try:
        channel_id = int(channel_id)
        if channel_id not in ALLOWED_CHANNEL_IDS:
            ALLOWED_CHANNEL_IDS.append(channel_id)
            set_data("allowed_channels", ALLOWED_CHANNEL_IDS)
            await interaction.response.send_message(
                f"✅ Đã thêm kênh có ID `{channel_id}` vào danh sách kênh được phép.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Kênh có ID `{channel_id}` đã có trong danh sách kênh được phép.", ephemeral=True
            )
    except ValueError:
        await interaction.response.send_message(
            f"❌ ID kênh không hợp lệ. Vui lòng nhập số.", ephemeral=True
        )

# Lệnh xóa kênh
@bot.tree.command(name="remove-channel", description="Xóa kênh khỏi danh sách kênh được phép")
@app_commands.describe(channel_id="ID của kênh")
async def remove_channel(interaction: discord.Interaction, channel_id: str):
    if str(interaction.user.id) not in ADMIN_IDS:
        await interaction.response.send_message("❌ Bạn không có quyền sử dụng lệnh này.", ephemeral=True)
        return
    try:
        channel_id = int(channel_id)
        if channel_id in ALLOWED_CHANNEL_IDS:
            ALLOWED_CHANNEL_IDS.remove(channel_id)
            set_data("allowed_channels", ALLOWED_CHANNEL_IDS)
            await interaction.response.send_message(
                f"✅ Đã xóa kênh có ID `{channel_id}` khỏi danh sách kênh được phép.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Kênh có ID `{channel_id}` không có trong danh sách kênh được phép.", ephemeral=True
            )
    except ValueError:
        await interaction.response.send_message(
            f"❌ ID kênh không hợp lệ. Vui lòng nhập số.", ephemeral=True
        )

# Lệnh /dich
@bot.tree.command(name="dich", description="Dịch văn bản sang ngôn ngữ khác")
@app_commands.describe(lang="Ngôn ngữ đích", dq="Văn bản cần dịch")
async def dich_command(interaction: discord.Interaction, lang: str, dq: str):
    api_url = f"https://minhnguyen3004.x10.mx/dich.php?lang={lang}&dq={dq}"

    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json(encoding='utf-8')
                    if data["success"]:
                        embed = discord.Embed(
                            title="🔤 Kết quả dịch:",
                            description=f"**Dịch từ:** {data['lang']} **→ Dịch sang:** {data['lang_dich']}",
                            color=discord.Color.green()
                        )
                        embed.add_field(
                            name="📝 Văn bản gốc",
                            value=f"```\n{data['text']}\n```",
                            inline=False
                        )
                        embed.add_field(
                            name="🔁 Văn bản đã dịch",
                            value=f"```\n{data['dich_text']}\n```",
                            inline=False
                        )
                        embed.set_footer(
                            text="✨ Dịch ngay và khám phá! ✨",
                            icon_url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                        )
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message(f"Lỗi: Không thể dịch văn bản.")
                else:
                    await interaction.response.send_message(
                        f"Lỗi: API không phản hồi (Mã lỗi {response.status})."
                    )
    except Exception as e:
        await interaction.response.send_message(f"Đã xảy ra lỗi: {e}")

# Lệnh /buff-like
@bot.tree.command(name="buff-like", description="Lấy số lượt thích cho UID Free Fire ( NEW UPDATE )")
@app_commands.describe(uid="Nhập UID người chơi")
async def buff_like(interaction: discord.Interaction, uid: str):
    url = f"https://ff-community-api.vercel.app/ff.Likes?uid={uid}&r=camon100nguoidangkikenhapihacker"
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json(encoding="utf-8")
                    if "message" in data and data["message"] == "Player has reached max likes today!":
                        embed = discord.Embed(
                            title="**❌ Không thể buff lượt thích!**",
                            description=f"UID `{uid}` đã đạt **lượt thích tối đa hôm nay**.",
                            color=discord.Color.red(),
                        )
                        embed.set_footer(
                            text="Hãy thử lại vào ngày mai hoặc liên hệ hỗ trợ.",
                            icon_url="https://th.bing.com/th/id/R.1ea2bfaf42437bd4a85ae448398f9e15?rik=yQ0RfB1kDRsDfw&pid=ImgRaw&r=0",
                        )
                        await interaction.followup.send(embed=embed)
                        return
                    embed = discord.Embed(
                        title=f"**🤖 Buff-Like ID : {uid} 🤖**",
                        description="Thông tin chi tiết:",
                        color=discord.Color.blue(),
                    )
                    embed.add_field(
                        name="***📛 Tên tài khoản:***",
                        value=f"```{data['AccountName']}```",
                        inline=False,
                    )
                    embed.add_field(
                        name="***🌍 Khu vực :***",
                        value=f"```{data['AccountRegion']}```",
                        inline=True,
                    )
                    embed.add_field(
                        name="***🏅 Level :***",
                        value=f"```{data['AccountLevel']}```",
                        inline=True,
                    )
                    embed.add_field(
                        name="***💳 UID:***",
                        value=f"```{data['AccountUID']}```",
                        inline=False,
                    )
                    embed.add_field(
                        name="***👍 Lượt thích trước:***",
                        value=f"```{data['LikesBefore']}```",
                        inline=True,
                    )
                    embed.add_field(
                        name="***❤️ Lượt thích thêm:***",
                        value=f"```{data['LikesAdded']}```",
                        inline=True,
                    )
                    embed.add_field(
                        name="***🔥 Lượt thích sau:***",
                        value=f"```{data['LikesAfter']}```",
                        inline=True,
                    )
                    embed.set_footer(
                        text="Developer: HAV",
                        icon_url="https://th.bing.com/th/id/R.1ea2bfaf42437bd4a85ae448398f9e15?rik=yQ0RfB1kDRsDfw&pid=ImgRaw&r=0",
                    )
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(
                        f"Đang Update"
                    )
    except Exception as e:
        await interaction.followup.send(f"Đã xảy ra lỗi: {e}")

# lệnh /info-ff
@bot.tree.command(name="info-ff", description="Lấy thông tin Free Fire từ UID ( NEW UPDATE )")
@app_commands.describe(uid="Nhập UID người chơi")
async def info_ff(interaction: discord.Interaction, uid: str):
    api_url = f"https://ffinfo-server.vercel.app/v1/api/playerinfo?uid={uid}"
    await interaction.response.defer()

    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json(encoding="utf-8")

                    account_info = data
                    guild_info = data.get("Guild Information", {})
                    pet_info = data.get("Pet Information", {})
                    equipped_items = data.get("Equipped Items", {})
                    signature = account_info.get("AccountSignature", "N/A").replace("\\n", "\n")

                    embed = discord.Embed(
                        title=f"🎮 Thông tin người chơi: {account_info.get('AccountName', 'N/A')}",
                        description=f"**UID:** {account_info.get('AccountUID', 'N/A')}\n**Khu vực:** {account_info.get('AccountRegion', 'N/A')}",
                        color=discord.Color.blue(),
                    )
                    embed.description += f"\n\n**Tiểu sử:**\n{signature}"
                    embed.add_field(
                        name="📊 Thông tin cơ bản",
                        value=f"""
    **Cấp độ:** {account_info.get('AccountLevel', 'N/A')}
    **Lượt thích:** {account_info.get('AccountLikes', 'N/A')}
    **EXP:** {account_info.get('AccountEXP', 'N/A')}
    **Phiên bản:** {account_info.get('ReleaseVersion', 'N/A')}
    **Thời gian tạo tài khoản:** {account_info.get('AccountCreateTime', 'N/A')}
    **Lần đăng nhập cuối:** {account_info.get('AccountLastLogin', 'N/A')}
    """,
                        inline=False,
                    )
                    embed.add_field(
                        name="🏆 Thông tin Rank",
                        value=f"""
    **BR Rank:** {account_info.get('BrRank', 'N/A')} (Max: {account_info.get('BrMaxRank', 'N/A')})
    **CS Rank:** {account_info.get('CsRank', 'N/A')} (Max: {account_info.get('CsMaxRank', 'N/A')})
    """,
                        inline=False,
                    )
                    if guild_info:
                        embed.add_field(
                            name="🏰 Guild",
                            value=f"""
    **Tên:** {guild_info.get('GuildName', 'N/A')}
    **ID:** {guild_info.get('GuildID', 'N/A')}
    **Cấp:** {guild_info.get('GuildLevel', 'N/A')}
    **Thành viên:** {guild_info.get('GuildMember', 'N/A')}/{guild_info.get('GuildCapacity', 'N/A')}
    """,
                            inline=False,
                        )

                    if pet_info:
                          embed.add_field(
                              name="🐾 Pet",
                              value=f"""
    **Tên:** {pet_info.get('PetName', 'N/A')}
    **ID:** {pet_info.get('PetID', 'N/A')}
    **Cấp:** {pet_info.get('PetLevel', 'N/A')}
    **EXP:** {pet_info.get('PetEXP', 'N/A')}
    """,
                              inline=False,
                          )

                    await interaction.followup.send(embed=embed)

                    avatar_url = f"https://ff-community-api.vercel.app/library/icons?id={account_info.get('AccountAvatarId', 'N/A')}"
                    banner_url = f"https://ff-community-api.vercel.app/library/icons?id={account_info.get('AccountBannerId', 'N/A')}"

                    weapons = equipped_items.get("EquippedWeapon", [])
                    outfits = equipped_items.get("EquippedOutfit", [])


                    if avatar_url:
                        async with session.get(avatar_url) as avatar_response:
                            if avatar_response.status == 200:
                                avatar_data = io.BytesIO(await avatar_response.read())
                                await interaction.followup.send(
                                    content="**Avatar**",
                                    file=discord.File(avatar_data, filename="avatar.png"),
                                )


                    if banner_url:
                        async with session.get(banner_url) as banner_response:
                            if banner_response.status == 200:
                                banner_data = io.BytesIO(await banner_response.read())
                                await interaction.followup.send(
                                    content="**Banner**",
                                    file=discord.File(banner_data, filename="banner.png"),
                                )

                    for idx, weapon in enumerate(weapons, 1):
                        weapon_url = weapon.get("Items Icon")
                        if weapon_url:
                            async with session.get(weapon_url) as weapon_response:
                                if weapon_response.status == 200:
                                    weapon_data = io.BytesIO(await weapon_response.read())
                                    await interaction.followup.send(
                                        content=f"**Weapon {idx}**",
                                        file=discord.File(weapon_data, filename=f"weapon_{idx}.png"),
                                    )


                    for idx, outfit in enumerate(outfits, 1):
                        outfit_url = outfit.get("Items Icon")
                        if outfit_url:
                            async with session.get(outfit_url) as outfit_response:
                                if outfit_response.status == 200:
                                    outfit_data = io.BytesIO(await outfit_response.read())
                                    await interaction.followup.send(
                                        content=f"**Trang Bị {idx}**",
                                        file=discord.File(outfit_data, filename=f"outfit_{idx}.png"),
                                    )
                else:
                    await interaction.followup.send(
                        f"❌ API không phản hồi (Mã lỗi {response.status})."
                    )
    except Exception as e:
        await interaction.followup.send(f"❌ Đã xảy ra lỗi: {e}")

# Lệnh /hav (sửa đổi để gửi tin nhắn công khai)
@bot.tree.command(name="hav", description="Chat với AI")
@app_commands.describe(cauhoi="Câu hỏi của bạn")
async def hav_command(interaction: discord.Interaction, cauhoi: str):
    await interaction.response.defer()  # Để bot có thời gian xử lý
    try:
        response = model.generate_content(cauhoi)
        chat_response = response.text
        # Kiểm tra độ dài response để tránh vượt quá giới hạn 2000 ký tự của Discord
        if len(chat_response) > 2000:
            chat_response = chat_response[:1900] + "... (bị cắt bớt)"
        await interaction.channel.send(f"**{interaction.user.display_name}** hỏi: {cauhoi}\n**HAV BOT** trả lời: {chat_response}")
    except Exception as e:
        await interaction.followup.send(f"❌ Đã xảy ra lỗi: {e}")

bot.run(TOKEN)