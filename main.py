import os
import asyncio
import sqlite3
import random
import json
import traceback  # Batafsil xato loglari uchun qo'shildi
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, Message, Update
)
from flask import Flask, request

# --- Environment o'zgaruvchilari --- #
# BOT_TOKEN, ADMIN_ID, CHANNEL_ID ni Render Environment Variables'da o'rnating
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# ADMIN_ID ni int ga o'tkazishda xato bo'lmasligi uchun ishonchli default qo'ydik
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1432311261"))
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@personal_blog_fayzulla")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi. Uni Render atrof-muhit o'zgaruvchilariga qo'shing.")

# --- Bot va Dispatcher --- #
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# --- SQLite bazaga ulanish --- #
def get_db():
    # SQLite3 faylini loyiha papkasida saqlaydi
    conn = sqlite3.connect("giveaway.db")
    conn.row_factory = sqlite3.Row
    return conn


# Baza yaratish
def initialize_db():
    conn = get_db()
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
    conn.close()


initialize_db()

# --- Flask app --- #
app = Flask(__name__)


# --- Tugmalar --- #
def get_main_markup():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Giveawayda qatnashish")],
            [KeyboardButton(text="📢 Kanalga a'zo bo'lish")]
        ],
        resize_keyboard=True
    )


def get_phone_markup():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqam yuborish", request_contact=True)]],
        resize_keyboard=True
    )


join_button_markup = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")
    ]]
)


# --- Aiogram Handlers --- #
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "Assalomu alaykum! 👋\n\nGiveaway ro'yxatiga qo'shilish uchun quyidagi tugmalardan birini tanlang:",
        reply_markup=get_main_markup()
    )


@dp.message(F.text == "🎁 Giveawayda qatnashish")
async def giveaway_handler(message: Message):
    user_id = message.from_user.id

    # Kanalga a'zolikni tekshirish
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            # Agar foydalanuvchi allaqachon ro'yxatdan o'tgan bo'lsa tekshirish
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            user_exists = cursor.fetchone()
            conn.close()

            if user_exists:
                await message.answer(
                    "⚠️ Siz allaqachon ro'yxatdan o'tgan bo'lishingiz mumkin.",
                    reply_markup=types.ReplyKeyboardRemove()
                )
            else:
                await message.answer(
                    "📞 Iltimos, telefon raqamingizni yuboring:",
                    reply_markup=get_phone_markup()
                )
        else:
            await message.answer(
                "📢 Siz hali kanalga a'zo bo'lmagansiz.\nAvval kanalga a'zo bo'ling va qaytadan urinib ko'ring.",
                reply_markup=join_button_markup
            )
    except Exception as e:
        await message.answer("❌ Xato yuz berdi. Qaytadan urinib ko'ring.")
        print(f"Error checking channel membership: {e}")


@dp.message(F.text == "📢 Kanalga a'zo bo'lish")
async def join_channel(message: Message):
    await message.answer(
        "📢 Kanalga qo'shilish uchun quyidagi tugmani bosing:",
        reply_markup=join_button_markup
    )


@dp.message(F.content_type == types.ContentType.CONTACT)
async def contact_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "No username"
    fullname = message.from_user.full_name

    # message.contact.phone_number kontakt yuborilganida mavjud bo'ladi
    phone_number = message.contact.phone_number

    # Kontakt egasi tekshiruvi (faqat o'z raqamini yuborishiga ruxsat berish)
    if message.contact.user_id != user_id:
        await message.answer(
            "⚠️ Faqat o'zingizning telefon raqamingizni yubora olasiz.",
            reply_markup=get_main_markup()  # Asosiy tugmalarni qaytarish
        )
        return

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Ro'yxatdan o'tganligini tekshirish (IntegrityError ga tushmaslik uchun)
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            await message.answer("⚠️ Siz allaqachon ro'yxatdan o'tgansiz.")
        else:
            # Ma'lumotni bazaga yozish
            cursor.execute(
                "INSERT INTO users (user_id, username, fullname, phone) VALUES (?, ?, ?, ?)",
                (user_id, username, fullname, phone_number)
            )
            conn.commit()
            await message.answer(
                "✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!\nSiz giveawayda ishtirokchisiz.",
                reply_markup=get_main_markup()
            )
    except Exception as e:
        await message.answer("❌ Xato yuz berdi. Qaytadan urinib ko'ring.")
        print(f"Error saving contact: {e}")
    finally:
        conn.close()


