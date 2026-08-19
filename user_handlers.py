import os
import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
import config as cfg

def is_admin(telegram_id: int) -> bool:
    admin_id = os.getenv("ADMIN_ID")
    return str(telegram_id) == str(admin_id) if admin_id else False

router = Router()

# Setup states
class CheckoutState(StatesGroup):
    waiting_for_receipt = State()

class SupportState(StatesGroup):
    waiting_for_ticket = State()

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    e_welcome = cfg.get_emoji(cfg.EMOJI_WELCOME, "👋")
    safe_name = html.escape(callback.from_user.first_name)
    msg = await bot.send_message(
        callback.from_user.id,
        f"\u200f{e_welcome} {safe_name} عزیز، به فروشگاه Ai Horizon خوش آمدید.\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=kb.get_main_menu_kb()
    )
    await db.update_last_menu_msg_id(callback.from_user.id, msg.message_id)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await db.add_user(message.from_user.id, message.from_user.username)
    e_welcome = cfg.get_emoji(cfg.EMOJI_WELCOME, "👋")
    
    # Try to delete old menu from database memory (persists across restarts!)
    old_msg_id = await db.get_last_menu_msg_id(message.from_user.id)
    await state.clear()
    
    if old_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=old_msg_id)
            logging.info(f"Deleted old menu msg_id: {old_msg_id}")
        except Exception as e:
            logging.warning(f"Could not delete old menu msg_id {old_msg_id}: {e}")
            
    # Try to delete the /start command itself
    try:
        await message.delete()
    except Exception:
        pass
            
    safe_name = html.escape(message.from_user.first_name)
    msg = await message.answer(
        f"\u200f{e_welcome} {safe_name} عزیز، به فروشگاه Ai Horizon خوش آمدید.\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=kb.get_main_menu_kb()
    )
    # Save the new menu message id to database!
    await db.update_last_menu_msg_id(message.from_user.id, msg.message_id)


@router.callback_query(F.data == "menu_buy")
async def show_products_callback(callback: CallbackQuery):
    products = await db.get_products()
    e_shop = cfg.get_emoji(cfg.EMOJI_SHOP, "🛍")
    if not products:
        await callback.message.edit_text(
            "در حال حاضر محصولی در فروشگاه وجود ندارد.",
            reply_markup=kb.get_main_menu_kb()
        )
        return
    
    await callback.message.edit_text(
        f"{e_shop} محصول مورد نظر خود را انتخاب کنید:",
        reply_markup=kb.get_products_kb(products)
    )


@router.callback_query(F.data == "menu_support")
async def show_support_callback(callback: CallbackQuery):
    e_support = cfg.get_emoji(cfg.EMOJI_SUPPORT, "📞")
    await callback.message.edit_text(
        f"{e_support} در صورت بروز هرگونه مشکل یا سوال می‌توانید با پشتیبانی در ارتباط باشید.",
        reply_markup=kb.get_support_kb()
    )

@router.callback_query(F.data == "support_ticket")
async def start_ticket(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 لطفا پیام، پیشنهاد یا مشکل خود را در قالب یک پیام متنی بنویسید و ارسال کنید:\n\n(برای لغو روی دکمه زیر کلیک کنید)",
        reply_markup=kb.get_cancel_ticket_kb()
    )
    await state.set_state(SupportState.waiting_for_ticket)
    # Save message ID so we can delete the prompt if they cancel or submit
    await state.update_data(prompt_msg_id=callback.message.message_id)

@router.callback_query(F.data == "cancel_ticket")
async def cancel_ticket_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_support_callback(callback)

