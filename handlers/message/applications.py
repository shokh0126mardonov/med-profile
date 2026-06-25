from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup,ReplyKeyboardRemove
from telegram.ext import ContextTypes,ConversationHandler

from ..utils import StepAplication

async def get_aplication(update:Update,context:ContextTypes.DEFAULT_TYPE):

    application = update.message.text

    context.user_data['application'] = update.message.text

    inline_keyboard = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Qaytadan kiritish", callback_data="confirm_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    await update.message.reply_text(
        text=application,reply_markup=reply_markup
    )

    return StepAplication.CONFIRM

async def confirm_aplication(update:Update,context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    if query.data == 'confirm_yes':
        await query.edit_message_text(
            'Ariza yuborildi!'
        )

        return ConversationHandler.END

    else:
        await query.edit_message_text(
            'Ariza qaytarildi! '
        )

        return StepAplication.APPLICATION
    
    

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    await update.message.reply_text(
        "Bu jarayon to'xtadi! ", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END