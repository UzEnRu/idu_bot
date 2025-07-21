import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)
from fastapi import FastAPI, Request
from telegram import Update as TgUpdate
import uvicorn

from idu_bot import get_csrf_and_captcha, get_captcha_image, submit_form, extract_results

# Yuklamalar
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://idu-bot.onrender.com/webhook"

telegram_app = Application.builder().token(BOT_TOKEN).build()
session = requests.Session()
user_data = {}  # Har bir user uchun vaqtincha saqlanadi

# Tugmalar
keyboard = [
    [KeyboardButton("🔍 Natijani ko‘rish")],
    [KeyboardButton("📞 Admin bilan bog‘lanish"), KeyboardButton("ℹ️ Yordam")],
    [KeyboardButton("🔁 Qaytadan urinish")]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Boshlanish
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎓 <b>Bu — IDU Universitetining Rasmiy Telegram Boti!</b>\n\n"
        "📋 Imtihon natijalarini ko‘rish uchun pastdagi tugmalardan foydalaning:"
    )
    await update.message.reply_html(text, reply_markup=reply_markup)

# Natija ko‘rish tugmasi
async def ask_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {}
    await update.message.reply_text("👤 Iltimos, passport raqamingizni yuboring:")
    
# Passport kelganda
async def handle_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    passport_id = update.message.text.strip()
    user_data[user_id]["passport_id"] = passport_id

    await update.message.reply_text("🔄 Captcha olinmoqda...")

    try:
        csrf_token, captcha_url = get_csrf_and_captcha(session)
        image_path = get_captcha_image(session, captcha_url)

        user_data[user_id]["csrf_token"] = csrf_token
        user_data[user_id]["captcha_image_path"] = image_path

        with open(image_path, "rb") as photo:
            await update.message.reply_photo(photo, caption="📸 Captcha kodini kiriting:")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik:\n{e}")
        user_data.pop(user_id, None)

# Captcha javobi kelganda
async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    captcha_text = update.message.text.strip()

    if user_id not in user_data or "passport_id" not in user_data[user_id]:
        await update.message.reply_text("❗ Avval passport raqamni kiriting.")
        return

    passport_id = user_data[user_id]["passport_id"]
    csrf_token = user_data[user_id]["csrf_token"]

    try:
        html = submit_form(session, passport_id, captcha_text, csrf_token)
        result = extract_results(html)
        await update.message.reply_text(result)
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik:\n{e}")

    user_data.pop(user_id, None)

# Yordam
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Yordam bo‘limi hozircha mavjud emas.")

# Admin
async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("📬 Admin bilan bog‘lanish: <a href='https://t.me/thelxn'>@thelxn</a>")

# Noaniq matn
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Iltimos, tugmalardan birini tanlang.", reply_markup=reply_markup)

# Webhook uchun FastAPI
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

@app.post("/webhook")
async def handle_webhook(req: Request):
    data = await req.json()
    update = TgUpdate.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

# Telegram handlerlar
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.Regex("🔍 Natijani ko‘rish") | filters.Regex("🔁 Qaytadan urinish"), ask_passport))
telegram_app.add_handler(MessageHandler(filters.Regex("📞 Admin bilan bog‘lanish"), admin_handler))
telegram_app.add_handler(MessageHandler(filters.Regex("ℹ️ Yordam"), help_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_passport))  # Passport yoki Captcha
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_captcha))   # Captcha oxirida

# Local development
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