# --- Admin Commands --- #
@dp.message(Command("users"))
async def get_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username, fullname, phone FROM users")
        users = cursor.fetchall()
        conn.close()

        if not users:
            await message.answer("📋 Hozircha foydalanuvchi yo'q.")
            return

        user_count = len(users)
        users_list = "\n".join([f"👤 {u['fullname']} (@{u['username']}) - {u['phone']}" for u in users])
        await message.answer(
            f"📋 **Jami ishtirokchilar: {user_count}**\n\nRo'yxatdagi foydalanuvchilar:\n\n{users_list}")
    except Exception as e:
        await message.answer("❌ Foydalanuvchilarni olishda xato.")
        print(f"Error fetching users: {e}")


@dp.message(Command("clear_users"))
async def clear_users_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return

    await message.answer("⚠️ Barcha foydalanuvchilarni o'chirishga ishonchingiz komilmi? Yuboring: `/confirm_clear`")


@dp.message(Command("confirm_clear"))
async def confirm_clear_users_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users")
        count = cursor.rowcount
        conn.commit()
        conn.close()
        await message.answer(f"✅ **{count}** ta foydalanuvchi bazadan o'chirildi.")
    except Exception as e:
        await message.answer("❌ O'chirishda xato yuz berdi.")
        print(f"Error clearing users: {e}")


@dp.message(Command("winners"))
async def winners_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, fullname, phone FROM users")
        users = cursor.fetchall()
        conn.close()

        if len(users) < 3:
            await message.answer(
                f"⚠️ G'oliblarni tanlash uchun kamida 3 ta ishtirokchi kerak! Hozirda: {len(users)} ta.")
            return

        winners = random.sample(users, 3)
        result_text = "🎉 **Giveaway g'oliblari**:\n\n"

        for i, winner in enumerate(winners, start=1):
            phone_last4 = winner['phone'][-4:] if winner['phone'] and len(winner['phone']) >= 4 else "****"
            result_text += f"**{i}.** {winner['fullname']} (@{winner['username']}) - *...{phone_last4}*\n"

        # G'oliblar ro'yxatini admin va kanalga yuborish (kanalga yuborish uchun CHANNEL_ID ni tekshiring)
        await bot.send_message(ADMIN_ID, result_text, parse_mode="Markdown")

        for winner in winners:
            try:
                # G'olibga xabar yuborish
                await bot.send_message(
                    winner['user_id'],
                    "🎉 **TABRIKLAYMIZ!** Siz giveaway g'oliblaridan birisiz!\nG'oliblikni tasdiqlash uchun admin bilan bog'laning."
                )
            except Exception as e:
                print(f"Could not send message to winner {winner['user_id']}: {e}")

        await message.answer("✅ G'oliblar muvaffaqiyatli tanlandi va ularga xabar yuborildi.")

    except Exception as e:
        await message.answer("❌ G'oliblarni tanlashda xato yuz berdi.")
        print(f"Error selecting winners: {e}")
        traceback.print_exc()


# --- Webhook yordamchi funksiyasi (asinxronlik uchun) --- #
async def process_update_async(update_data):
    try:
        update = Update(**update_data)
        await dp.process_update(update)
    except Exception as e:
        # Bu erda aiogramning update-ni qayta ishlashdagi xatolar yoziladi
        print(f"AIOGRAM PROCESS ERROR: {e}")
        traceback.print_exc()


# --- Webhook endpoint --- #
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)  # JSON ma'lumotini olish

        # Asinxron vazifani ishga tushirish (bloklanmaslik uchun)
        # asyncio.create_task() ishlatilishi uchun nest_asyncio zarur
        asyncio.create_task(process_update_async(data))

        return "OK", 200
    except json.JSONDecodeError:
        # JSON o'qishdagi xato. Telegram so'rovni noto'g'ri yuborgan bo'lishi mumkin.
        print(f"WEBHOOK ERROR: Invalid JSON received. Data: {request.data[:100]}...")
        return "Invalid JSON", 400
    except Exception as e:
        # Boshqa kutilmagan xatolar
        print(f"WEBHOOK UNEXPECTED ERROR: {e}")
        traceback.print_exc()
        return "Internal Error", 500


# --- Run Flask server --- #
if __name__ == "__main__":
    import nest_asyncio

    nest_asyncio.apply()  # Asyncio va Flask ni birga ishlatish uchun

    # Render tomonidan avtomatik o'rnatilgan PORT ni ishlatish
    # Agar PORT o'rnatilmagan bo'lsa, Render loglarda ko'rsatilgan 10000 ni ishlatamiz
    PORT = int(os.environ.get("PORT", 10000))

    print(f"Starting Flask server on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)