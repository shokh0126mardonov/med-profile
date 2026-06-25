from telegram import Update
from telegram.ext import ContextTypes

from ..utils import StepAplication

async def ariza(update:Update,context:ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('login'):

        await update.message.reply_text(
            "Ariza yuboring!"
        )

        return StepAplication.APPLICATION

    else:
        login_required_text = (
            "🔒 **Xizmatlardan foydalanish uchun tizimga kirish talab etiladi.**\n\n"
            "Klinika shifokorlari bilan bogʻlanish va arizangizni koʻrib chiqishimiz uchun, iltimos, avval roʻyxatdan oʻting:\n\n"
            "👉 /login buyrugʻini bosing."
        )
        await update.message.reply_text(
            text=login_required_text,
            parse_mode="Markdown"
        )