import os
import django

from telegram import Update
from telegram.ext import ContextTypes
from ..utils import StepBot

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 
django.setup()

from apps.users.models import SickModel

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    sick_exists = await SickModel.objects.filter(telegram_id=user_id).aexists()

    if not sick_exists:
        await update.message.reply_text(
            "📋 **Roʻyxatdan oʻtish jarayoni boshlandi.**\n\n"
            "Iltimos, ism va familiyangizni kiriting (Masalan: Ali Valiyev):",
            parse_mode="Markdown"
        )
        return StepBot.FULL_NAME
        
    else:
        await update.message.reply_text(
            "✅ **Siz allaqachon roʻyxatdan oʻtgansiz!**\n\n"
            "Shifokorlarimizga ariza yuborish uchun 👉 /ariza buyrugʻini bosing."
        )
        return None