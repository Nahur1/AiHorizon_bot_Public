import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import database as db
from user_handlers import router as user_router
from admin_handlers import router as admin_router

load_dotenv()

async def main():
    logging.basicConfig(level=logging.INFO)
    
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token or bot_token == "your_bot_token_here":
        logging.error("BOT_TOKEN is missing! Please set it in .env file.")
        return

    # Init database
    await db.init_db()

    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    from middlewares import ForceJoinMiddleware
    
    dp.message.middleware(ForceJoinMiddleware())
    dp.callback_query.middleware(ForceJoinMiddleware())

    dp.include_router(admin_router)
    dp.include_router(user_router)

    # Set the bot commands to show a "Menu" button on the bottom left
    from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat

    # Default commands for everyone
    await bot.set_my_commands(
        [BotCommand(command="start", description="🏠 منوی اصلی")],
        scope=BotCommandScopeAllPrivateChats()
    )

    # Specific commands just for the admin
    admin_id = os.getenv("ADMIN_ID")
    if admin_id:
        try:
            await bot.set_my_commands(
                [
                    BotCommand(command="start", description="🏠 منوی اصلی"),
                    BotCommand(command="admin", description="⚙️ پنل مدیریت")
                ],
                scope=BotCommandScopeChat(chat_id=int(admin_id))
            )
        except Exception as e:
            logging.error(f"Failed to set admin commands: {e}")

    logging.info("Starting bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
