from telegram import Update
from telegram.ext import ContextTypes
from ..utils import StepBot

async def register(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if context.user_data.get('login') is None:
        await update.message.reply_text(
            'Full-name yuboring'
        )

        return StepBot.FULL_NAME
        
    else:
        await update.message.reply_text(
            'Siz login qilingansiz!'
        )