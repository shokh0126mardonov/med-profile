import os
import django

from telegram import Update
from telegram.ext import ContextTypes

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 
django.setup()

from apps.users.models import SickModel
from ..utils import StepAplication

async def ariza(update:Update,context:ContextTypes.DEFAULT_TYPE):


    sick_exists = await SickModel.objects.filter(telegram_id=update.effective_user.id).aexists()

    if sick_exists:

        await update.message.reply_text(
            "Ariza yuboring!"
        )

        return StepAplication.APPLICATION

    else:
        await update.message.reply_text(
           "siz /register buyrug'i orqali ro'yxatdan o'ting! "
       )