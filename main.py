from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, Message
from flask import Flask, request
import sqlite3
import random
import asyncio
import os

BOT_TOKEN = "7919646429:AAEnNv63u9mz58Wj5T-pmsFO-oOqdQtL298"
ADMIN_ID = 1432311261
CHANNEL_ID = "@personal_blog_fayzulla"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# SQLite bazaga ulanish
conn = sqlite3.connect("giveaway.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    username TEXT,
    fullname TEXT,
    phone TEXT
)
''')
conn.commit()

# Flask app yaratish
app = Flask(__name__)

# Tugmalar
join_button = InlineKeyboardButton(text="📢 Kanalga a'zo bo‘lish", url="https://t.me/personal_blog_fayzulla")
giveaway_button = KeyboardButton(text="🎁 Giveawayda qatnashish")
main_markup = ReplyKeyboardMarkup(keyboard=[[giveaway_button]], resize_keyboard=True)
join_markup = InlineKeyboardMarkup(inline_keyboard=[[join_button]])
phone_button = KeyboardButton(text="📞 Telefon raqam yuborish", request_contact=True)
phone_markup = ReplyKeyboardMarkup(keyboard=[[phone_button]], resize_keyboard=True)

# --- Aiogram Handlers --- #
@dp.message(Command("start"))
async def start_handler(message: Message):
    main_markup = ReplyKeyboardMarkup(
        keyboard=[
            [giveaway_button],
            [KeyboardButton(text="📢 Kanalga a'zo bo‘lish")]
        ],
        resize_keyboard=True
    )
    await message.answer("Assalomu alaykum! Giveaway ro‘yxatiga qo‘shilish uchun quyidagi tugmalardan birini tanlang:", reply_markup=main_markup)

@dp.message(F.text == "🎁 Giveawayda qatnashish")
async def giveaway_handler(message: Message):
    user_id = message.from_user.id
    member = await bot.get_chat_member(CHANNEL_ID, user_id)

    if member.status in ["member", "administrator", "creator"]:
        await message.answer("📞 Iltimos, telefon raqamingizni yuboring:", reply_markup=phone_markup)
    else:
        await message.answer("📢 Siz hali kanalga a'zo bo‘lmagansiz. Avval kanalga a'zo bo‘ling va qaytadan urinib ko‘ring.", reply_markup=join_markup)

@dp.message(F.text == "📢 Kanalga a'zo bo‘lish")
async def join_channel(message: Message):
    join_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga a'zo bo‘lish", url="https://t.me/personal_blog_fayzulla")]
        ]
    )
    await message.answer("📢 Kanalga qo‘shilish uchun quyidagi tugmani bosing:", reply_markup=join_markup)

@dp.message(F.content_type == types.ContentType.CONTACT)
async def contact_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    fullname = message.from_user.full_name
    phone_number = message.contact.phone_number

    try:
        cursor.execute("INSERT INTO users (user_id, username, fullname, phone) VALUES (?, ?, ?, ?)",
                       (user_id, username, fullname, phone_number))
        conn.commit()
        await message.answer("✅ Muvaffaqiyatli ro‘yxatdan o‘tdingiz!", reply_markup=types.ReplyKeyboardRemove())
    except:
        await message.answer("⚠ Siz allaqachon ro‘yxatdan o‘tgan bo‘lishingiz mumkin.")

# --- Admin Commands --- #
@dp.message(Command("users"))
async def get_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return
    cursor.execute("SELECT username, fullname FROM users")
    users = cursor.fetchall()
    users_list = "\n".join([f"👤 {u[1]} (@{u[0]})" if u[0] else f"👤 {u[1]}" for u in users])
    await message.answer(f"📋 Ro‘yxatdagi foydalanuvchilar:\n\n{users_list}")

@dp.message(Command("clear_users"))
async def clear_users_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return
    cursor.execute("DELETE FROM users")
    conn.commit()
    await message.answer("✅ Barcha foydalanuvchilar bazadan o‘chirildi.")

@dp.message(Command("winners"))
async def winners_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return
    cursor.execute("SELECT user_id, username, fullname, phone FROM users")
    users = cursor.fetchall()
    if len(users) < 3:
        await message.answer("⚠ G‘oliblarni tanlash uchun yetarli ishtirokchi yo‘q!")
        return
    winners = random.sample(users, 3)
    result_text = "🎉 Giveaway g‘oliblari:\n"
    for i, winner in enumerate(winners, start=1):
        phone_last4 = winner[3][-4:]
        result_text += f"{i}. @{winner[1] or winner[2]} - {phone_last4}\n"
    await bot.send_message(ADMIN_ID, result_text)
    for winner in winners:
        try:
            await bot.send_message(winner[0], "🎉 Tabriklaymiz! Siz giveaway g‘oliblaridan birisiz!")
        except:
            pass

# --- Webhook Route --- #
@app.route("/", methods=["POST"])
async def telegram_webhook():
    json_str = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_str)
    await dp.process_update(update)
    return "OK"

# --- Run Flask --- #
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # Flask + asyncio uchun
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT)
