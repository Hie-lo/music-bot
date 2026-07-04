import asyncio
import logging
import os
import sys
from pathlib import Path

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, str(Path(__file__).parent))

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from handlers.play_handler import PlayHandler
from handlers.admin_handler import AdminHandler
from handlers.control_handler import ControlHandler

# ایجاد پوشه logs اگر وجود نداشت
if not os.path.exists('logs'):
    os.makedirs('logs')

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MusicBot:
    def __init__(self):
        self.app = Client(
            "musicbot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        
        # نمونه‌سازی هندلرها
        self.play_handler = PlayHandler(self.app)
        self.admin_handler = AdminHandler(self.app)
        self.control_handler = ControlHandler(self.app)
    
    async def start(self):
        """شروع ربات"""
        logger.info("🚀 ربات موزیک پلیر در حال راه‌اندازی...")
        
        # ========== ثبت دستورات اصلی با استفاده از filters.text ==========
        
        # دستور start و help
        @self.app.on_message(filters.command(["start", "help"]) & (filters.private | filters.group))
        async def start_command(client, message: Message):
            await self.send_welcome(message)
        
        # دستورات فارسی با filters.text
        @self.app.on_message(filters.text & filters.group)
        async def handle_text_messages(client, message: Message):
            await self.handle_text_message(message)
        
        # ========== ثبت هندلرهای callback ==========
        @self.app.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            await self.handle_callback(callback_query)
        
        # ========== ثبت هندلرهای اختصاصی ==========
        self.play_handler.register_handlers()
        self.admin_handler.register_handlers()
        self.control_handler.register_handlers()
        
        # ========== راه‌اندازی ربات ==========
        logger.info("✅ ربات آماده کار است!")
        await self.app.start()
        
        bot_info = await self.app.get_me()
        logger.info(f"🎵 ربات با نام @{bot_info.username} فعال شد")
        
        # نگه‌داشتن ربات در حالت اجرا
        await asyncio.Event().wait()
    
    async def stop(self):
        """توقف ربات"""
        logger.info("🛑 ربات در حال توقف...")
        await self.app.stop()
        logger.info("✅ ربات متوقف شد")
    
    async def handle_text_message(self, message: Message):
        """مدیریت پیام‌های متنی در گروه"""
        text = message.text or ""
        
        # شروع با / رو نادیده بگیر (برای دستورات انگلیسی)
        if text.startswith('/'):
            return
        
        # دستورات فارسی
        if text.startswith('پخش '):
            # این توسط play_handler مدیریت میشه
            pass
        elif text == 'توقف':
            await self.control_handler.pause_song(message)
        elif text == 'ادامه':
            await self.control_handler.resume_song(message)
        elif text == 'بعدی':
            await self.control_handler.skip_song(message)
        elif text == 'اتمام':
            await self.control_handler.stop_song(message)
        elif text == 'لیست پخش':
            await self.control_handler.show_queue(message)
    
    async def send_welcome(self, message: Message):
        """ارسال پیام خوش‌آمدگویی"""
        
        # متن پیام
        welcome_text = """
🎵 **به ربات موزیک پلیر خوش آمدید!**

من یک ربات قدرتمند برای پخش موسیقی در گروه‌های تلگرام هستم.

✨ **قابلیت‌ها:**
• پخش از یوتیوب، اسپاتیفای و ساندکلاد
• پخش با لینک مستقیم
• مدیریت صف پخش
• کنترل کامل با دکمه‌های شیشه‌ای
• پخش دسته‌جمعی با ریپلای

📌 **دستورات اصلی:**
• `پخش [نام موزیک]` - جستجو و پخش خودکار
• `پخش لینک [لینک]` - پخش با لینک
• `پخش یوتیوب [نام]` - جستجو در یوتیوب
• `پخش اسپاتیفای [نام]` - جستجو در اسپاتیفای

🎮 **کنترل پخش:**
• `توقف` - مکث پخش
• `ادامه` - ادامه پخش
• `بعدی` - آهنگ بعدی
• `اتمام` - توقف کامل
• `لیست پخش` - نمایش صف

👑 **مدیریت:**
• `افزودن ادمین موزیک [ایدی]` - افزودن ادمین جدید

💡 **نکته:** برای پخش چند موزیک، روی پیام‌ها ریپلای بزنید و `پخش` رو بفرستید.
"""
        
        # دکمه‌ها
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ افزودن به گروه", url="https://t.me/Player_Boy_bot?startgroup=true"),
                InlineKeyboardButton("📢 کانال", url="https://t.me/your_channel"),
            ],
            [
                InlineKeyboardButton("📖 راهنما", callback_data="help"),
                InlineKeyboardButton("📊 وضعیت", callback_data="status"),
            ],
            [
                InlineKeyboardButton("🧑‍💻 پشتیبانی", url="https://t.me/your_support"),
            ]
        ])
        
        # ارسال پیام
        await message.reply_text(
            welcome_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    
    async def handle_callback(self, callback_query: CallbackQuery):
        """مدیریت دکمه‌های شیشه‌ای"""
        data = callback_query.data
        
        if data == "help":
            await callback_query.answer("📖 راهنما ارسال شد")
            await callback_query.message.reply_text(
                "📖 **راهنمای کامل ربات:**\n\n"
                "**دستورات پخش:**\n"
                "• `پخش [نام]` - جستجو در همه پلتفرم‌ها\n"
                "• `پخش یوتیوب [نام]` - فقط یوتیوب\n"
                "• `پخش اسپاتیفای [نام]` - فقط اسپاتیفای\n"
                "• `پخش لینک [لینک]` - پخش مستقیم لینک\n\n"
                "**کنترل پخش:**\n"
                "• `توقف` - مکث\n"
                "• `ادامه` - ادامه\n"
                "• `بعدی` - آهنگ بعدی\n"
                "• `اتمام` - توقف کامل\n\n"
                "**مدیریت:**\n"
                "• `افزودن ادمین موزیک [ایدی]` - افزودن ادمین\n"
                "• `حذف ادمین موزیک [ایدی]` - حذف ادمین\n"
                "• `لیست ادمین‌ها` - نمایش ادمین‌ها"
            )
        
        elif data == "status":
            await callback_query.answer("📊 وضعیت ربات")
            await callback_query.message.reply_text(
                "📊 **وضعیت ربات:**\n\n"
                "✅ **وضعیت:** آنلاین\n"
                "🎵 **در حال پخش:** -"
            )
        
        else:
            # هندل کردن دکمه‌های کنترلی
            await self.control_handler.handle_callback(callback_query)

if __name__ == "__main__":
    bot = MusicBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("⏹️ ربات با دستور کاربر متوقف شد")
        asyncio.run(bot.stop())
    except Exception as e:
        logger.error(f"❌ خطا: {e}")