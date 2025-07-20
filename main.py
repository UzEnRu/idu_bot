from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)
from idu_bot import get_csrf_and_captcha, get_captcha_image, submit_form, extract_results
import requests
import logging
import json
import os

# Logging
logging.basicConfig(level=logging.INFO)

# Telegram bot token
BOT_TOKEN = "7263433130:AAGznHKPVi7-SwfHwK8MkgLbf-O63mQi8nY"

# HTTP session
session = requests.Session()

# States
ASK_PASSPORT, ASK_CAPTCHA = range(2)

# Temporary data for each user
user_data_store = {}

# JSON file path
DATA_FILE = "data.json"

# Foydalanuvchi maʼlumotlarini faylga yozish
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

# /start komandasi — interaktiv tugmalar bilan
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👀 See Results", callback_data="start_check")],
        [InlineKeyboardButton("📞 Admin bilan bog‘lanish", callback_data="contact_admin")],
        [InlineKeyboardButton("ℹ️ Yordam", callback_data="help")],
        [InlineKeyboardButton("🔁 Qaytadan urinish", callback_data="retry")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Salom!\nIltimos, quyidagi tugmalardan birini tanlang:",
        reply_markup=reply_markup
    )

# Callback: See Results — passportni sorashni boshlaydi
async def see_results_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📄 Iltimos, passport raqamingizni yuboring:")
    return ASK_PASSPORT

# Callback: qolgan tugmalar — hozircha faqat javob beradi
async def placeholder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("ℹ️ Ushbu funksiya hali mavjud emas.")

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
        await update.message.reply_text("❌ Captcha yoki token olishda xatolik:\n" + str(e))
        return ConversationHandler.END

    # Saqlash
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

    # Captcha yuborish
    with open(image_path, "rb") as photo_file:
        await update.message.reply_photo(
            photo=photo_file,
            caption="📸 Iltimos, ushbu captcha rasmdagi matnni kiriting:"
        )

    return ASK_CAPTCHA

# Captcha qabul qilish
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

        # JSON ga yozish
        save_user_data(user_data["user_info"])

    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik yuz berdi:\n{e}")

    return ConversationHandler.END

# /cancel komandasi
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END

# Main
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(see_results_callback, pattern="^start_check$"),
        ],
        states={
            ASK_PASSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_passport)],
            ASK_CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_captcha)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Qo‘shimcha tugmalar uchun placeholder handler
    app.add_handler(CallbackQueryHandler(placeholder_callback, pattern="^(contact_admin|help|retry)$"))
    app.add_handler(conv_handler)

    print("✅ Bot ishga tushdi...")
    app.run_polling()
