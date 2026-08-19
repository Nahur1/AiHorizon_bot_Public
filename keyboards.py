from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config as cfg


def _btn_kwargs(text: str, custom_id: str, fallback_emoji: str, style: str = "primary") -> dict:
    kwargs = {}
    if custom_id and custom_id != "0":
        kwargs = {"text": text, "icon_custom_emoji_id": custom_id}
    else:
        kwargs = {"text": f"{fallback_emoji} {text}"}
    
    if style in ["primary", "danger", "success"]:
        kwargs["style"] = style
    return kwargs

def get_main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        callback_data="menu_buy",
        **_btn_kwargs("خرید اکانت", cfg.EMOJI_SHOP, "🛒")
    )
    builder.button(
        callback_data="menu_orders",
        **_btn_kwargs("سفارشات من", cfg.EMOJI_ORDERS, "📦")
    )
    builder.button(
        callback_data="menu_support",
        **_btn_kwargs("پشتیبانی", cfg.EMOJI_SUPPORT, "📞")
    )
    
    builder.adjust(1, 2)
    return builder.as_markup()

def get_products_kb(products) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for prod in products:
        # Check if the product has a custom emoji in the database
        prod_dict = dict(prod)
        emoji_id = prod_dict.get('emoji_id')
        if not emoji_id or emoji_id == '0':
            emoji_id = cfg.EMOJI_PRODUCT
            
        builder.button(
            callback_data=f"prod_{prod['id']}",
            **_btn_kwargs(prod['name'], emoji_id, "🔹")
        )
    builder.button(
        callback_data="back_to_main",
        **_btn_kwargs("صفحه اصلی", "0", "🏠")
    )
    builder.adjust(1)
    return builder.as_markup()

def get_product_details_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        callback_data=f"buy_{product_id}",
        **_btn_kwargs("خرید", cfg.EMOJI_CARD, "💳", style="success")
    )
    builder.button(
        text="🔙 بازگشت به لیست", 
        callback_data="back_to_products",
    )
    builder.button(
        callback_data="back_to_main",
        **_btn_kwargs("صفحه اصلی", "0", "🏠")
    )
    builder.adjust(1)
    return builder.as_markup()

def get_admin_verification_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        callback_data=f"admin_approve_{order_id}",
        **_btn_kwargs("تایید و ارسال", cfg.EMOJI_SUCCESS, "✅", style="success")
    )
    builder.button(
        callback_data=f"admin_reject_{order_id}",
        **_btn_kwargs("رد رسید", cfg.EMOJI_ERROR, "❌", style="danger")
    )
    builder.adjust(2)
    return builder.as_markup()

def get_receipt_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        callback_data="back_to_main",
        **_btn_kwargs("لغو و بازگشت به منو", "0", "🏠", style="danger")
    )
    return builder.as_markup()

def get_support_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 چت مستقیم (DM)", url=cfg.SUPPORT_URL)
    builder.button(callback_data="support_ticket", **_btn_kwargs("📝 ارسال تیکت در ربات", "0", "📝"))
    builder.button(callback_data="back_to_main", **_btn_kwargs("بازگشت", "0", "🔙"))
    builder.adjust(1)
    return builder.as_markup()

def get_cancel_ticket_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(callback_data="cancel_ticket", **_btn_kwargs("انصراف", "0", "❌", style="danger"))
    return builder.as_markup()

def get_force_join_kb(channel_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 عضویت در کانال", url=channel_url)
    builder.button(callback_data="check_join", **_btn_kwargs("تایید عضویت", "0", "✅", style="success"))
    builder.adjust(1)
    return builder.as_markup()

def get_admin_panel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(callback_data="admin_add_product", **_btn_kwargs("افزودن محصول", "0", "➕"))
    builder.button(callback_data="admin_del_product", **_btn_kwargs("حذف محصول", "0", "➖", style="danger"))
    builder.button(callback_data="back_to_main", **_btn_kwargs("صفحه اصلی", "0", "🏠"))
    builder.adjust(2, 1)
    return builder.as_markup()

def get_admin_products_kb(products) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for prod in products:
        builder.button(callback_data=f"admin_del_prod_{prod['id']}", text=f"❌ {prod['name']}")
    builder.button(callback_data="admin_panel", **_btn_kwargs("بازگشت به پنل", "0", "🔙"))
    builder.adjust(1)
    return builder.as_markup()
