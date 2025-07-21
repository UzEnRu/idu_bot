from telegram import Update
from telegram.ext import ContextTypes

async def help_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Yordam bo‘limi hozircha mavjud emas. Tez orada qo‘shiladi.")
