import os
import django
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode 

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


# 2. FAYLNI QABUL QILISH
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query and query.data == "skip_file":
        await query.answer()
        context.user_data['file_id'] = None
    else:
        message = update.message
        file_id = None
        if message.document:
            file_id = message.document.file_id
        elif message.photo:
            file_id = message.photo[-1].file_id
            
        context.user_data['file_id'] = file_id

    inline_keyboard = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Qaytadan kiritish", callback_data="confirm_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    app_text = context.user_data.get('application', '')
    has_file = "📎 Biriktirilgan" if context.user_data.get('file_id') else "❌ Yo'q"

    msg_text = f"📝 **Ariza ma'lumotlari:**\n\n**Matn:** {app_text}\n**Fayl:** {has_file}\n\nUshbu arizani tasdiqlaysizmi?"
    
    if query:
        await query.edit_message_text(text=msg_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text=msg_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    return StepAplication.CONFIRM


# 3. TASDIQLASH (HA BO'LGANDA)
async def confirm_aplication(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'confirm_yes':
        try:
            # Sening mantiqing bo'yicha foydalanuvchi bazada aniq bor, shuning uchun aget() qilamiz
            sick_user = await SickModel.objects.aget(telegram_id=user_id)
            
            # Xavfsiz yaratish: ManyToMany (doctors) bilan muammo bo'lmasligi uchun faqat kerakli maydonlarni beramiz
            await Applications.objects.acreate(
                sick=sick_user,
                text=context.user_data.get('application', ''),
                file_id=context.user_data.get('file_id', None),
                status='NEW' # Default holatda yangi ariza
            )
            
            await query.edit_message_text('✅ Arizangiz muvaffaqiyatli shifokorlarga yuborildi!')
            context.user_data.clear() 
            return ConversationHandler.END
            
        except Exception as e:
            # Agar kodingda boshqa xato bo'lsa terminal srazi senga aytib beradi:
            print(f"💥 BAZAGA YOZISHDA XATO: {e}")
            await query.edit_message_text("❌ Tizimda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
            return ConversationHandler.END

    # 💡 SEN AYTGAN JOYLAR: "YO'Q" (CONFIRM_NO) BO'LGANDA QAYTADAN ARIZA SO'RASH
    elif query.data == 'confirm_no':
        context.user_data.pop('application', None) # Eski matnni o'chirib tashlaymiz
        context.user_data.pop('file_id', None)
        
        await query.edit_message_text(
            text="❌ **Ariza bekor qilindi.**\n\nIltimos, shifokorlarimiz uchun yangi ariza matnini qaytadan yozib yuboring:",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Foydalanuvchini yana ariza matnini kutish bosqichiga qaytaramiz!
        return StepAplication.APPLICATION


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Bu jarayon to'xtadi! ", reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END