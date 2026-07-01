from telegram import Bot
from decouple import config


async def send_to_user(telegram_id: int, text_message: str, file_to_send=None):
    """
    Bemorga xabar va shifokorlar yuklagan fayllarni yuboruvchi universal funksiya.
    file_to_send -> Telegram File ID, mahalliy fayl yo'li (path) yoki URL bo'lishi mumkin.
    """
    bot = Bot(token=config("TOKEN"))
    
    # 1. Agar shifokorlar fayl yuklagan bo'lsa, uni hujjat (Document) sifatida yuboramiz
    if file_to_send:
        try:
            await bot.send_document(
                chat_id=telegram_id,
                document=file_to_send,
                caption=text_message,  # Matnni faylning tagiga izoh (caption) qilib joylaymiz
                parse_mode="Markdown"
            )
            return  # Fayl bilan matn ketdi, pastdagi oddiy send_message ishlashi shart emas
        except Exception as file_error:
            print(f"⚠️ Fayl yuborishda xato, faqat matnni yuborishga urinamiz: {file_error}")

    # 2. Agar fayl bo'lmasa yoki fayl yuborish o'xshamasa, faqat matnning o'zini yuboramiz
    await bot.send_message(
        chat_id=telegram_id,
        text=text_message,
        parse_mode="Markdown"
    )