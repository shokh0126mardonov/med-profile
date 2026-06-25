import os
import django
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode # HTML formatlash uchun kerak

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.shortcuts import get_object_or_404
from apps.application.models import Applications
from apps.users.models import SickModel

# Asinxron adapter
from asgiref.sync import sync_to_async

from ..utils import StepAplication

# Sinxron get_object_or_404 funksiyasini asinxron ko'rinishga o'tkazamiz
async_get_object_or_404 = sync_to_async(get_object_or_404)


async def get_aplication(update: Update, context: ContextTypes.DEFAULT_TYPE):
    application = update.message.text
    context.user_data['application'] = application

    inline_keyboard = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Qaytadan kiritish", callback_data="confirm_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    await update.message.reply_text(
        text=f"Sizning arizangiz:\n\n{application}\n\nTasdiqlaysizmi?",
        reply_markup=reply_markup
    )

    return StepAplication.CONFIRM


async def confirm_aplication(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Foydalanuvchi ID sini xavfsiz olish
    user_id = query.from_user.id

    if query.data == 'confirm_yes':
        try:
            # 1. Asinxron tarzda SickModel dan user obyektini olamiz
            sick_user = await async_get_object_or_404(SickModel, telegram_id=user_id)
            
            # 2. Arizani asinxron saqlaymiz
            await Applications.objects.acreate(
                sick=sick_user,
                text=context.user_data.get('application', '')
            )
            
            await query.edit_message_text('✅ Ariza muvaffaqiyatli yuborildi!')
            return ConversationHandler.END
            
        except Exception as e:
            # Agar get_object_or_404 topa olmasa Http404 tashlaydi yoki boshqa xatolik bo'lsa
            await query.edit_message_text(f"Xatolik yuz berdi yoki siz bazadan topilmadingiz.")
            return ConversationHandler.END

    elif query.data == 'confirm_no':
        old_application = context.user_data.get('application', '')
        
        # Foydalanuvchiga matnni bitta bosganda nusxa oladigan qilib qaytaramiz
        text_to_edit = (
            "❌ Ariza bekor qilindi.\n\n"
            "Pastdagi matn ustiga **bitta bosing**, u nusxalanadi (copy bo'ladi). "
            "Keyin uni tahrirlab, qaytadan yuboring:\n\n"
            f"<code>{old_application}</code>"
        )
        
        await query.edit_message_text(text=text_to_edit, parse_mode=ParseMode.HTML)
        
        # Foydalanuvchini qaytadan ariza qabul qiladigan state-ga qaytaramiz
        return StepAplication.APPLICATION


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Bu jarayon to'xtadi! ", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END