@router.message(SupportState.waiting_for_ticket)
async def process_ticket(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    prompt_msg_id = data.get("prompt_msg_id")
    await state.clear()
    
    # Try to delete the prompt message
    if prompt_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
        except Exception:
            pass
            
    import os
    admin_id_str = os.getenv("ADMIN_ID")
    if not admin_id_str:
        await message.answer("❌ متاسفانه سیستم پشتیبانی در حال حاضر غیرفعال است.")
        return
    admin_id = int(admin_id_str)
    
    ticket_text = f"📩 <b>تیکت جدید از طرف کاربر!</b>\n\n"
    ticket_text += f"👤 نام: {html.escape(message.from_user.full_name)}\n"
    ticket_text += f"🆔 آیدی: <code>{message.from_user.id}</code>\n"
    if message.from_user.username:
        ticket_text += f"🔗 یوزرنیم: @{message.from_user.username}\n"
        
    ticket_text += f"\n📝 <b>متن پیام:</b>\n{html.escape(message.text or 'رسانه/فایل ارسال شد.')}"
    
    try:
        if message.text:
            await bot.send_message(admin_id, ticket_text)
        else:
            await message.copy_to(admin_id, caption=ticket_text)
            
        await message.answer(
            "✅ پیام شما با موفقیت برای پشتیبانی ارسال شد. در اسرع وقت از طریق همین ربات به شما پاسخ داده خواهد شد.",
            reply_markup=kb.get_main_menu_kb()
        )
    except Exception as e:
        logging.error(f"Error sending ticket: {e}")
        await message.answer(
            "❌ متاسفانه در ارسال پیام مشکلی رخ داد.",
            reply_markup=kb.get_main_menu_kb()
        )


@router.callback_query(F.data == "menu_orders")
async def show_orders_callback(callback: CallbackQuery):
    e_orders = cfg.get_emoji(cfg.EMOJI_ORDERS, "📦")
    orders = await db.get_user_orders(callback.from_user.id)
    
    if not orders:
        await callback.message.edit_text(
            f"{e_orders} شما هنوز هیچ سفارشی ثبت نکرده‌اید.",
            reply_markup=kb.get_main_menu_kb()
        )
        return
        
    text = f"{e_orders} <b>لیست سفارشات شما:</b>\n\n"
    for order in orders:
        order_dict = dict(order)
        status_raw = order_dict['status']
        if status_raw == 'pending':
            status = "⏳ در حال بررسی"
        elif status_raw == 'approved':
            status = "✅ تحویل داده شده"
        elif status_raw == 'rejected':
            status = "❌ رد شده"
        else:
            status = status_raw
            
        date = order_dict['created_at'][:16].replace("T", " ") # Format: YYYY-MM-DD HH:MM
        
        text += f"▪️ <b>سفارش #{order_dict['id']}</b>\n"
        text += f"محصول: {order_dict['product_name']}\n"
        text += f"وضعیت: {status}\n"
        text += f"تاریخ: {date}\n"
        
        if status_raw == 'approved':
            acc_details = order_dict.get('account_details')
            if acc_details:
                text += f"اطلاعات اکانت:\n<code>{html.escape(acc_details)}</code>\n"
                
        text += "\n"
        
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_main_menu_kb()
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
        
    e_welcome = cfg.get_emoji(cfg.EMOJI_WELCOME, "👋")
    safe_name = html.escape(callback.from_user.first_name)
    await callback.message.edit_text(
        f"\u200f{e_welcome} {safe_name} عزیز، به فروشگاه Ai Horizon خوش آمدید.\n\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=kb.get_main_menu_kb()
    )
    # Save the edited message id to database so /start can delete it later
    await db.update_last_menu_msg_id(callback.from_user.id, callback.message.message_id)


@router.callback_query(F.data == "back_to_products")
async def back_to_products_handler(callback: CallbackQuery):
    products = await db.get_products()
    e_shop = cfg.get_emoji(cfg.EMOJI_SHOP, "🛍")
    await callback.message.edit_text(
        f"{e_shop} محصول مورد نظر خود را انتخاب کنید:",
        reply_markup=kb.get_products_kb(products)
    )


@router.callback_query(F.data.startswith("prod_"))
async def product_details_handler(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = await db.get_product(product_id)
    
    if not product:
        await callback.answer("محصول یافت نشد!", show_alert=True)
        return
        
    product_dict = dict(product)
    emoji_id = product_dict.get('emoji_id')
    if not emoji_id or emoji_id == '0':
        emoji_id = cfg.EMOJI_PRODUCT
    e_prod = cfg.get_emoji(emoji_id, "🔹")
    e_price = cfg.get_emoji(cfg.EMOJI_PRICE, "💰")
    e_desc = cfg.get_emoji(cfg.EMOJI_DESC, "📝")
    
    text = f"{e_prod} <b>{product['name']}</b>\n\n"
    text += f"{e_desc} توضیحات: {product['description']}\n"
    text += f"{e_price} قیمت: {product['price']:,} تومان\n"
    
    await callback.message.edit_text(text, reply_markup=kb.get_product_details_kb(product_id))


@router.callback_query(F.data.startswith("buy_"))
async def buy_product_handler(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    product = await db.get_product(product_id)
    
    if not product:
        await callback.answer("محصول یافت نشد!", show_alert=True)
        return
    
    card_number = os.getenv("CARD_NUMBER", "تنظیم نشده")
    card_owner = os.getenv("CARD_OWNER_NAME", "تنظیم نشده")
    
    e_cart = cfg.get_emoji(cfg.EMOJI_CART, "🛒")
    e_card = cfg.get_emoji(cfg.EMOJI_CARD, "💳")
    e_camera = cfg.get_emoji(cfg.EMOJI_CAMERA, "📸")
    
    await callback.message.edit_text(
        f"{e_cart} شما در حال خرید <b>{product['name']}</b> هستید.\n"
        f"مبلغ قابل پرداخت: {product['price']:,} تومان\n\n"
        f"{e_card} لطفا مبلغ را به کارت زیر واریز کنید:\n\n"
        f"<code>{card_number}</code>\n\n"
        f"به نام: {card_owner}\n\n"
        f"{e_camera} پس از واریز، عکس رسید را همینجا ارسال کنید.",
        reply_markup=kb.get_receipt_kb()
    )
    
    await state.set_state(CheckoutState.waiting_for_receipt)
    await state.update_data(product_id=product_id)
    await callback.answer()


@router.message(CheckoutState.waiting_for_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    product_id = data.get('product_id')
    
    if not product_id:
        await message.answer("خطا: اطلاعات سفارش یافت نشد. لطفا دوباره از منوی اصلی اقدام کنید.")
        await state.clear()
        return
    
    product = await db.get_product(product_id)
    photo_id = message.photo[-1].file_id
    
    try:
        # Save order to DB
        order_id = await db.create_order(message.from_user.id, product_id, photo_id)
        
        # Send to admin
        try:
            admin_id = int(os.getenv("ADMIN_ID", "0"))
        except ValueError:
            admin_id = 0
            
        if admin_id:
            e_new = cfg.get_emoji(cfg.EMOJI_NEW_ORDER, "🆕")
            e_user = cfg.get_emoji(cfg.EMOJI_USER, "👤")
            e_cart = cfg.get_emoji(cfg.EMOJI_CART, "🛍")
            e_price = cfg.get_emoji(cfg.EMOJI_PRICE, "💰")
            
            username = message.from_user.username or "بدون_آیدی"
            admin_text = f"{e_new} <b>سفارش جدید (#{order_id})</b>\n\n"
            admin_text += f"{e_user} کاربر: @{username} (ID: {message.from_user.id})\n"
            admin_text += f"{e_cart} محصول: {product['name']}\n"
            admin_text += f"{e_price} مبلغ: {product['price']:,} تومان\n"
            
            try:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_id,
                    caption=admin_text,
                    reply_markup=kb.get_admin_verification_kb(order_id)
                )
            except Exception as e:
                logging.error(f"Failed to send order to admin: {e}")
        
        e_success = cfg.get_emoji(cfg.EMOJI_SUCCESS, "✅")
        msg = await message.answer(
            f"{e_success} رسید شما با موفقیت ثبت شد و در حال بررسی است...\n"
            "پس از تایید ادمین، اطلاعات اکانت برای شما ارسال خواهد شد.",
            reply_markup=kb.get_main_menu_kb()
        )
        
        # Save the new menu message id to database!
        await db.update_last_menu_msg_id(message.from_user.id, msg.message_id)
    except Exception as e:
        logging.error(f"Error in process_receipt: {e}")
        await message.answer("❌ متاسفانه خطایی در ثبت رسید رخ داد. لطفا بعدا تلاش کنید یا با پشتیبانی تماس بگیرید.")
    finally:
        await state.clear()


@router.message(CheckoutState.waiting_for_receipt)
async def process_receipt_invalid(message: Message):
    e_error = cfg.get_emoji(cfg.EMOJI_ERROR, "❌")
    await message.answer(f"{e_error} لطفا عکس رسید واریز را ارسال کنید (به صورت عکس، نه فایل یا متن).")


@router.message()
async def fallback_old_keyboard(message: Message):
    await message.answer(
        "لطفا از دکمه‌های شیشه‌ای منو استفاده کنید. (اگر منو را نمی‌بینید، دستور /start را ارسال کنید)",
        reply_markup=ReplyKeyboardRemove()
    )
