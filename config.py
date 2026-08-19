import os
from dotenv import load_dotenv

load_dotenv()

SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/YourSupportID")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@YourChannel")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/YourChannel")

# تنظیمات مربوط به اموجی‌های پریمیوم
# اگر می‌خواهید از اموجی پریمیوم استفاده کنید، آیدی آن را به جای 0 قرار دهید.
# مثال: EMOJI_WELCOME = "5458904472598095631"

EMOJI_WELCOME = "5458904472598095631"      # اموجی سلام و خوشآمدگویی
EMOJI_SHOP = "4970023558068568720"         # اموجی فروشگاه و لیست محصولات
EMOJI_PRODUCT = "5796185041717433060"      # اموجی کنار نام محصول
EMOJI_DESC = "0"         # اموجی توضیحات محصول
EMOJI_PRICE = "0"        # اموجی قیمت
EMOJI_CART = "0"         # اموجی سبد خرید
EMOJI_CARD = "0"         # اموجی کارت بانکی
EMOJI_CAMERA = "0"       # اموجی دوربین/ارسال رسید
EMOJI_SUCCESS = "0"      # اموجی تایید و موفقیت
EMOJI_ERROR = "0"        # اموجی خطا و رد شدن
EMOJI_NEW_ORDER = "0"    # اموجی سفارش جدید برای ادمین
EMOJI_USER = "0"         # اموجی کاربر
EMOJI_SUPPORT = "0"      # اموجی بخش پشتیبانی
EMOJI_ORDERS = "0"       # اموجی بخش سفارشات من
EMOJI_ADMIN_PROMPT = "0" # اموجی درخواست ارسال اطلاعات از ادمین
EMOJI_ADMIN_SUCCESS = "0" # اموجی موفقیت ارسال برای ادمین

def get_emoji(emoji_id: str, fallback_emoji: str) -> str:
    """
    Returns the HTML tag for a custom emoji if an ID is provided,
    otherwise returns the fallback standard emoji.
    """
    if emoji_id and emoji_id != "0":
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback_emoji}</tg-emoji>'
    return fallback_emoji
