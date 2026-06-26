from telegram import Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get('login'):
        welcome_back_text = (
            "👋 **Assalomu alaykum! Tibbiyot markazimiz botiga xush kelibsiz!**\n\n"
            "Siz tizimdan muvaffaqiyatli oʻtgansiz. Quyidagi buyruqlar orqali xizmatlarimizdan foydalanishingiz mumkin:\n\n"
            "📍 /location — Klinikamizning aniq manzili va geografik joylashuvi\n"
            "📝 /ariza — Shifokor koʻrigiga ariza qoldirish. Kasallik belgilari yoki sizni qiynayotgan simptomlarni yozib qoldiring, shifokorlarimiz siz bilan bogʻlanishadi.\n\n"
            "🏥 _Sizning salomatligingiz — bizning oliy maqsadimiz!_"
        )
        await update.message.reply_text(
            text=welcome_back_text,
            parse_mode="Markdown"
        )
    else:
        # Tizimga kirmaganlar uchun ogohlantirish dizayni
            login_required_text = (
                "🔒 **Xizmatlardan foydalanish uchun tizimga kirish talab etiladi.**\n\n"
                "Agar siz avval roʻyxatdan oʻtgan boʻlsangiz, tizimga kirish uchun 👉 /login buyrugʻini bosing.\n\n"
                "Agar birinchi marta kirayotgan boʻlsangiz, avval 👉 /register buyrugʻi orqali roʻyxatdan oʻting."
            )
            await update.message.reply_text(
                text=login_required_text,
                parse_mode="Markdown"
            )