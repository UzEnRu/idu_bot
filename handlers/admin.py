from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📬 Xabar yuborish", url="https://t.me/thelxn")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="go_back")]
    ])

    text = (
        "👤 <b>Admin bilan bog‘lanish</b>\n\n"
        "Ismingizni, muammo yoki taklifingizni to‘liq yozib yuboring.\n\n"
        "Admin siz bilan Telegram orqali bog‘lanadi."
    )
    await update.message.reply_html(text, reply_markup=keyboard)
