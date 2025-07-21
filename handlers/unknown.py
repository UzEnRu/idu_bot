from telegram import Update
from telegram.ext import ContextTypes
from keyboards.main_menu import reply_markup

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❗ Noto‘g‘ri buyruq. Tugmalardan foydalaning.", reply_markup=reply_markup)
