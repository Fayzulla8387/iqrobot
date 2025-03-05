from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
import asyncio
import sqlite3
import random

# Token
BOT_TOKEN = "7919646429:AAFnVGXZqbtDOtaX5sSoOjC4MHNMLMIDhXQ"

# Admin ID
ADMIN_ID = 1432311261  # O'zingizning Telegram ID'ingizni yozing

# Bot va dispatcher yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# SQLite bazaga ulanish
conn = sqlite3.connect("giveaway.db")
cursor = conn.cursor()

# Foydalanuvchilar jadvalini yaratish
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

# Telefon raqamini so‘rash tugmasi
phone_button = KeyboardButton(text="📞 Telefon raqam yuborish", request_contact=True)
phone_markup = ReplyKeyboardMarkup(keyboard=[[phone_button]], resize_keyboard=True)

# Start komandasi
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Assalomu alaykum! Giveaway ro‘yxatiga qo‘shilish uchun telefon raqamingizni yuboring.", reply_markup=phone_markup)

# Telefon raqamini qabul qilish (aiogram 3.x uchun to‘g‘ri usul)
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
        await message.answer("✅ Muvaffaqiyatli ro‘yxatdan o‘tdingiz! G‘oliblar tez orada aniqlanadi.", reply_markup=types.ReplyKeyboardRemove())
    except:
        await message.answer("⚠ Siz allaqachon ro‘yxatdan o‘tgan bo‘lishingiz mumkin.")


@dp.message(Command("users"))
async def get_users(message: types.Message):
    ADMIN_ID = 1432311261  # O'zingizning Telegram ID'ingizni kiriting

    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return

    cursor.execute("SELECT username, fullname FROM users")
    users = cursor.fetchall()

    if not users:
        await message.answer("📭 Hozircha hech kim /start bosmadi.")
        return

    users_list = "\n".join([f"👤 {u[1]} (@{u[0]})" if u[0] else f"👤 {u[1]}" for u in users])
    await message.answer(f"📋 Ro‘yxatdagi foydalanuvchilar:\n\n{users_list}")



@dp.message(Command("clear_users"))
async def clear_users_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz bu buyruqni ishlata olmaysiz!")
        return

    conn = sqlite3.connect("giveaway.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()

    await message.answer("✅ Barcha foydalanuvchilar bazadan o‘chirildi.")
# Giveaway g‘oliblarini aniqlash (faqat admin ishlatishi mumkin)
@dp.message(Command("winners"))
async def winners_handler(message: Message):
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
        phone_last4 = winner[3][-4:]  # Telefon raqamining oxirgi 4 raqami
        result_text += f"{i}. @{winner[1] or winner[2]} - {phone_last4}\n"

    # Faqat adminga yuborish
    await bot.send_message(ADMIN_ID, result_text)

    # G‘oliblarga xabar yuborish
    for winner in winners:
        try:
            await bot.send_message(winner[0], "🎉 Tabriklaymiz! Siz giveaway g‘oliblaridan birisiz!")
        except:
            pass  # Agar foydalanuvchi botni bloklagan bo‘lsa, xatolik bo‘ladi

# Asosiy asyncio tsikli
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
