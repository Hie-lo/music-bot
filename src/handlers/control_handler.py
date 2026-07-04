from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from player import MusicPlayer
from search import SearchManager
import logging

logger = logging.getLogger(__name__)

class ControlHandler:
    def __init__(self, app: Client):
        self.app = app
        self.music_player = MusicPlayer(app)
        self.search_manager = SearchManager()
    
    def register_handlers(self):
        """ثبت هندلرهای کنترلی"""
        
        # دستورات متنی
        @self.app.on_message(filters.command(["توقف", "pause"]) & filters.group)
        async def pause_command(client, message: Message):
            await self.pause_song(message)
        
        @self.app.on_message(filters.command(["ادامه", "resume"]) & filters.group)
        async def resume_command(client, message: Message):
            await self.resume_song(message)
        
        @self.app.on_message(filters.command(["بعدی", "skip"]) & filters.group)
        async def skip_command(client, message: Message):
            await self.skip_song(message)
        
        @self.app.on_message(filters.command(["اتمام", "stop"]) & filters.group)
        async def stop_command(client, message: Message):
            await self.stop_song(message)
        
        @self.app.on_message(filters.command(["لیست پخش", "queue"]) & filters.group)
        async def queue_command(client, message: Message):
            await self.show_queue(message)
        
        # دکمه‌های شیشه‌ای (Callback)
        @self.app.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            await self.handle_callback(callback_query)
    
    async def pause_song(self, message: Message):
        """مکث کردن پخش"""
        try:
            chat_id = message.chat.id
            success = await self.music_player.pause_song(chat_id)
            
            if success:
                await message.reply_text("⏸️ پخش متوقف شد.")
            else:
                await message.reply_text("❌ هیچ موزیکی در حال پخش نیست!")
        except Exception as e:
            logger.error(f"خطا در توقف پخش: {e}")
            await message.reply_text("❌ خطایی رخ داد!")
    
    async def resume_song(self, message: Message):
        """ادامه پخش"""
        try:
            chat_id = message.chat.id
            success = await self.music_player.resume_song(chat_id)
            
            if success:
                await message.reply_text("▶️ پخش ادامه یافت.")
            else:
                await message.reply_text("❌ هیچ موزیکی در حالت توقف نیست!")
        except Exception as e:
            logger.error(f"خطا در ادامه پخش: {e}")
            await message.reply_text("❌ خطایی رخ داد!")
    
    async def skip_song(self, message: Message):
        """رد شدن از آهنگ فعلی"""
        try:
            chat_id = message.chat.id
            
            # چک کردن اینکه کاربر مجاز هست یا نه
            if not await self.is_authorized(message):
                await message.reply_text("❌ شما دسترسی به این آهنگ ندارید!")
                return
            
            next_song = await self.music_player.skip_song(chat_id)
            
            if next_song:
                await message.reply_text(
                    f"⏭️ **آهنگ بعدی:**\n"
                    f"🎵 {next_song.get('title', 'Unknown')}\n"
                    f"🎤 {next_song.get('artist', 'Unknown Artist')}"
                )
            else:
                await message.reply_text("⏹️ لیست پخش به پایان رسید.")
        except Exception as e:
            logger.error(f"خطا در رد شدن از آهنگ: {e}")
            await message.reply_text("❌ خطایی رخ داد!")
    
    async def stop_song(self, message: Message):
        """توقف کامل پخش"""
        try:
            chat_id = message.chat.id
            
            # چک کردن اینکه کاربر مجاز هست یا نه
            if not await self.is_authorized(message):
                await message.reply_text("❌ شما دسترسی به این آهنگ ندارید!")
                return
            
            success = await self.music_player.stop_song(chat_id)
            
            if success:
                await message.reply_text("⏹️ پخش متوقف شد و از کال خارج شدم.")
            else:
                await message.reply_text("❌ خطا در توقف پخش!")
        except Exception as e:
            logger.error(f"خطا در توقف پخش: {e}")
            await message.reply_text("❌ خطایی رخ داد!")
    
    async def show_queue(self, message: Message):
        """نمایش لیست پخش"""
        try:
            chat_id = message.chat.id
            queue_info = self.music_player.queue_manager.get_queue_info(chat_id)
            await message.reply_text(queue_info)
        except Exception as e:
            logger.error(f"خطا در نمایش لیست پخش: {e}")
            await message.reply_text("❌ خطایی رخ داد!")
    
    async def handle_callback(self, callback_query: CallbackQuery):
        """مدیریت دکمه‌های شیشه‌ای"""
        try:
            data = callback_query.data
            chat_id = callback_query.message.chat.id
            user_id = callback_query.from_user.id
            
            # پردازش دکمه‌ها
            if data.startswith("pause"):
                await self.music_player.pause_song(chat_id)
                await callback_query.answer("⏸️ پخش متوقف شد")
            
            elif data.startswith("resume"):
                await self.music_player.resume_song(chat_id)
                await callback_query.answer("▶️ پخش ادامه یافت")
            
            elif data.startswith("skip"):
                # چک کردن دسترسی
                if await self.is_authorized_callback(callback_query):
                    next_song = await self.music_player.skip_song(chat_id)
                    if next_song:
                        await callback_query.answer(f"⏭️ در حال پخش: {next_song.get('title')}")
                    else:
                        await callback_query.answer("⏹️ لیست پخش به پایان رسید")
                else:
                    await callback_query.answer("❌ شما دسترسی ندارید!", show_alert=True)
            
            elif data.startswith("stop"):
                if await self.is_authorized_callback(callback_query):
                    await self.music_player.stop_song(chat_id)
                    await callback_query.answer("⏹️ پخش متوقف شد")
                else:
                    await callback_query.answer("❌ شما دسترسی ندارید!", show_alert=True)
            
            elif data.startswith("queue"):
                queue_info = self.music_player.queue_manager.get_queue_info(chat_id)
                await callback_query.answer("📋 لیست پخش ارسال شد")
                await callback_query.message.reply_text(queue_info)
            
            elif data.startswith("repeat"):
                # قابلیت تکرار
                await callback_query.answer("🔄 حالت تکرار فعال شد", show_alert=True)
            
            # ویرایش پیام (اختیاری - می‌تونه پیام رو آپدیت کنه)
            # await callback_query.message.edit_text("...")
            
        except Exception as e:
            logger.error(f"خطا در پردازش callback: {e}")
            await callback_query.answer("❌ خطایی رخ داد!", show_alert=True)
    
    async def is_authorized(self, message: Message) -> bool:
        """چک کردن دسترسی کاربر به کنترل آهنگ"""
        # اینجا می‌تونی منطق دسترسی رو پیاده‌سازی کنی
        # مثلاً ادمین‌ها و کسی که آهنگ رو اضافه کرده
        from handlers.admin_handler import AdminHandler
        admin_handler = AdminHandler(self.app)
        return await admin_handler.is_admin(message.from_user.id)
    
    async def is_authorized_callback(self, callback_query: CallbackQuery) -> bool:
        """چک کردن دسترسی کاربر در callback"""
        from handlers.admin_handler import AdminHandler
        admin_handler = AdminHandler(self.app)
        return await admin_handler.is_admin(callback_query.from_user.id)