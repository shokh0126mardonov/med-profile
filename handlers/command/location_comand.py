import os
import django

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from decouple import config

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 
django.setup()

from apps.users.models import SickModel

async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lat = config('LATITUDE', cast=float)
    lon = config('LONGITUDE', cast=float)
    
    user_id = update.effective_user.id  
    
    is_registered = await SickModel.objects.filter(telegram_id=user_id).aexists()
    
    med_text = (
        "🏥 **Tibbiyot Markazimiz Joylashuvi**\n\n"
        "📍 **Manzil:** Toshkent sh., Chilonzor tumani, 9-kvartal\n"
        "🏢 **Moʻljal:** Xalq banki roʻparasi\n\n"
        "🕒 **Ish vaqti:** 24/7 (Tez yordam va qabul boʻlimi doim ochiq)\n"
        "📞 **Aloqa:** +998 (71) 123-45-67\n\n"
        "👇 Quyida xarita orqali aniq lokatsiyamiz yuborildi.\n\n"
    )
    
    if not is_registered:
        med_text += "⚠️ **Siz hali ro'yxatdan o'tmagansiz!**\nKlinika xizmatlaridan foydalanish va shifokorlarimizga ariza yuborish uchun, iltimos, avval 👉 /register buyrug'i orqali ro'yxatdan o'ting."
    else:
        med_text += "✅ **Siz tizimdan muvaffaqiyatli o'tgansiz!**\nAgarda shifokorlarimizga shaxsiy ariza yoki tashxis bo'yicha murojaat yubormoqchi bo'lsangiz, 👉 /ariza buyrug'ini bosing."

    inline_keyboard = [
        [
            InlineKeyboardButton(
                text="🗺️ Google Maps'da ochish", 
                url=f"https://www.google.com/maps?q={lat},{lon}" 
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    await update.message.reply_location(
        latitude=lat,
        longitude=lon
    )

    await update.message.reply_text(
        text=med_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

