from telegram import Update, InputFile, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from idu_bot import get_csrf_and_captcha, get_captcha_image, submit_form, extract_results
import requests
import logging
import json
import os

# Logging
logging.basicConfig(level=logging.INFO)

# Token va URL
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://idu-bot.onrender.com/webhook"

telegram_app = Application.builder().token(BOT_TOKEN).build()
session = requests.Session()

# State-lar
ASK_PASSPORT, ASK_CAPTCHA = range(2)

# Foydalanuvchi ma'lumotlari
user_data_store = {}
DATA_FILE = "data.json"

# Asosiy tugmalar
keyboard = [
    [KeyboardButton("🔍 Natijani ko‘rish")],
    [KeyboardButton("📞 Admin bilan bog‘lanish"), KeyboardButton("ℹ️ Yordam")],
    [KeyboardButton("🔁 Qaytadan urinish")]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def save_user_data(user_info):
    data = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    data.append(user_info)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🎓 <b>Bu — IDU Universitetining Rasmiy Telegram Boti!</b>\n\n"
        "📋 Imtihon natijalarini ko‘rish uchun pastdagi tugmalardan birini tanlang:"
    )
    await update.message.reply_html(welcome_text, reply_markup=reply_markup)
    return ConversationHandler.END

# Tugmalarni boshqarish
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    user_id = user.id

    if text in ("🔍 Natijani ko‘rish", "🔁 Qaytadan urinish"):
        await update.message.reply_text("👤 Iltimos, passport raqamingizni yuboring (masalan: AB1234567):")
        return ASK_PASSPORT

    elif text == "📞 Admin bilan bog‘lanish":
        await update.message.reply_html("📬 Admin bilan bog‘lanish: <a href='https://t.me/thelxn'>@thelxn</a>")
        return ConversationHandler.END

    elif text == "ℹ️ Yordam":
        await update.message.reply_text("ℹ️ Hozircha yordam bo‘limi mavjud emas. Tez orada ishga tushiriladi.")
        return ConversationHandler.END

    else:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.")
        return ConversationHandler.END

# Passport qabul qilish
async def handle_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    passport_id = update.message.text.strip()

    await update.message.reply_text("🔄 Captcha olinmoqda...")

    try:
        csrf_token, captcha_url = get_csrf_and_captcha(session)
        image_path = get_captcha_image(session, captcha_url)
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik yuz berdi:\n{e}")
        return ConversationHandler.END

    user_data_store[user_id] = {
        "passport_id": passport_id,
        "csrf_token": csrf_token,
        "captcha_image_path": image_path,
        "user_info": {
            "user_id": user_id,
            "full_name": user.full_name,
            "username": user.username,
            "passport_id": passport_id
        }
    }

    with open(image_path, "rb") as photo:
        await update.message.reply_photo(photo, caption="📸 Captcha rasmini kiriting:")
    return ASK_CAPTCHA

# Captcha
async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    captcha_text = update.message.text.strip()
    user_data = user_data_store.get(user_id)

    if not user_data:
        await update.message.reply_text("❌ Ma'lumot topilmadi. /start dan boshlang.")
        return ConversationHandler.END

    try:
        html = submit_form(session, user_data["passport_id"], captcha_text, user_data["csrf_token"])
        result = extract_results(html)
        await update.message.reply_text(result)
        save_user_data(user_data["user_info"])
    except Exception as e:
        await update.message.reply_text(f"❌ Natijani olishda xatolik:\n{e}")
    return ConversationHandler.END

# Cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END

# FastAPI webhook
from fastapi import FastAPI, Request
from telegram import Update as TgUpdate
import uvicorn

app = FastAPI()

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = TgUpdate.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

# Handlers
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT, main_menu_handler)],
    states={
        ASK_PASSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_passport)],
        ASK_CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_captcha)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(conv_handler)

# Local dev
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
