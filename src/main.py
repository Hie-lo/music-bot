import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from handlers.play_handler import PlayHandler
from handlers.admin_handler import AdminHandler
from handlers.control_handler import ControlHandler

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
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="src/handlers")
        )
        
        # نمونه‌سازی هندلرها
        self.play_handler = PlayHandler(self.app)
        self.admin_handler = AdminHandler(self.app)
        self.control_handler = ControlHandler(self.app)
    
    async def start(self):
        """شروع ربات"""
        logger.info("🚀 ربات موزیک پلیر در حال راه‌اندازی...")
        
        # ثبت دستورات
        @self.app.on_message(filters.command(["start", "help"]))
        async def start_command(client, message: Message):
            await message.reply_text(
                "🎵 **ربات موزیک پلیر پیشرفته**\n\n"
                "📌 **دستورات اصلی:**\n"
                "• `پخش [نام موزیک]` - جستجو و پخش خودکار\n"
                "• `پخش یوتیوب [نام]` - جستجو در یوتیوب\n"
                "• `پخش اسپاتیفای [نام]` - جستجو در اسپاتیفای\n"
                "• `پخش ساندکلاد [نام]` - جستجو در ساندکلاد\n"
                "• `پخش لینک [لینک]` - پخش با لینک\n\n"
                "🎯 **پخش دسته‌جمعی:**\n"
                "• روی چند پیام ریپلای کن و `پخش` رو بفرست\n\n"
                "🎮 **کنترل پخش:**\n"
                "• ⏸️ توقف | ▶️ ادامه | ⏭️ بعدی | ⏹️ اتمام\n"
                "• 🔁 تکرار | 📋 لیست پخش\n\n"
                "👑 **مدیریت:**\n"
                "• `افزودن ادمین موزیک [ایدی]` - افزودن ادمین جدید\n"
                "• `حذف ادمین موزیک [ایدی]` - حذف ادمین\n\n"
                "💡 **نکته:** اگه اسپاتیفای تنظیم نشده باشه، ربات خودکار از یوتیوب استفاده می‌کنه.",
                disable_web_page_preview=True
            )
        
        # ثبت هندلرها
        self.play_handler.register_handlers()
        self.admin_handler.register_handlers()
        self.control_handler.register_handlers()
        
        # راه‌اندازی ربات
        logger.info("✅ ربات آماده کار است!")
        await self.app.start()
        logger.info(f"🎵 ربات با نام @{(await self.app.get_me()).username} فعال شد")
        
        # نگه‌داشتن ربات در حالت اجرا
        await asyncio.Event().wait()
    
    async def stop(self):
        """توقف ربات"""
        logger.info("🛑 ربات در حال توقف...")
        await self.app.stop()
        logger.info("✅ ربات متوقف شد")

if __name__ == "__main__":
    bot = MusicBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("⏹️ ربات با دستور کاربر متوقف شد")
        asyncio.run(bot.stop())
    except Exception as e:
        logger.error(f"❌ خطا: {e}")