from telegram import Update
from telegram.ext import ContextTypes


async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if context.user_data.get('login'):
        await update.message.reply_text(
            "Salom"
        )
    else:
        await update.message.reply_text(
            'login qiling /login tugmasini bosing'
        )