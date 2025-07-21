import logging
import requests
from fastapi import FastAPI, Request
from telegram import Update as TgUpdate
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)
import uvicorn

from config import BOT_TOKEN, WEBHOOK_URL
from handlers.start import start
from handlers.admin import contact_admin
from handlers.help import help_message
from handlers.user_flow import ask_passport, handle_user_input
from handlers.unknown import unknown

# FastAPI
app = FastAPI()

# Telegram
bot_app = Application.builder().token(BOT_TOKEN).build()
session = requests.Session()
bot_app.bot_data["session"] = session

# Handlerlar
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.Regex("🔍 Natijani ko‘rish") | filters.Regex("🔁 Qaytadan urinish"), ask_passport))
bot_app.add_handler(MessageHandler(filters.Regex("📞 Admin bilan bog‘lanish"), contact_admin))
bot_app.add_handler(MessageHandler(filters.Regex("ℹ️ Yordam"), help_message))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
bot_app.add_handler(MessageHandler(filters.ALL, unknown))

@app.on_event("startup")
async def on_startup():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.set_webhook(WEBHOOK_URL)

@app.post("/webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    update = TgUpdate.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
