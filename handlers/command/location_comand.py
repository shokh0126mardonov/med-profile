from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from decouple import config

async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get('login'):
        lat = config('LATITUDE', cast=float)
        lon = config('LONGITUDE', cast=float)
        
        med_text = (
            "🏥 **Tibbiyot Markazimiz Joylashuvi**\n\n"
            "📍 **Manzil:** Toshkent sh., Chilonzor tumani, 9-kvartal\n"
            "🏢 **Moʻljal:** Xalq banki roʻparasi\n\n"
            "🕒 **Ish vaqti:** 24/7 (Tez yordam va qabul boʻlimi doim ochiq)\n"
            "📞 **Aloqa:** +998 (71) 123-45-67\n\n"
            "👇 Quyida xarita orqali aniq lokatsiyamiz yuborildi."
        )
        
        inline_keyboard = [
            [
                InlineKeyboardButton(
                    text="🗺️ Google Maps'da ochish", 
                    url=f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard)

        await update.message.reply_text(
            text=med_text,
            # reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        await update.message.reply_location(
            latitude=lat,
            longitude=lon
        )
    
    else:
        login_required_text = (
            "🔒 **Xizmatlardan foydalanish uchun tizimga kirish talab etiladi.**\n\n"
            "Klinika shifokorlari bilan bogʻlanish va arizangizni koʻrib chiqishimiz uchun, iltimos, avval roʻyxatdan oʻting:\n\n"
            "👉 /login buyrugʻini bosing."
        )
        await update.message.reply_text(
            text=login_required_text,
            parse_mode="Markdown"
        )