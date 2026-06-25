import os
import django
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') # core o'rniga loyihangiz nomi
django.setup()

from apps.users.models import SickModel
from ..utils import StepBot


from ..utils import StepBot  

async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = update.message.text.title()
    context.user_data['full_name'] = full_name

    await update.message.reply_text(
        'Kontaktni yuboring:',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[
                KeyboardButton(text='📞 Kontaktni yuborish', request_contact=True)
            ]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return StepBot.PHONE_NUMBER


async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contact'] = update.message.contact.phone_number

    inline_keyboard = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Qaytadan kiritish", callback_data="confirm_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    full_name = context.user_data.get('full_name', '')
    contact = context.user_data.get('contact', '')

    await update.message.reply_text(
        text=f"Ma'lumotlaringizni tekshiring:\n\n"
             f"👤 Ism: {full_name}\n"
             f"📞 Telefon: {contact}\n\n"
             f"Ma'lumotlarni tasdiqlaysizmi?",
        reply_markup=reply_markup
    )
    return StepBot.CONFIRM


async def inline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  

    full_name = context.user_data.get('full_name', '')
    phone_number = context.user_data.get('contact', '')
    telegram_id = update.effective_user.id

    if query.data == "confirm_yes":
        sick_exists = await SickModel.objects.filter(phone=phone_number).aexists()

        if not sick_exists:
            await SickModel.objects.acreate(
                telegram_id=telegram_id,
                full_name=full_name,
                phone = phone_number
            )
            await query.edit_message_text(text="🎉 Tizimga muvaffaqiyatli kirdingiz!")
            return ConversationHandler.END
        else:
            await query.edit_message_text(
                text=f"Sizning ({phone_number}) telefon raqamingiz tizimda allaqachon mavjud!"
            )
            return ConversationHandler.END

    elif query.data == "confirm_no":
        await query.edit_message_text(text="Qaytadan ro'yxatdan o'tish.\n\nTo'liq ism-sharifingizni kiriting:")
        return StepBot.FULL_NAME