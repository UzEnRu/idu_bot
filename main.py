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

# Bot token va webhook URL
BOT_TOKEN = "7263433130:AAGznHKPVi7-SwfHwK8MkgLbf-O63mQi8nY"
WEBHOOK_URL = "https://idu-bot.onrender.com/webhook"

# Telegram Application
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Session va conversation holatlari
session = requests.Session()
ASK_PASSPORT, ASK_CAPTCHA = range(2)
user_data_store = {}
DATA_FILE = "data.json"

# User ma'lumotlarini saqlash
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

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🔍 Natijani ko‘rish")],
        [KeyboardButton("📞 Admin bilan bog‘lanish"), KeyboardButton("ℹ️ Yordam")],
        [KeyboardButton("🔁 Qaytadan urinish")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    welcome_text = (
        "🎓 <b>Bu — IDU Universitetining Rasmiy Telegram Boti!</b>\n\n"
        "📋 Ushbu bot orqali siz imtihon natijalaringizni osonlik bilan bilib olishingiz mumkin.\n\n"
        "🚀 Boshlash uchun pastdagi tugmani bosing:"
    )
    await update.message.reply_html(welcome_text, reply_markup=reply_markup)
    return ASK_PASSPORT

# Pasport so‘rash handler
async def handle_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    passport_id = update.message.text.strip()

    if passport_id == "🔍 Natijani ko‘rish":
        await update.message.reply_text("👤 Iltimos, passport raqamingizni quyidagicha yuboring (AB1234567):")
        return ASK_PASSPORT

    await update.message.reply_text("🔄 Captcha olinmoqda...")

    try:
        csrf_token, captcha_url = get_csrf_and_captcha(session)
        image_path = get_captcha_image(session, captcha_url)
    except Exception as e:
        await update.message.reply_text("❌ Captcha yoki token olishda xatolik:\n" + str(e))
        return ConversationHandler.END

    user_data_store[user_id] = {
        "passport_id": passport_id,
        "csrf_token": csrf_token,
        "captcha_image_path": image_path,
        "user_info": {
            "user_id": user_id,
            "full_name": user.full_name,
            "username": user.username,
            "passport_id": passport_id,
            "phone_number": update.message.contact.phone_number if update.message.contact else None
        }
    }

    with open(image_path, "rb") as photo_file:
        await update.message.reply_photo(
            photo=photo_file,
            caption="📸 Iltimos, ushbu captcha rasmdagi matnni kiriting:"
        )
    return ASK_CAPTCHA

# Captcha javobini olish handler
async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    captcha_text = update.message.text.strip()
    user_data = user_data_store.get(user_id)

    if not user_data:
        await update.message.reply_text("❌ Maʼlumotlar topilmadi. /start dan boshlang.")
        return ConversationHandler.END

    passport_id = user_data["passport_id"]
    csrf_token = user_data["csrf_token"]

    await update.message.reply_text("📤 Maʼlumot yuborilmoqda...")

    try:
        html = submit_form(session, passport_id, captcha_text, csrf_token)
        result = extract_results(html)
        await update.message.reply_text(result)
        save_user_data(user_data["user_info"])
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik yuz berdi:\n{e}")
    return ConversationHandler.END

# Bekor qilish
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END

# 🌐 FastAPI app & webhook
from fastapi import FastAPI, Request
from telegram import Update as TgUpdate
import uvicorn

app = FastAPI()

# Startup event: initialize, start, and set webhook
@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

# Webhook endpoint
@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = TgUpdate.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"status": "ok"}

# Bot handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_PASSPORT: [
            MessageHandler(filters.TEXT & filters.Regex("🔍 Natijani ko‘rish"), handle_passport),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_passport)
        ],
        ASK_CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_captcha)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

telegram_app.add_handler(conv_handler)

# Local dev uchun
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
