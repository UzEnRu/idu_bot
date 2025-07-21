from telegram import Update
from telegram.ext import ContextTypes

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "📬 Admin bilan bog‘lanish: <a href='https://t.me/thelxn'>@thelxn</a>"
    )
