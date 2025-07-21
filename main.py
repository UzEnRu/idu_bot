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

# Token va webhook URL
BOT_TOKEN = "7263433130:AAGznHKPVi7-SwfHwK8MkgLbf-O63mQi8nY"
WEBHOOK_URL = "https://idu-bot.onrender.com/webhook"

telegram_app = Application.builder().token(BOT_TOKEN).build()

# Session & States
session = requests.Session()
ASK_PASSPORT, ASK_CAPTCHA = range(2)
user_data_store = {}
DATA_FILE = "data.json"

# Klaviatura
keyboard = [
    [KeyboardButton("🔍 Natijani ko‘rish")],
    [KeyboardButton("📞 Admin bilan bog‘lanish"), KeyboardButton("ℹ️ Yordam")],
    [KeyboardButton("🔁 Qaytadan urinish")]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# User ma’lumotlarini saqlash
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
    welcome_text = (
        "🎓 <b>Bu — IDU Universitetining Rasmiy Telegram Boti!</b>\n\n"
        "📋 Ushbu bot orqali siz imtihon natijalaringizni osonlik bilan bilib olishingiz mumkin.\n\n"
        "🚀 Boshlash uchun pastdagi tugmani bosing:"
    )
    await update.message.reply_html(welcome_text, reply_markup=reply_markup)

# 🔍 tugmasi yoki passport kiritsangiz
async def handle_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text.strip()

    # Tugma bosilgan bo‘lsa, passportni so‘raymiz
    if text in ["🔍 Natijani ko‘rish", "🔁 Qaytadan urinish"]:
        await update.message.reply_text("👤 Iltimos, passport raqamingizni quyidagicha yuboring (AB1234567):")
        return ASK_PASSPORT

    # Aks holda, bu passport raqam deb qabul qilamiz
    passport_id = text
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
        await update.message.reply_text("❌ Maʼlumotlar topilmadi. Iltimos, /start dan boshlang.")
        return ConversationHandler.END

    passport_id = user_data["passport_id"]
    csrf_token = user_data["csrf_token"]

    await update.message.reply_text("📤 Maʼlumot yuborilmoqda...")

    try:
        html = submit_form(session, passport_id, captcha_text, csrf_token)
        result = extract_results(html)
        await update.message.reply_text(result, reply_markup=reply_markup)
        save_user_data(user_data["user_info"])
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik yuz berdi:\n{e}", reply_markup=reply_markup)

    return ConversationHandler.END

# Admin va Yordam tugmalari
async def handle_other_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📞 Admin bilan bog‘lanish":
        await update.message.reply_text("📞 Admin: @admin_username")
    elif text == "ℹ️ Yordam":
        await update.message.reply_text("ℹ️ Yordam uchun: pasport raqamingizni kiriting, captcha ni to‘g‘ri yozing.")
    else:
        await update.message.reply_text("❓ Nomaʼlum buyruq. Pastdagi menyudan foydalaning.")

# Bekor qilish
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=reply_markup)
    return ConversationHandler.END

# 🌐 FastAPI app & webhook
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

# 🧠 Conversation handler
conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.TEXT & filters.Regex("🔍 Natijani ko‘rish"), handle_passport),
        MessageHandler(filters.TEXT & filters.Regex("🔁 Qaytadan urinish"), handle_passport),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_passport),
        CommandHandler("start", start),
    ],
    states={
        ASK_PASSPORT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_passport),
        ],
        ASK_CAPTCHA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_captcha),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

telegram_app.add_handler(conv_handler)

# Qo‘shimcha tugmalarni tutuvchi umumiy handler
telegram_app.add_handler(
    MessageHandler(filters.TEXT & filters.Regex("📞|ℹ️"), handle_other_buttons)
)

# Local test uchun
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
