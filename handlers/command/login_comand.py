import os
import django
from telegram import Update,ReplyKeyboardMarkup,KeyboardButton
from telegram.ext import ContextTypes

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # core o'rniga loyihangiz nomi
django.setup()

from apps.users.models import SickModel
from ..utils import Steplogin


async def login(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        'Contact yuboring!',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[
                KeyboardButton(text='📞 Kontaktni yuborish', request_contact=True)
            ]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )

    return Steplogin.CONTACT


async def try_user(update:Update,context:ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact.phone_number

    sick_exists = await SickModel.objects.filter(phone=contact).aexists()

    if sick_exists:
        context.user_data['login'] = True

        await update.message.reply_text(
            text="Siz login qilindingiz!"
        )

    else:
        await update.message.reply_text(
            text='Siz tizimdan topilmadingiz /register orqali royxatdan oting'
        )