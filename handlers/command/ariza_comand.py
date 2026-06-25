from telegram import Update
from telegram.ext import ContextTypes

from ..utils import StepAplication

async def ariza(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ariza yuboring!"
    )

    return StepAplication.APPLICATION