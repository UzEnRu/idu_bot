import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
from fastapi import FastAPI, Request
from telegram import Update as TgUpdate
import uvicorn

from idu_bot import get_csrf_and_captcha, download_captcha, submit_result, parse_result

# Logger va .env yuklash
logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = FastAPI()
bot_app = Application.builder().token(BOT_TOKEN).build()
session = requests.Session()
user_state = {}

# Tugmalar
keyboard = [
    [KeyboardButton("🔍 Natijani ko‘rish")],
    [KeyboardButton("📞 Admin bilan bog‘lanish"), KeyboardButton("ℹ️ Yordam")],
    [KeyboardButton("🔁 Qaytadan urinish")]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Boshlanish komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎓 <b>IDU natijalar botiga xush kelibsiz!</b>\n"
        "📋 Iltimos, quyidagi menyudan foydalaning:"
    )
    await update.message.reply_html(text, reply_markup=reply_markup)

# Admin
async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "📬 Admin bilan bog‘lanish: <a href='https://t.me/thelxn'>@thelxn</a>"
    )

# Yordam
async def help_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Yordam bo‘limi hozircha mavjud emas. Tez orada qo‘shiladi.")

# Passportni so‘rash
async def ask_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = {"step": "awaiting_passport"}
    await update.message.reply_text("🆔 Iltimos, passport raqamingizni yuboring:")

# Foydalanuvchi javobini boshqarish
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text.strip()

    state = user_state.get(user_id, {}).get("step")

    if state == "awaiting_passport":
        user_state[user_id]["passport"] = msg
        user_state[user_id]["step"] = "awaiting_captcha"

        await update.message.reply_text("🔄 Captcha olinmoqda...")

        try:
            csrf, captcha_url = get_csrf_and_captcha(session)
            img_path = download_captcha(session, captcha_url)

            user_state[user_id]["csrf"] = csrf
            with open(img_path, "rb") as img:
                await update.message.reply_photo(img, caption="📸 Captcha kodini kiriting:")
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik:\n{e}")
            user_state.pop(user_id, None)

    elif state == "awaiting_captcha":
        passport = user_state[user_id]["passport"]
        csrf = user_state[user_id]["csrf"]
        captcha = msg

        try:
            html = submit_result(session, passport, captcha, csrf)
            result = parse_result(html)
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik:\n{e}")

        user_state.pop(user_id, None)
    else:
        await update.message.reply_text("Iltimos, menyudan foydalaning.", reply_markup=reply_markup)

# Noto‘g‘ri buyruqlar
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❗ Noto‘g‘ri buyruq. Tugmalardan foydalaning.", reply_markup=reply_markup)

# Telegram Handlerlar
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.Regex("🔍 Natijani ko‘rish") | filters.Regex("🔁 Qaytadan urinish"), ask_passport))
bot_app.add_handler(MessageHandler(filters.Regex("📞 Admin bilan bog‘lanish"), contact_admin))
bot_app.add_handler(MessageHandler(filters.Regex("ℹ️ Yordam"), help_message))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
bot_app.add_handler(MessageHandler(filters.ALL, unknown))

# FastAPI Webhook
@app.on_event("startup")
async def on_startup():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.set_webhook(WEBHOOK_URL)

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    update = TgUpdate.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}

# Lokal test uchun
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
