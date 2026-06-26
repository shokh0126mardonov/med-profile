import asyncio
from telegram import Bot
from decouple import config

async def send_to_user(telegram_id: int, text_message: str):
    # Bot obyektini token orqali yaratamiz
    bot = Bot(token=config("TOKEN"))
    
    # Xabarni await orqali yuboramiz
    await bot.send_message(
        chat_id=telegram_id,
        text=text_message,
        parse_mode="Markdown" # formatlash uchun (ixtiyoriy)
    )