import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
import os
from motor.motor_asyncio import AsyncIOMotorClient

# =====================
# SOZLAMALAR
# =====================
BOT_TOKEN = os.environ.get("8677339015:AAFJO3bngk6AVZqYGP2R88ldw5hVOCKwgho")
MONGO_URI = os.environ.get("mongodb+srv://javohiraxatov980_db_user:fGhf8nNY3BDGE08u@cluster0.rmrry9g.mongodb.net/?appName=Cluster0")
CHANNEL_ID = "@englishhub1uz"
ADMIN_ID = 5027894185

# =====================
# MONGODB ULANISH
# =====================
client = AsyncIOMotorClient(MONGO_URI)
db = client["referal_bot"]
users_col = db["users"]
referrals_col = db["referrals"]

# =====================
# YORDAMCHI FUNKSIYALAR
# =====================
async def get_user(user_id: str):
    return await users_col.find_one({"_id": user_id})

async def save_user(user_id: str, username: str, name: str):
    await users_col.update_one(
        {"_id": user_id},
        {"$setOnInsert": {"username": username, "name": name, "invited": 0}},
        upsert=True
    )

async def increment_invited(referrer_id: str):
    await users_col.update_one(
        {"_id": referrer_id},
        {"$inc": {"invited": 1}}
    )

async def get_referral(user_id: str):
    return await referrals_col.find_one({"_id": user_id})

async def save_referral(user_id: str, referrer_id: str):
    await referrals_col.insert_one({"_id": user_id, "referrer": referrer_id})

# =====================
# BOT VA DISPATCHER
# =====================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =====================
# /start COMMAND
# =====================
@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.full_name

    await save_user(user_id, username, message.from_user.full_name)

    # Referral tekshirish
    args = message.text.split()
    if len(args) > 1:
        referrer_id = args[1]
        existing_ref = await get_referral(user_id)
        referrer = await get_user(referrer_id)

        if referrer_id != user_id and referrer and not existing_ref:
            await save_referral(user_id, referrer_id)
            await increment_invited(referrer_id)

            referrer_data = await get_user(referrer_id)
            try:
                await bot.send_message(
                    int(referrer_id),
                    f"🎉 Tabriklaymiz! Yangi odam qo'shildi!\n"
                    f"👤 Kim: {message.from_user.full_name}\n"
                    f"📊 Jami taklif: {referrer_data['invited']} ta"
                )
            except:
                pass

    # Kanal a'zoligini tekshirish
    try:
        member = await bot.get_chat_member(CHANNEL_ID, message.from_user.id)
        is_member = member.status not in ["left", "kicked"]
    except:
        is_member = False

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    user = await get_user(user_id)

    if is_member:
        await message.answer(
            f"👋 Salom, {message.from_user.full_name}!\n\n"
            f"🎯 Sizning referral linkingiz:\n{ref_link}\n\n"
            f"👥 Siz taklif qilganlar: {user['invited']} ta\n\n"
            f"🏆 Mukofotlar:\n"
            f"🥇 1-o'rin → 50 ⭐ Stars\n"
            f"🥈 2-o'rin → 25 ⭐ Stars\n\n"
            f"📢 Linkni do'stlaringizga yuboring!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Mening natijam", callback_data="mystats")],
                [InlineKeyboardButton(text="🏆 Liderlar jadvali", callback_data="leaderboard")]
            ])
        )
    else:
        await message.answer(
            f"👋 Salom! Avval kanalga obuna bo'ling:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Kanalga o'tish", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")],
                [InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="check_sub")]
            ])
        )

# =====================
# OBUNA TEKSHIRISH
# =====================
@dp.callback_query(F.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, callback.from_user.id)
        is_member = member.status not in ["left", "kicked"]
    except:
        is_member = False

    if is_member:
        user_id = str(callback.from_user.id)
        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        user = await get_user(user_id)

        await callback.message.edit_text(
            f"✅ Rahmat! Kanalga obuna bo'ldingiz!\n\n"
            f"🔗 Sizning referral linkingiz:\n{ref_link}\n\n"
            f"👥 Taklif qilganlar: {user.get('invited', 0)} ta",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Mening natijam", callback_data="mystats")],
                [InlineKeyboardButton(text="🏆 Liderlar jadvali", callback_data="leaderboard")]
            ])
        )
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

# =====================
# MENING NATIJAM
# =====================
@dp.callback_query(F.data == "mystats")
async def my_stats(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user = await get_user(user_id)
    invited = user.get("invited", 0) if user else 0

    all_users = await users_col.find().sort("invited", -1).to_list(None)
    rank = next((i + 1 for i, u in enumerate(all_users) if u["_id"] == user_id), "-")

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    await callback.message.edit_text(
        f"📊 SIZNING NATIJANGIZ:\n\n"
        f"👤 Ism: {callback.from_user.full_name}\n"
        f"👥 Taklif qilganlar: {invited} ta\n"
        f"🏅 Reytingdagi o'rni: {rank}-o'rin\n\n"
        f"🔗 Linkingiz:\n{ref_link}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Liderlar jadvali", callback_data="leaderboard")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")]
        ])
    )
    await callback.answer()

# =====================
# LIDERLAR JADVALI
# =====================
@dp.callback_query(F.data == "leaderboard")
async def leaderboard(callback: types.CallbackQuery):
    top_users = await users_col.find().sort("invited", -1).limit(10).to_list(10)

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    text = "🏆 LIDERLAR JADVALI:\n\n"

    for i, u in enumerate(top_users):
        name = u.get("name", "Noma'lum")
        invited = u.get("invited", 0)
        medal = medals[i] if i < len(medals) else f"{i+1}."
        text += f"{medal} {name} — {invited} ta\n"

    if not top_users:
        text += "Hali hech kim taklif qilmagan."

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")]
        ])
    )
    await callback.answer()

# =====================
# ORQAGA
# =====================
@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    await start(callback.message)
    await callback.answer()

# =====================
# ADMIN STATISTIKA
# =====================
@dp.message(Command("stats"))
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Ruxsat yo'q!")

    total = await users_col.count_documents({})
    top_users = await users_col.find().sort("invited", -1).limit(10).to_list(10)

    text = f"📊 ADMIN STATISTIKA:\n\n"
    text += f"👥 Jami foydalanuvchilar: {total} ta\n\n"
    text += "🏆 TOP 10:\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top_users):
        name = u.get("name", "Noma'lum")
        username = u.get("username", "-")
        invited = u.get("invited", 0)
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {name} (@{username}) — {invited} ta\n"

    await message.answer(text)

# =====================
# ADMIN WINNER
# =====================
@dp.message(Command("winner"))
async def announce_winner(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Ruxsat yo'q!")

    top_users = await users_col.find().sort("invited", -1).limit(2).to_list(2)

    if not top_users:
        return await message.answer("Hali ishtirokchi yo'q!")

    text = "🎉 TANLOV YAKUNLANDI!\n\n🏆 G'OLIBLAR:\n\n"

    if len(top_users) >= 1:
        u1 = top_users[0]
        text += f"🥇 1-o'rin: {u1['name']} — {u1['invited']} ta\n💰 50 ⭐ Stars\n\n"
    if len(top_users) >= 2:
        u2 = top_users[1]
        text += f"🥈 2-o'rin: {u2['name']} — {u2['invited']} ta\n💰 25 ⭐ Stars\n\n"

    text += "Barcha ishtirokchilarga rahmat! 🙏"
    await message.answer(text)
    try:
        await bot.send_message(CHANNEL_ID, text)
    except:
        pass

# =====================
# ISHGA TUSHIRISH
# =====================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
