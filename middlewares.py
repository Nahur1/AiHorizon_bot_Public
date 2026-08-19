import os
import logging
from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatMemberStatus

import keyboards as kb
import config as cfg

async def check_membership(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=cfg.CHANNEL_USERNAME, user_id=user_id)
        return member.status in [
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.RESTRICTED
        ]
    except Exception as e:
        logging.error(f"Force Join Error: {e}")
        # If bot is not admin, API returns Bad Request. We allow access to prevent locking everyone out.
        return True 

class ForceJoinMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot = data['bot']
        user = data.get('event_from_user')
        chat = data.get('event_chat')
        
        if not user or not chat:
            return await handler(event, data)
            
        # Admin bypass
        admin_id_str = os.getenv("ADMIN_ID", "")
        if str(user.id) == admin_id_str:
            return await handler(event, data)
            
        if isinstance(event, CallbackQuery) and event.data == "check_join":
            is_member = await check_membership(bot, user.id)
            if not is_member:
                await event.answer("❌ هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)
                return
            else:
                await event.answer("✅ عضویت شما تایید شد!", show_alert=True)
                return await handler(event, data)

        is_member = await check_membership(bot, user.id)
        
        if not is_member:
            text = "⚠️ <b>کاربر گرامی!</b>\n\nبرای استفاده از ربات و ثبت سفارش، لطفا ابتدا در کانال رسمی ما عضو شوید، سپس روی دکمه «✅ تایید عضویت» کلیک کنید."
            
            if isinstance(event, Message):
                # Only reply if it's a private chat
                if event.chat.type == "private":
                    await event.answer(text, reply_markup=kb.get_force_join_kb(cfg.CHANNEL_URL))
            elif isinstance(event, CallbackQuery):
                await event.message.edit_text(text, reply_markup=kb.get_force_join_kb(cfg.CHANNEL_URL))
            return # Block propagation
            
        return await handler(event, data)
