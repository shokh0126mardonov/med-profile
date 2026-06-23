from telegram import Update
from telegram.ext import (
    Application,CommandHandler,ConversationHandler,MessageHandler,filters
)
from decouple import config
from handlers import start,login,StepBot,get_full_name

def main() -> None:
    application = Application.builder().token(config("TOKEN")).build()
    
    application.add_handler(
        CommandHandler(
            'start',start
        )
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login',login)],
        states={
            StepBot.FULL_NAME:[MessageHandler(filters=filters.TEXT,callback=get_full_name)]
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()