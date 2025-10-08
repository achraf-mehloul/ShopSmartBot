import asyncio
import json
import logging
import os
from pathlib import Path
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Data loading module
def load_products() -> list[dict]:
    """Load products from data/products.json."""
    products_path = Path("data/products.json")
    if not products_path.exists():
        logger.error("products.json not found in data/ folder")
        raise FileNotFoundError("data/products.json missing")
    
    try:
        with open(products_path, "r", encoding="utf-8") as f:
            products = json.load(f)
        logger.info(f"Loaded {len(products)} products from JSON")
        return products
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in products.json: {e}")
        raise ValueError("Invalid JSON format in products.json")

# Platform selection
PLATFORM_MAP = {
    "express": "⚡ علي إكس براس",
    "trendyol": "🛍️ تريندويل", 
    "amazon": "🚀 أمازون"
}

# Category mapping (English JSON keys to Arabic button labels)
CATEGORY_MAP = {
    "groceries": "🛒 مواد غذائية",
    "beauty": "💄 الجمال",
    "mobiles": "📱 الجوالات",
    "home_appliances": "🏠 الأجهزة المنزلية"
}

def get_greeting() -> str:
    """Get dynamic greeting based on time of day."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "صباح الخير! 🌅"
    elif 12 <= hour < 18:
        return "مساء الخير! ☀️"
    else:
        return "مساء الخير! 🌙"

def get_products_by_category(products: list[dict], category: str) -> list[dict]:
    """Filter products by category."""
    return [p for p in products if p.get("category") == category][:3]  # Limit to 3

def get_placeholder_image() -> FSInputFile:
    """Get fallback placeholder image."""
    placeholder_path = Path("assets/placeholder.jpg")
    if not placeholder_path.exists():
        logger.warning("Placeholder image not found; using text fallback")
        return None
    return FSInputFile(placeholder_path)

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for MarkdownV2."""
    reserved_chars = r'_*[]()~`>#+-=|{}.!/'
    for char in reserved_chars:
        text = text.replace(char, f'\\{char}')
    return text

# Handlers
@router.message(CommandStart())
async def start_handler(message: Message):
    """Handle /start command with beautiful design."""
    greeting = get_greeting()
    welcome_text = (
        f"{greeting}\n\n"
        "🎉 **مرحباً بك في متجرنا الإلكتروني!** 🌟\n\n"
        "✨ *اختر المنصة التي تريد استعراض عروضها:*"
    )
    
    # Beautiful platform selection keyboard
    builder = ReplyKeyboardBuilder()
    
    # Add platform buttons with beautiful spacing
    for platform in PLATFORM_MAP.values():
        builder.add(KeyboardButton(text=platform))
    
    builder.adjust(1)  # One button per row for better UX
    
    keyboard = builder.as_markup(
        resize_keyboard=True, 
        one_time_keyboard=False,
        input_field_placeholder="👉 اختر منصة..."
    )
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

@router.message(F.text == "🚀 أمازون")
async def amazon_handler(message: Message):
    """Handle Amazon platform selection with beautiful design."""
    welcome_text = (
        "🚀 **مرحباً بك في أمازون!**\n\n"
        "🛍️ *اختر القسم الذي يهمك لعرض العروض الحصرية:*"
    )
    
    # Beautiful category keyboard for Amazon
    builder = ReplyKeyboardBuilder()
    
    # Add category buttons with emojis
    for arabic_label in CATEGORY_MAP.values():
        builder.add(KeyboardButton(text=arabic_label))
    
    # Add back button
    builder.add(KeyboardButton(text="↩️ رجوع إلى المنصات"))
    
    builder.adjust(2)  # Two buttons per row
    
    keyboard = builder.as_markup(
        resize_keyboard=True, 
        one_time_keyboard=False,
        input_field_placeholder="🎯 اختر القسم..."
    )
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

@router.message(F.text == "↩️ رجوع إلى المنصات")
async def back_to_platforms_handler(message: Message):
    """Handle back to platforms."""
    await start_handler(message)

