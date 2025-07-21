from telegram import Update
from telegram.ext import ContextTypes
from keyboards.main_menu import reply_markup
from utils.state import user_state
from core.idu_client import get_csrf_and_captcha, download_captcha, submit_result, parse_result

async def ask_passport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = {"step": "awaiting_passport"}
    await update.message.reply_text("🆔 Iltimos, passport raqamingizni yuboring:")

async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text.strip()
    state = user_state.get(user_id, {}).get("step")

    if state == "awaiting_passport":
        user_state[user_id]["passport"] = msg
        user_state[user_id]["step"] = "awaiting_captcha"
        await update.message.reply_text("🔄 Captcha olinmoqda...")

        try:
            session = context.bot_data["session"]
            csrf, captcha_url = get_csrf_and_captcha(session)
            img_path = download_captcha(session, captcha_url)

            user_state[user_id]["csrf"] = csrf
            with open(img_path, "rb") as img:
                await update.message.reply_photo(img, caption="📸 Captcha kodini kiriting:")
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik:\n{e}")
            user_state.pop(user_id, None)

    elif state == "awaiting_captcha":
        passport = user_state[user_id]["passport"]
        csrf = user_state[user_id]["csrf"]
        captcha = msg
        session = context.bot_data["session"]

        try:
            html = submit_result(session, passport, captcha, csrf)
            result = parse_result(html)
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik:\n{e}")
        user_state.pop(user_id, None)
    else:
        await update.message.reply_text("Iltimos, menyudan foydalaning.", reply_markup=reply_markup)
