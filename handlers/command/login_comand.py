import os
import django
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 
django.setup()

from apps.users.models import SickModel
from ..utils import Steplogin


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Foydalanuvchiga nima uchun kontakt kerakligini tushuntiramiz va chiroyli formatlaymiz
    welcome_text = (
        "👋 **Tizimga kirish bo'limiga xush kelibsiz!**\n\n"
        "Iltimos, pastdagi **«📞 Kontaktni yuborish»** tugmasini bosish orqali "
        "telefon raqamingizni yuboring, biz sizni bazadan tekshiramiz."
    )

    await update.message.reply_text(
        text=welcome_text,
        parse_mode="Markdown", # Qalin matnlar ishlashi uchun
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[
                KeyboardButton(text='📞 Kontaktni yuborish', request_contact=True)
            ]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )

    return Steplogin.CONTACT


async def try_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact.phone_number

    sick_exists = await SickModel.objects.filter(phone=contact).aexists()

    if sick_exists:
        context.user_data['login'] = True

        # Muvaffaqiyatli login matni
        success_text = (
            "✅ **Muvaffaqiyatli kirildi!**\n\n"
            "Siz tizimdan muvaffaqiyatli o'tdingiz. Bot xizmatlaridan to'liq foydalanishingiz mumkin."
        )
        await update.message.reply_text(
            text=success_text,
            parse_mode="Markdown"
        )

    else:
        # Topilmagandagi xabar va komandani bosiladigan (giperhavola) qilish
        error_text = (
            "⚠️ **Kechirasiz, siz tizimdan topilmadingiz!**\n\n"
            "Ushbu telefon raqami bazamizda mavjud emas. Iltimos, qaytadan ro'yxatdan o'tish uchun "
            "/register buyrug'ini bosing yoki yozing."
        )
        await update.message.reply_text(
            text=error_text,
            parse_mode="Markdown"
        )