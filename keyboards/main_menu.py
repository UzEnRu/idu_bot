from telegram import KeyboardButton, ReplyKeyboardMarkup

keyboard = [
    [KeyboardButton("🔍 Natijani ko‘rish")],
    [KeyboardButton("📞 Admin bilan bog‘lanish"), KeyboardButton("ℹ️ Yordam")],
    [KeyboardButton("🔁 Qaytadan urinish")]
]

reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
