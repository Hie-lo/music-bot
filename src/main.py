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
from search import SearchManager
from player import MusicPlayer
import re
import json

# ایجاد پوشه logs
os.makedirs('logs', exist_ok=True)

# تنظیم لاگ
logging.basicConfig(
    level=logging.DEBUG,  # تغییر به DEBUG برای دیباگ کامل
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# نمونه‌سازی
search_manager = SearchManager()
music_player = None

class MusicBot:
    def __init__(self):
        self.app = Client(
            "musicbot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        global music_player
        music_player = MusicPlayer(self.app)
        self.music_player = music_player
        self.search_manager = search_manager
    
    async def start(self):
        logger.info("🚀 ربات موزیک پلیر در حال راه‌اندازی...")
        
        # ========== ثبت هندلرها ==========
        self.register_handlers()
        
        logger.info("✅ ربات آماده کار است!")
        await self.app.start()
        
        bot_info = await self.app.get_me()
        logger.info(f"🎵 ربات با نام @{bot_info.username} فعال شد")
        
        await asyncio.Event().wait()
    
    def register_handlers(self):
        """ثبت همه هندلرها با روش ساده"""
        
        # ===== 1. هندلر عمومی برای تمام پیام‌های متنی (برای دیباگ) =====
        @self.app.on_message(filters.text)
        async def all_messages(client, message: Message):
            logger.info(f"📩 پیام جدید: {message.text} | از: {message.from_user.id} | گروه: {message.chat.id}")
            
            # اگه پیام در گروه نیست، نادیده بگیر
            if not message.chat.type in ["group", "supergroup"]:
                await message.reply_text("🤖 این ربات فقط در گروه‌ها کار می‌کند!")
                return
            
            text = message.text or ""
            
            # ===== دستور start =====
            if text.startswith("/start") or text.startswith("/help"):
                await self.send_welcome(message)
                return
            
            # ===== دستور پخش =====
            if text.startswith("پخش "):
                query = text[3:].strip()
                await self.handle_play(message, query)
                return
            
            # ===== دستور پخش لینک =====
            if text.startswith("پخش لینک "):
                link = text[8:].strip()
                await self.handle_play_link(message, link)
                return
            
            # ===== دستور پخش در پلتفرم خاص =====
            platform_match = re.match(r'^پخش (یوتیوب|اسپاتیفای|ساندکلاد) (.+)$', text)
            if platform_match:
                platform = platform_match.group(1)
                query = platform_match.group(2)
                await self.handle_play_platform(message, platform, query)
                return
            
            # ===== دستورات کنترل =====
            if text == "توقف":
                await self.pause_song(message)
                return
            if text == "ادامه":
                await self.resume_song(message)
                return
            if text == "بعدی":
                await self.skip_song(message)
                return
            if text == "اتمام":
                await self.stop_song(message)
                return
            if text == "لیست پخش":
                await self.show_queue(message)
                return
            
            # ===== دستورات مدیریت =====
            if text.startswith("افزودن ادمین موزیک "):
                await self.add_admin(message)
                return
            if text.startswith("حذف ادمین موزیک "):
                await self.remove_admin(message)
                return
            if text == "لیست ادمین‌ها":
                await self.list_admins(message)
                return
            
            # ===== دستور پخش با ریپلای =====
            if text == "پخش" and message.reply_to_message:
                await self.handle_play_reply(message)
                return
            
            # ===== اگه هیچکدوم نبود =====
            # برای دیباگ: به کاربر بگو که دستور پشتیبانی نمیشه
            # (در حالت عادی این خط رو کامنت کن)
            # await message.reply_text("❌ دستور نامعتبر! برای راهنما /start رو بفرست.")
        
        # ===== 2. هندلر دکمه‌های شیشه‌ای =====
        @self.app.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            logger.info(f"🔘 دکمه فشرده شد: {callback_query.data}")
            await self.handle_callback(callback_query)
        
        logger.info("✅ همه هندلرها ثبت شدند")
    
    # ========== توابع اصلی ==========
    
    async def handle_play(self, message: Message, query: str):
        """پخش با سرچ"""
        try:
            logger.info(f"🎵 درخواست پخش: {query}")
            
            if not query:
                await message.reply_text("❌ لطفاً نام موزیک را وارد کنید!")
                return
            
            msg = await message.reply_text(f"🔍 در حال جستجوی: {query}")
            
            results = await self.search_manager.search_with_fallback(query)
            
            if not results:
                await msg.edit_text("❌ موزیک مورد نظر پیدا نشد!")
                return
            
            song = results[0]
            logger.info(f"✅ پیدا شد: {song.title} - {song.platform}")
            
            audio_url = await self.search_manager.get_audio_url(song.url, song.platform)
            
            if not audio_url:
                await msg.edit_text("❌ خطا در دریافت لینک پخش!")
                return
            
            success = await self.music_player.play_song(
                message.chat.id,
                audio_url,
                song.to_dict()
            )
            
            if success:
                await self._send_play_message(message, song)
                await msg.delete()
            else:
                await msg.edit_text("❌ خطا در پخش موزیک!")
                
        except Exception as e:
            logger.error(f"❌ خطا در پخش: {e}", exc_info=True)
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    async def handle_play_link(self, message: Message, link: str):
        """پخش با لینک"""
        try:
            logger.info(f"🔗 درخواست پخش لینک: {link}")
            
            platform = self._detect_platform(link)
            audio_url = await self.search_manager.get_audio_url(link, platform)
            
            if not audio_url:
                await message.reply_text("❌ خطا در دریافت لینک پخش!")
                return
            
            song_info = {
                'title': f"🎵 لینک پخش",
                'url': link,
                'duration': 0,
                'artist': 'Unknown',
                'platform': platform,
                'thumbnail': ''
            }
            
            success = await self.music_player.play_song(
                message.chat.id,
                audio_url,
                song_info
            )
            
            if success:
                await self._send_play_message(message, song_info)
            else:
                await message.reply_text("❌ خطا در پخش موزیک!")
                
        except Exception as e:
            logger.error(f"❌ خطا در پخش لینک: {e}", exc_info=True)
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    async def handle_play_platform(self, message: Message, platform: str, query: str):
        """پخش در پلتفرم خاص"""
        try:
            logger.info(f"🎵 درخواست پخش در {platform}: {query}")
            
            results = await self.search_manager.search(query, platform)
            
            if not results:
                await message.reply_text(f"⚠️ در {platform} پیدا نشد، جستجو در یوتیوب...")
                results = await self.search_manager.search(query, 'youtube')
            
            if not results:
                await message.reply_text("❌ موزیک مورد نظر پیدا نشد!")
                return
            
            song = results[0]
            audio_url = await self.search_manager.get_audio_url(song.url, song.platform)
            
            if not audio_url:
                await message.reply_text("❌ خطا در دریافت لینک پخش!")
                return
            
            success = await self.music_player.play_song(
                message.chat.id,
                audio_url,
                song.to_dict()
            )
            
            if success:
                await self._send_play_message(message, song)
            else:
                await message.reply_text("❌ خطا در پخش موزیک!")
                
        except Exception as e:
            logger.error(f"❌ خطا در پخش پلتفرم: {e}", exc_info=True)
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    async def handle_play_reply(self, message: Message):
        """پخش با ریپلای"""
        try:
            msg = message.reply_to_message
            if msg and msg.text:
                logger.info(f"📎 ریپلای: {msg.text}")
                results = await self.search_manager.search_with_fallback(msg.text)
                if results:
                    song = results[0]
                    audio_url = await self.search_manager.get_audio_url(song.url, song.platform)
                    if audio_url:
                        await self.music_player.play_song(
                            message.chat.id,
                            audio_url,
                            song.to_dict()
                        )
                        await self._send_play_message(message, song)
            
        except Exception as e:
            logger.error(f"❌ خطا در پخش ریپلای: {e}", exc_info=True)
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    # ========== توابع کنترل ==========
    
    async def pause_song(self, message: Message):
        try:
            success = await self.music_player.pause_song(message.chat.id)
            await message.reply_text("⏸️ پخش متوقف شد." if success else "❌ هیچ موزیکی در حال پخش نیست!")
        except Exception as e:
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    async def resume_song(self, message: Message):
        try:
            success = await self.music_player.resume_song(message.chat.id)
            await message.reply_text("▶️ پخش ادامه یافت." if success else "❌ هیچ موزیکی در حالت توقف نیست!")
        except Exception as e:
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    async def skip_song(self, message: Message):
        try:
            next_song = await self.music_player.skip_song(message.chat.id)
            if next_song:
                await message.reply_text(
                    f"⏭️ **آهنگ بعدی:**\n"
                    f"🎵 {next_song.get('title', 'Unknown')}"
                )
            else:
                await message.reply_text("⏹️ لیست پخش به پایان رسید.")
        except Exception as e:
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    async def stop_song(self, message: Message):
        try:
            success = await self.music_player.stop_song(message.chat.id)
            await message.reply_text("⏹️ پخش متوقف شد." if success else "❌ خطا در توقف پخش!")
        except Exception as e:
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    async def show_queue(self, message: Message):
        try:
            queue_info = self.music_player.queue_manager.get_queue_info(message.chat.id)
            await message.reply_text(queue_info)
        except Exception as e:
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    # ========== توابع مدیریت ==========
    
    async def add_admin(self, message: Message):
        try:
            parts = message.text.split()
            user_id = int(parts[1]) if len(parts) > 1 and not message.reply_to_message else (
                message.reply_to_message.from_user.id if message.reply_to_message else None
            )
            
            if not user_id:
                await message.reply_text("❌ دستور صحیح: `افزودن ادمین موزیک [ایدی]`")
                return
            
            admins = []
            try:
                with open(Config.ADMINS_FILE, 'r') as f:
                    data = json.load(f)
                    admins = data.get('admins', [])
            except:
                pass
            
            if user_id in admins:
                await message.reply_text(f"⚠️ کاربر `{user_id}` قبلاً ادمین است!")
                return
            
            admins.append(user_id)
            with open(Config.ADMINS_FILE, 'w') as f:
                json.dump({'admins': admins}, f, indent=2)
            
            await message.reply_text(f"✅ کاربر `{user_id}` به لیست ادمین‌ها اضافه شد.")
        except Exception as e:
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    async def remove_admin(self, message: Message):
        try:
            parts = message.text.split()
            user_id = int(parts[1]) if len(parts) > 1 and not message.reply_to_message else (
                message.reply_to_message.from_user.id if message.reply_to_message else None
            )
            
            if not user_id:
                await message.reply_text("❌ دستور صحیح: `حذف ادمین موزیک [ایدی]`")
                return
            
            import json
            admins = []
            try:
                with open(Config.ADMINS_FILE, 'r') as f:
                    data = json.load(f)
                    admins = data.get('admins', [])
            except:
                pass
            
            if user_id not in admins:
                await message.reply_text(f"⚠️ کاربر `{user_id}` ادمین نیست!")
                return
            
            admins.remove(user_id)
            with open(Config.ADMINS_FILE, 'w') as f:
                json.dump({'admins': admins}, f, indent=2)
            
            await message.reply_text(f"✅ کاربر `{user_id}` از لیست ادمین‌ها حذف شد.")
        except Exception as e:
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    async def list_admins(self, message: Message):
        try:
            import json
            admins = []
            try:
                with open(Config.ADMINS_FILE, 'r') as f:
                    data = json.load(f)
                    admins = data.get('admins', [])
            except:
                pass
            
            if not admins:
                await message.reply_text("📋 لیست ادمین‌ها خالی است!")
                return
            
            text = "👑 **لیست ادمین‌ها:**\n\n"
            for i, admin_id in enumerate(admins, 1):
                try:
                    user = await self.app.get_users(admin_id)
                    name = user.first_name or f"کاربر {admin_id}"
                    text += f"{i}. {name} (`{admin_id}`)\n"
                except:
                    text += f"{i}. کاربر با ایدی `{admin_id}`\n"
            
            await message.reply_text(text)
        except Exception as e:
            await message.reply_text(f"❌ خطا: {str(e)}")
    
    # ========== توابع کمکی ==========
    
    async def _send_play_message(self, message: Message, song_info):
        """ارسال پیام با اطلاعات آهنگ"""
        from utils import create_play_message
        text, keyboard = create_play_message(song_info, message.chat.id)
        await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)
    
    async def handle_callback(self, callback_query: CallbackQuery):
        """مدیریت دکمه‌های شیشه‌ای"""
        try:
            data = callback_query.data
            chat_id = callback_query.message.chat.id
            
            if data.startswith("pause"):
                await self.music_player.pause_song(chat_id)
                await callback_query.answer("⏸️ پخش متوقف شد")
            
            elif data.startswith("resume"):
                await self.music_player.resume_song(chat_id)
                await callback_query.answer("▶️ پخش ادامه یافت")
            
            elif data.startswith("skip"):
                next_song = await self.music_player.skip_song(chat_id)
                if next_song:
                    await callback_query.answer(f"⏭️ در حال پخش: {next_song.get('title')}")
                else:
                    await callback_query.answer("⏹️ لیست پخش به پایان رسید")
            
            elif data.startswith("stop"):
                await self.music_player.stop_song(chat_id)
                await callback_query.answer("⏹️ پخش متوقف شد")
            
            elif data.startswith("queue"):
                queue_info = self.music_player.queue_manager.get_queue_info(chat_id)
                await callback_query.answer("📋 لیست پخش ارسال شد")
                await callback_query.message.reply_text(queue_info)
            
            elif data == "help":
                await callback_query.answer("📖 راهنما")
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
                    "• `اتمام` - توقف کامل\n"
                    "• `لیست پخش` - نمایش صف"
                )
            
            elif data == "status":
                await callback_query.answer("📊 وضعیت ربات")
                await callback_query.message.reply_text(
                    "📊 **وضعیت ربات:**\n\n"
                    "✅ **وضعیت:** آنلاین\n"
                    "🎵 **در حال پخش:** -"
                )
            
        except Exception as e:
            logger.error(f"❌ خطا در callback: {e}")
            await callback_query.answer("❌ خطا!", show_alert=True)
    
    async def send_welcome(self, message: Message):
        """ارسال پیام خوش‌آمدگویی"""
        welcome_text = """
🎵 **به ربات موزیک پلیر خوش آمدید!**

من یک ربات قدرتمند برای پخش موسیقی در گروه‌های تلگرام هستم.

📌 **دستورات اصلی:**
• `پخش [نام موزیک]` - جستجو و پخش خودکار
• `پخش لینک [لینک]` - پخش با لینک
• `پخش یوتیوب [نام]` - جستجو در یوتیوب
• `پخش اسپاتیفای [نام]` - جستجو در اسپاتیفای

🎮 **کنترل پخش:**
• `توقف` - مکث
• `ادامه` - ادامه
• `بعدی` - آهنگ بعدی
• `اتمام` - توقف کامل
• `لیست پخش` - نمایش صف
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ افزودن به گروه", url="https://t.me/Player_Boy_bot?startgroup=true"),
            ],
            [
                InlineKeyboardButton("📖 راهنما", callback_data="help"),
                InlineKeyboardButton("📊 وضعیت", callback_data="status"),
            ]
        ])
        
        await message.reply_text(welcome_text, reply_markup=keyboard)
    
    def _detect_platform(self, link: str) -> str:
        if 'youtube.com' in link or 'youtu.be' in link:
            return 'youtube'
        elif 'spotify.com' in link:
            return 'spotify'
        elif 'soundcloud.com' in link:
            return 'soundcloud'
        return 'default'

if __name__ == "__main__":
    bot = MusicBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("⏹️ ربات متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطا: {e}", exc_info=True)