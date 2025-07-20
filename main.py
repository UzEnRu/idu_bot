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
import asyncio
from aiohttp import web

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = "7263433130:AAGznHKPVi7-SwfHwK8MkgLbf-O63mQi8nY"
WEBHOOK_URL = "https://YOUR-RENDER-URL.onrender.com/webhook"

session = requests.Session()
ASK_PASSPORT, ASK_CAPTCHA = range(2)
user_data_store = {}
DATA_FILE = "data.json"

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

async def handle_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    passport_id = update.message.text.strip()

    if passport_id == "🔍 Natijani ko‘rish":
        await update.message.reply_text("\ud83d\udc64 Iltimos, passport raqamingizni quyidagicha yuboring(AB1234567):")
        return ASK_PASSPORT

    await update.message.reply_text("\ud83d\udd04 Captcha olinmoqda...")

    try:
        csrf_token, captcha_url = get_csrf_and_captcha(session)
        image_path = get_captcha_image(session, captcha_url)
    except Exception as e:
        await update.message.reply_text("\u274c Captcha yoki token olishda xatolik:\n" + str(e))
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

async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    captcha_text = update.message.text.strip()

    user_data = user_data_store.get(user_id)
    if not user_data:
        await update.message.reply_text("\u274c Maʼlumotlar topilmadi. /start dan boshlang.")
        return ConversationHandler.END

    passport_id = user_data["passport_id"]
    csrf_token = user_data["csrf_token"]

    await update.message.reply_text("\ud83d\udce4 Maʼlumot yuborilmoqda...")

    try:
        html = submit_form(session, passport_id, captcha_text, csrf_token)
        result = extract_results(html)
        await update.message.reply_text(result)
        save_user_data(user_data["user_info"])
    except Exception as e:
        await update.message.reply_text(f"\u274c Xatolik yuz berdi:\n{e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\u274c Bekor qilindi.")
    return ConversationHandler.END

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

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

    app.add_handler(conv_handler)
    await app.initialize()
    await app.bot.set_webhook(WEBHOOK_URL)
    await app.start()

    async def webhook_handler(request):
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response()

    runner = web.AppRunner(web.Application().add_routes([web.post("/webhook", webhook_handler)]))
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()
    print("✅ Webhook ishga tushdi...")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())