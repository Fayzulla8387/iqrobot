import os
import asyncio
import sqlite3
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, Message
)
from flask import Flask, request
import json

# Environment o'zgaruvchilari
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1432311261"))
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@personal_blog_fayzulla")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://yourdomain.com")
WEBHOOK_PATH = "/webhook"

# Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# SQLite bazaga ulanish
def get_db():
    conn = sqlite3.connect("giveaway.db")
    conn.row_factory = sqlite3.Row
    return conn


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

# Flask app yaratish
app = Flask(__name__)


# Tugmalarni yaratish
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

    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
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
        print(f"Error in giveaway_handler: {e}")


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
    phone_number = message.contact.phone_number

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (user_id, username, fullname, phone) VALUES (?, ?, ?, ?)",
            (user_id, username, fullname, phone_number)
        )
        conn.commit()
        conn.close()
        await message.answer(
            "✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!",
            reply_markup=types.ReplyKeyboardRemove()
        )
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Siz allaqachon ro'yxatdan o'tgan bo'lishingiz mumkin.")
    except Exception as e:
        await message.answer("❌ Xato yuz berdi.")
        print(f"Error in contact_handler: {e}")


# --- Admin Commands --- #
@dp.message(Command("users"))
async def get_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username, fullname FROM users")
        users = cursor.fetchall()
        conn.close()

        if not users:
            await message.answer("📋 Hozircha foydalanuvchi yo'q.")
            return

        users_list = "\n".join([f"👤 {u['fullname']} (@{u['username']})" for u in users])
        await message.answer(f"📋 Ro'yxatdagi foydalanuvchilar:\n\n{users_list}")
    except Exception as e:
        await message.answer("❌ Xato yuz berdi.")
        print(f"Error in get_users: {e}")


@dp.message(Command("clear_users"))
async def clear_users_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users")
        conn.commit()
        conn.close()
        await message.answer("✅ Barcha foydalanuvchilar bazadan o'chirildi.")
    except Exception as e:
        await message.answer("❌ Xato yuz berdi.")
        print(f"Error in clear_users_handler: {e}")


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
            await message.answer("⚠️ G'oliblarni tanlash uchun kamida 3 ta ishtirokchi kerak!")
            return

        winners = random.sample(users, 3)
        result_text = "🎉 Giveaway g'oliblari:\n\n"

        for i, winner in enumerate(winners, start=1):
            phone_last4 = winner['phone'][-4:] if winner['phone'] else "****"
            result_text += f"{i}. @{winner['username']} - {phone_last4}\n"

        await bot.send_message(ADMIN_ID, result_text)

        for winner in winners:
            try:
                await bot.send_message(
                    winner['user_id'],
                    "🎉 Tabriklaymiz! Siz giveaway g'oliblaridan birisiz!"
                )
            except Exception as e:
                print(f"Could not notify winner {winner['user_id']}: {e}")
    except Exception as e:
        await message.answer("❌ Xato yuz berdi.")
        print(f"Error in winners_handler: {e}")


# --- Webhook Setup Routes --- #
@app.route("/webhook_setup", methods=["GET"])
async def setup_webhook():
    """Webhook o'rnatish uchun endpoint"""
    try:
        webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
        await bot.set_webhook(url=webhook_url)
        return {"status": "success", "message": f"Webhook o'rnatildi: {webhook_url}"}, 200
    except Exception as e:
        print(f"Webhook setup error: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.route("/webhook_delete", methods=["GET"])
async def delete_webhook():
    """Webhookni o'chirish"""
    try:
        await bot.delete_webhook()
        return {"status": "success", "message": "Webhook o'chirildi"}, 200
    except Exception as e:
        print(f"Webhook delete error: {e}")
        return {"status": "error", "message": str(e)}, 500


# --- Webhook Route --- #
@app.route(WEBHOOK_PATH, methods=["POST"])
async def telegram_webhook():
    """Telegram xabarlarni qabul qilish"""
    try:
        data = request.get_json()
        if data:
            update = types.Update.model_validate(data)
            await dp.process_update(update)
        return "OK", 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return "ERROR", 400


# --- Health Check --- #
@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "ok"}, 200


# --- Async Context Manager --- #
async def on_startup():
    """Bot ishga tushganda"""
    try:
        webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
        await bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook o'rnatildi: {webhook_url}")
    except Exception as e:
        print(f"❌ Webhook o'rnatishda xato: {e}")


async def on_shutdown():
    """Bot o'chib ketganda"""
    try:
        await bot.delete_webhook()
        print("✅ Webhook o'chirildi")
    except Exception as e:
        print(f"❌ Webhook o'chirishda xato: {e}")


# --- Main --- #
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))


    # Startup va shutdown
    @app.before_request
    def before_request():
        pass


    print(f"🚀 Bot {PORT} portda webhook rejimida ishga tushdi")
    print(f"📍 Webhook URL: {WEBHOOK_URL}{WEBHOOK_PATH}")

    app.run(host="0.0.0.0", port=PORT, debug=False)