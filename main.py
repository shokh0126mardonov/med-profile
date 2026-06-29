from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
)
from decouple import config
from handlers import (
    start, register, 
    get_full_name, get_contact,
    inline_callback,location,ariza,
    confirm_aplication,get_aplication,
    cancel,login,try_user,
    Steplogin,StepBot,StepAplication
)

def main() -> None:
    application = Application.builder().token(config("TOKEN")).build()
    
    # application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('start', location))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', register)],
        states={
            StepBot.FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, callback=get_full_name)],
            
            StepBot.PHONE_NUMBER: [MessageHandler(filters.CONTACT, callback=get_contact)],
            
            StepBot.CONFIRM: [CallbackQueryHandler(inline_callback)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True 
    )


    conv_handler2 = ConversationHandler(
        entry_points=[CommandHandler('login',login)],
        states={
            Steplogin.CONTACT:[MessageHandler(filters=filters.CONTACT ,callback=try_user)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conv_handler3 = ConversationHandler(
        entry_points=[CommandHandler('ariza', ariza)],
        states={
            StepAplication.APPLICATION:[MessageHandler(filters=filters.TEXT &  ~filters.COMMAND,callback=get_aplication)],
            StepAplication.CONFIRM:[CallbackQueryHandler(confirm_aplication)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True 
    )

    application.add_handler(conv_handler)
    application.add_handler(conv_handler2)
    application.add_handler(conv_handler3)
    
    print("Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()