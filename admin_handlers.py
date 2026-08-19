import os
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import config as cfg

router = Router()

class AdminDeliveryState(StatesGroup):
    waiting_for_account_details = State()

def is_admin(telegram_id: int) -> bool:
    admin_id = os.getenv("ADMIN_ID")
    if not admin_id:
        return False
    return str(telegram_id) == str(admin_id)

@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve_order(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("شما دسترسی ندارید.", show_alert=True)
        return

    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("سفارش یافت نشد.", show_alert=True)
        return
        
    if order['status'] != 'pending':
        await callback.answer("این سفارش قبلا تعیین وضعیت شده است.", show_alert=True)
        return

    # Prompt admin to enter details
    e_prompt = cfg.get_emoji(cfg.EMOJI_ADMIN_PROMPT, "✍️")
    await callback.message.answer(f"{e_prompt} لطفا ایمیل و پسورد اکانت را برای تحویل به کاربر ارسال کنید:\n(مربوط به سفارش #{order_id})")
    
    await state.set_state(AdminDeliveryState.waiting_for_account_details)
    await state.update_data(order_id=order_id, msg_to_edit_id=callback.message.message_id, msg_to_edit_chat=callback.message.chat.id)
    await callback.answer()


@router.message(AdminDeliveryState.waiting_for_account_details)
async def process_manual_delivery(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    order_id = data['order_id']
    msg_to_edit_id = data.get('msg_to_edit_id')
    msg_to_edit_chat = data.get('msg_to_edit_chat')
    
    account_details = message.text
    
    if not account_details:
        await message.answer("لطفا اطلاعات اکانت را به صورت متن ارسال کنید.")
        return
    
    order = await db.get_order(order_id)
    if not order:
        await message.answer("خطا: سفارش یافت نشد.")
        await state.clear()
        return

    user_id = order['telegram_id']
    product_id = order['product_id']
    product = await db.get_product(product_id)
    
    e_success = cfg.get_emoji(cfg.EMOJI_SUCCESS, "✅")
    e_prod = cfg.get_emoji(cfg.EMOJI_PRODUCT, "🔹")
    admin_text = message.text
    
    # Save the order status AND the account details in the DB
    await db.approve_order_manual(order_id, account_details=admin_text)
    
    # Send account to user
    msg_to_user = f"{e_success} <b>پرداخت شما تایید شد!</b>\n\n"
    msg_to_user += f"{e_prod} محصول: {product['name']}\n\n"
    msg_to_user += f"اطلاعات اکانت شما:\n<code>{account_details}</code>\n\n"
    msg_to_user += "از خرید شما متشکریم! 🙏"
    
    try:
        await bot.send_message(user_id, msg_to_user)
        
        # Edit the original receipt message caption
        if msg_to_edit_id and msg_to_edit_chat:
            try:
                # Get original message to read its caption
                # We edit caption by appending approval status
                await bot.edit_message_caption(
                    chat_id=msg_to_edit_chat,
                    message_id=msg_to_edit_id,
                    caption=f"{e_success} تایید شد و اکانت ارسال شد. (سفارش #{order_id})"
                )
            except Exception as e:
                logging.warning(f"Could not edit admin message caption: {e}")
                
        e_admin_success = cfg.get_emoji(cfg.EMOJI_ADMIN_SUCCESS, "✅")
        await message.answer(f"{e_admin_success} اکانت با موفقیت برای کاربر ارسال شد.")
    except Exception as e:
        logging.error(f"Error sending account to user: {e}")
        await message.answer(f"خطا در ارسال پیام به کاربر: {e}")
        
    await state.clear()


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_order(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("شما دسترسی ندارید.", show_alert=True)
        return

    order_id = int(callback.data.split("_")[2])
    order = await db.get_order(order_id)
    
    if not order:
        await callback.answer("سفارش یافت نشد.", show_alert=True)
        return
        
    if order['status'] != 'pending':
        await callback.answer("این سفارش قبلا تعیین وضعیت شده است.", show_alert=True)
        return

    await db.reject_order(order_id)
    
    user_id = order['telegram_id']
    product_id = order['product_id']
    product = await db.get_product(product_id)
    
    e_error = cfg.get_emoji(cfg.EMOJI_ERROR, "❌")
    
    msg_to_user = f"{e_error} <b>پرداخت شما برای {product['name']} تایید نشد!</b>\n\n"
    msg_to_user += "لطفا برای پیگیری با پشتیبانی در ارتباط باشید."
    
    try:
        await bot.send_message(user_id, msg_to_user)
        try:
            await callback.message.edit_caption(
                caption=callback.message.caption + f"\n\n{e_error} رد شد."
            )
        except Exception as e:
            logging.warning(f"Could not edit caption: {e}")
        await callback.answer("سفارش رد شد و به کاربر اطلاع داده شد.")
    except Exception as e:
        logging.error(f"Error rejecting order: {e}")
        await callback.answer(f"خطا در ارسال پیام به کاربر: {e}", show_alert=True)

# ---------------- Product Management ----------------

from aiogram.filters import Command

class AdminProductState(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_desc = State()
    waiting_for_emoji = State()

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    import keyboards as kb
    await message.answer("ورود به پنل مدیریت:", reply_markup=kb.get_admin_panel_kb())

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    import keyboards as kb
    await callback.message.edit_text("ورود به پنل مدیریت:", reply_markup=kb.get_admin_panel_kb())

@router.callback_query(F.data == "admin_add_product")
async def admin_add_product(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("نام محصول جدید را وارد کنید:\n(برای لغو /cancel را بفرستید)")
    await state.set_state(AdminProductState.waiting_for_name)

@router.message(AdminProductState.waiting_for_name)
async def process_product_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    import keyboards as kb
    if message.text == "/cancel":
        await state.clear()
        await message.answer("عملیات لغو شد.", reply_markup=kb.get_admin_panel_kb())
        return
    await state.update_data(name=message.text)
    await message.answer("قیمت محصول را به تومان (فقط عدد) وارد کنید:")
    await state.set_state(AdminProductState.waiting_for_price)

@router.message(AdminProductState.waiting_for_price)
async def process_product_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    import keyboards as kb
    if message.text == "/cancel":
        await state.clear()
        await message.answer("عملیات لغو شد.", reply_markup=kb.get_admin_panel_kb())
        return
    if not message.text.isdigit():
        await message.answer("لطفا فقط عدد وارد کنید!")
        return
    await state.update_data(price=int(message.text))
    await message.answer("توضیحات محصول را وارد کنید:")
    await state.set_state(AdminProductState.waiting_for_desc)

@router.message(AdminProductState.waiting_for_desc)
async def process_product_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    import keyboards as kb
    if message.text == "/cancel":
        await state.clear()
        await message.answer("عملیات لغو شد.", reply_markup=kb.get_admin_panel_kb())
        return
    await state.update_data(desc=message.text)
    await message.answer("حالا اموجی پریمیوم را بفرستید (کافیست خود اموجی را از کیبورد تلگرام بفرستید).\n(اگر اموجی خاصی ندارید، عدد 0 را بفرستید):")
    await state.set_state(AdminProductState.waiting_for_emoji)

@router.message(AdminProductState.waiting_for_emoji)
async def process_product_emoji(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    import keyboards as kb
    if message.text == "/cancel":
        await state.clear()
        await message.answer("عملیات لغو شد.", reply_markup=kb.get_admin_panel_kb())
        return
        
    data = await state.get_data()
    name = data['name']
    price = data['price']
    desc = data['desc']
    
    emoji_id = "0"
    if message.text != "0" and message.entities:
        for entity in message.entities:
            if entity.type == "custom_emoji":
                emoji_id = entity.custom_emoji_id
                break
    
    if message.text != "0" and emoji_id == "0":
        await message.answer("اموجی پریمیوم یافت نشد! لطفا فقط یک اموجی پریمیوم بفرستید، یا عدد 0 را وارد کنید.")
        return
    
    await db.add_product(name, price, desc, emoji_id)
    await state.clear()
    await message.answer(f"✅ محصول <b>{name}</b> با موفقیت اضافه شد!", reply_markup=kb.get_admin_panel_kb())

@router.callback_query(F.data == "admin_del_product")
async def admin_del_product_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    import keyboards as kb
    products = await db.get_products()
    if not products:
        await callback.answer("محصولی وجود ندارد!", show_alert=True)
        return
    await callback.message.edit_text("برای حذف، روی محصول مورد نظر کلیک کنید:", reply_markup=kb.get_admin_products_kb(products))

@router.callback_query(F.data.startswith("admin_del_prod_"))
async def admin_delete_product(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    import keyboards as kb
    prod_id = int(callback.data.split("_")[3])
    await db.delete_product(prod_id)
    
    products = await db.get_products()
    if not products:
        await callback.message.edit_text("✅ محصول حذف شد.\nدیگر محصولی در فروشگاه وجود ندارد.", reply_markup=kb.get_admin_panel_kb())
    else:
        await callback.message.edit_text("✅ محصول حذف شد. یک محصول دیگر برای حذف انتخاب کنید:", reply_markup=kb.get_admin_products_kb(products))
import html
import re

@router.message(F.reply_to_message)
async def admin_reply_to_ticket(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
        
    replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    
    if "تیکت جدید از طرف کاربر!" in replied_text:
        match = re.search(r"🆔 آیدی:\s*(?:<code>)?(\d+)", replied_text)
        if match:
            user_id = int(match.group(1))
            try:
                reply_text = f"👨‍💻 <b>پاسخ پشتیبانی به تیکت شما:</b>\n\n{html.escape(message.text or 'پیوست ارسال شد.')}"
                
                if message.text:
                    await bot.send_message(user_id, reply_text)
                else:
                    await message.copy_to(user_id, caption=reply_text)
                    
                await message.answer("✅ پاسخ شما با موفقیت برای کاربر ارسال شد.")
            except Exception as e:
                logging.error(f"Error sending reply to user: {e}")
                await message.answer("❌ خطا در ارسال پیام به کاربر. ممکن است کاربر ربات را بلاک کرده باشد.")
        else:
            await message.answer("❌ آیدی کاربر در متن پیام پیدا نشد!")
