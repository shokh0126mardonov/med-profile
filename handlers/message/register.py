from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from ..utils import StepBot  

async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = update.message.text
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

    if query.data == "confirm_yes":
        await query.edit_message_text(text="🎉 Tizimga muvaffaqiyatli kirdingiz!")
        return ConversationHandler.END

    elif query.data == "confirm_no":
        # Ma'lumotlarni o'chirib, qaytadan ism so'raymiz
        await query.edit_message_text(text="Qaytadan ro'yxatdan o'tish.\n\nTo'liq ism-sharifingizni  kiriting:")
        return StepBot.FULL_NAME