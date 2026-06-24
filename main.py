from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
)
from decouple import config
from handlers import start, login, StepBot, get_full_name, get_contact, inline_callback

def main() -> None:
    application = Application.builder().token(config("TOKEN")).build()
    
    application.add_handler(CommandHandler('start', start))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login)],
        states={
            StepBot.FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, callback=get_full_name)],
            
            StepBot.PHONE_NUMBER: [MessageHandler(filters.CONTACT, callback=get_contact)],
            
            StepBot.CONFIRM: [CallbackQueryHandler(inline_callback)]
        },
        fallbacks=[],
        allow_reentry=True 
    )

    application.add_handler(conv_handler)
    
    print("Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()