import os
import django
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode 
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.application.models import Applications
from apps.users.models import SickModel
from ..utils import StepAplication

# 1. MATNNI QABUL QILISH
async def get_aplication(update: Update, context: ContextTypes.DEFAULT_TYPE):
    application = update.message.text
    context.user_data['application'] = application

    inline_keyboard = [
        [InlineKeyboardButton(text="⏭️ Faylsiz davom etish", callback_data="skip_file")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    await update.message.reply_text(
        text=(
            "✍️ Ariza matni qabul qilindi.\n\n"
            "📎 Endi arizangizga tegishli **fayl, rasm yoki hujjat** yuboring.\n"
            "Agar fayl yuborishni istamasangiz, pastdagi tugmani bosing:"
        ),
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return StepAplication.FILE


TOKEN = config('TOKEN')

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    file_id = None
    file_url = None
    
    if query and query.data == "skip_file":
        await query.answer()
        context.user_data['file_id'] = None
        context.user_data['user_file_url'] = None
    
    else:
        message = update.message
        
        if message.document:
            file_id = message.document.file_id
        elif message.photo:
            file_id = message.photo[-1].file_id 
            
        context.user_data['file_id'] = file_id

        if file_id:
            try:
                url = f"https://api.telegram.org/bot{TOKEN}/getFile"
                response = requests.get(url, params={'file_id': file_id}, timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        file_path = result['result']['file_path']
                        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            except Exception as e:
                print(f"💥 Bot ichida fayl yo'lini aniqlashda xatolik: {e}")
        
        context.user_data['user_file_url'] = file_url

    inline_keyboard = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Qaytadan kiritish", callback_data="confirm_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    # 4-QADAM: Xabar matnini tayyorlash
    app_text = context.user_data.get('application', '')
    has_file = "📎 Biriktirilgan (Yuklandi)" if context.user_data.get('user_file_url') else "❌ Yo'q"

    msg_text = (
        "📝 **Ariza ma'lumotlari:**\n\n"
        f"**Matn:** {app_text}\n"
        f"**Fayl:** {has_file}\n\n"
        "Ushbu arizani tasdiqlaysizmi?"
    )
    
    # 5-QADAM: Foydalanuvchiga xabarni chiqarish (Tugma bosilganiga yoki fayl kelganiga qarab)
    if query:
        await query.edit_message_text(
            text=msg_text, 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text=msg_text, 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.MARKDOWN
        )

    # Keyingi qadamga (CONFIRM) o'tkazamiz
    return StepAplication.CONFIRM



async def confirm_aplication(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'confirm_yes':
        try:
            # 1. Bemor foydalanuvchini bazadan asinxron olamiz
            sick_user = await SickModel.objects.aget(telegram_id=user_id)
            
            # 2. Arizani asinxron yaratamiz
            new_application = await Applications.objects.acreate(
                sick=sick_user,
                text=context.user_data.get('application', ''),
                user_file_url=context.user_data.get('user_file_url'),
                # status='NEW' # 🚀 To'g'ridan-to'g'ri ASSIGNED qilamiz, chunki hozir shifokorlar birikadi!
            )
            
            # =====================================================================
            # 🔥 ASINXRON BIRIKTIRUV (BOT ICHIDAGI DOIMIY ISHLOVCHI FOR SIKLI)
            # =====================================================================
            from django.contrib.auth import get_user_model
            from apps.application.models import ApplicationAssignment
            User = get_user_model()

            
            async for doctor in User.objects.filter(role='DOCTOR'):
                # Har bir shifokor uchun asinxron biriktiruv yaratamiz
                await ApplicationAssignment.objects.acreate(
                    application=new_application,
                    doctor=doctor,
                    status='UNSEEN'
                )
            # =====================================================================
            
            await query.edit_message_text('✅ Arizangiz muvaffaqiyatli shifokorlarga yuborildi!')
            context.user_data.clear() 
            return ConversationHandler.END
            
        except Exception as e:
            print(f"💥 BAZAGA YOZISHDA XATO: {e}")
            await query.edit_message_text("❌ Tizimda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
            return ConversationHandler.END

    elif query.data == 'confirm_no':
        context.user_data.pop('application', None)
        context.user_data.pop('file_id', None)
        
        await query.edit_message_text(
            text="❌ **Ariza bekor qilindi.**\n\nIltimos, shifokorlarimiz uchun yangi ariza matnini qaytadan yozib yuboring:",
            parse_mode=ParseMode.MARKDOWN
        )
        return StepAplication.APPLICATION
    
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Bu jarayon to'xtadi! ", reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END