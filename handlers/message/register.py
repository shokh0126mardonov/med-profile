from telegram import Update,ReplyKeyboardMarkup,KeyboardButton
from telegram.ext import ContextTypes


async def get_full_name(update:Update,context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'contact yuboring',
        reply_markup=
        ReplyKeyboardMarkup(
            keyboard=[[
                KeyboardButton(
                text='Contact',request_contact=True
                )
            ]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )