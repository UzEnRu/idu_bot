from telegram import Update
from telegram.ext import ContextTypes
from keyboards.main_menu import reply_markup

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎓 <b>IDU natijalar botiga xush kelibsiz!</b>\n"
        "📋 Iltimos, quyidagi menyudan foydalaning:"
    )
    await update.message.reply_html(text, reply_markup=reply_markup)