@router.message(F.text.in_(list(CATEGORY_MAP.values())))
async def category_handler(message: Message):
    """Handle category selection with beautiful product display."""
    try:
        products = load_products()
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Data load error: {e}")
        await message.answer(
            "⚠️ **عذراً، حدث خطأ مؤقت**\nالرجاء المحاولة لاحقًا.",
            parse_mode="Markdown"
        )
        return
    
    # Map Arabic text back to English category
    selected_category = next((k for k, v in CATEGORY_MAP.items() if v == message.text), None)
    if not selected_category:
        await message.answer("❌ قسم غير معروف. استخدم /start للبدء.")
        return
    
    cat_products = get_products_by_category(products, selected_category)
    if not cat_products:
        await message.answer(
            "📦 **لا توجد منتجات في هذا القسم حالياً**\n\n"
            "✨ جاري تحديث العروض قريباً!",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="↩️ رجوع إلى المنصات")]],
                resize_keyboard=True
            ),
            parse_mode="Markdown"
        )
        return
    
    # Remove keyboard and show loading message
    await message.answer(
        f"🔄 **جاري تحميل المنتجات في {message.text}...**", 
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    
    # Send each product with beautiful design
    for idx, product in enumerate(cat_products, 1):
        await send_product_message(message, product, idx)
    
    # End of list message with beautiful back button
    end_text = (
        "🎊 **تم عرض جميع المنتجات**\n\n"
        "💫 *اختر قسم آخر أو عد إلى القائمة الرئيسية*"
    )
    
    back_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 عرض المزيد"), KeyboardButton(text="↩️ رجوع إلى المنصات")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(end_text, reply_markup=back_keyboard, parse_mode="Markdown")

@router.message(F.text == "🛒 عرض المزيد")
async def show_more_handler(message: Message):
    """Handle show more products."""
    await amazon_handler(message)

async def send_product_message(message: Message, product: dict, idx: int):
    """Send a beautiful product message with photo and caption."""
    image_path = Path(product.get("image", ""))
    photo = None
    if image_path.exists():
        photo = FSInputFile(image_path)
    else:
        photo = get_placeholder_image()
    
    caption = await _build_caption(product, idx)
    keyboard = await _build_product_keyboard(product["detail_url"])
    
    try:
        if photo:
            await message.answer_photo(
                photo=photo, 
                caption=caption, 
                reply_markup=keyboard, 
                parse_mode="MarkdownV2"
            )
        else:
            await message.answer(
                caption, 
                reply_markup=keyboard, 
                parse_mode="MarkdownV2"
            )
    except Exception as e:
        logger.error(f"Failed to send product {product['id']}: {e}")
        # Fallback to plain text with beautiful design
        plain_caption = caption.replace('\\*', '*').replace('~~', '').replace('➡️', '->')
        await message.answer(plain_caption, reply_markup=keyboard)

async def _build_caption(product: dict, idx: int) -> str:
    """Build beautiful formatted Arabic caption for a product."""
    title = product["title"]
    old_price = product.get("old_price", 0)
    new_price = product["new_price"]
    savings = old_price - new_price if old_price > 0 else 0
    
    # Escape text for MarkdownV2
    escaped_title = escape_markdown_v2(title)
    escaped_old_price = escape_markdown_v2(f"{old_price} ريال")
    escaped_new_price = escape_markdown_v2(f"{new_price} ريال")
    escaped_savings = escape_markdown_v2(f"{savings} ريال")
    
    # Build beautiful caption with emojis and formatting
    caption = f"*🏷️ المنتج {idx}: {escaped_title}*\n\n"
    
    # Price information with beautiful formatting
    if old_price > 0:
        caption += f"💵 *السعر:*\n~~{escaped_old_price}~~ ➡️ *{escaped_new_price}*\n"
        caption += f"💰 *وفرت: {escaped_savings}* 🎉"
    else:
        caption += f"💵 *السعر: {escaped_new_price}*"
    
    return caption

async def _build_product_keyboard(detail_url: str) -> InlineKeyboardMarkup:
    """Build beautiful inline keyboard for product."""
    # Create a more attractive button
    button = InlineKeyboardButton(
        text="🛒 اشترِ الآن", 
        url=detail_url
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])

# Handle other platforms (currently only Amazon works)
@router.message(F.text.in_(["⚡ علي إكس براس", "🛍️ تريندويل"]))
async def other_platforms_handler(message: Message):
    """Handle other platforms - show coming soon message."""
    platform_name = message.text
    coming_soon_text = (
        f"{platform_name}\n\n"
        "🚧 **جاري التطوير**\n\n"
        "⚡ *هذه المنصة قيد التطوير حالياً*\n"
        "✨ ستكون متاحة قريباً بإذن الله\n\n"
        "💎 *يمكنك تجربة منصة أمازون الآن!*"
    )
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 أمازون")],
            [KeyboardButton(text="↩️ رجوع إلى المنصات")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(coming_soon_text, reply_markup=keyboard, parse_mode="Markdown")

# Main entry point
async def main():
    """Start the bot."""
    logger.info("🚀 Starting Beautiful E-Commerce Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())