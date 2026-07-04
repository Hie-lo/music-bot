from pyrogram import Client, filters
from pyrogram.types import Message
from search import SearchManager
from player import MusicPlayer
import logging
import re

logger = logging.getLogger(__name__)

class PlayHandler:
    def __init__(self, app: Client):
        self.app = app
        self.search_manager = SearchManager()
        self.music_player = MusicPlayer(app)
    
    def register_handlers(self):
        """ثبت هندلرهای پخش"""
        app = self.app
        
        # هندلر اصلی پخش با filters.text
        @app.on_message(filters.text & filters.group)
        async def play_command(client, message: Message):
            text = message.text or ""
            
            # دستورات پخش با ریپلای
            if text == "پخش" and message.reply_to_message:
                await self.handle_play_reply(message)
            
            # پخش با اسم
            elif text.startswith("پخش "):
                query = text[3:].strip()
                await self.handle_play(message, query)
            
            # پخش لینک
            elif text.startswith("پخش لینک "):
                link = text[8:].strip()
                await self.handle_play_link(message, link)
            
            # پخش در پلتفرم خاص
            elif re.match(r'^پخش (یوتیوب|اسپاتیفای|ساندکلاد) .+', text):
                parts = text.split(" ", 2)
                if len(parts) >= 3:
                    platform = parts[1]
                    query = parts[2]
                    await self.handle_play_platform(message, platform, query)
        
        logger.info("✅ هندلرهای پخش ثبت شدند")
    
    async def handle_play(self, message: Message, query: str):
        """مدیریت پخش با سرچ عمومی"""
        try:
            if not query:
                await message.reply_text("❌ لطفاً نام موزیک را وارد کنید!")
                return
            
            # جستجو با fallback
            results = await self.search_manager.search_with_fallback(query)
            
            if not results:
                await message.reply_text("❌ موزیک مورد نظر پیدا نشد!")
                return
            
            # گرفتن بهترین نتیجه
            song = results[0]
            
            # گرفتن لینک صوتی
            audio_url = await self.search_manager.get_audio_url(song.url, song.platform)
            if not audio_url:
                await message.reply_text("❌ خطا در دریافت لینک پخش!")
                return
            
            # پخش آهنگ
            success = await self.music_player.play_song(
                message.chat.id,
                audio_url,
                song.to_dict()
            )
            
            if success:
                # ارسال پیام اطلاعات
                await self._send_play_message(message, song)
            else:
                await message.reply_text("❌ خطا در پخش موزیک!")
                
        except Exception as e:
            logger.error(f"خطا در پخش: {e}")
            await message.reply_text("❌ خطایی رخ داد! لطفاً دوباره تلاش کنید.")
    
    async def handle_play_link(self, message: Message, link: str):
        """مدیریت پخش با لینک"""
        try:
            if not link:
                await message.reply_text("❌ لطفاً لینک را وارد کنید!")
                return
            
            # تشخیص پلتفرم از لینک
            platform = self._detect_platform(link)
            
            # گرفتن اطلاعات آهنگ از لینک
            audio_url = await self.search_manager.get_audio_url(link, platform)
            if not audio_url:
                await message.reply_text("❌ خطا در دریافت لینک پخش!")
                return
            
            # ساخت اطلاعات آهنگ
            song_info = {
                'title': f"🎵 {link[:30]}...",
                'url': link,
                'duration': 0,
                'artist': 'Unknown',
                'platform': platform,
                'thumbnail': ''
            }
            
            # پخش آهنگ
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
            logger.error(f"خطا در پخش لینک: {e}")
            await message.reply_text("❌ خطایی رخ داد! لطفاً دوباره تلاش کنید.")
    
    async def handle_play_platform(self, message: Message, platform: str, query: str):
        """مدیریت پخش در پلتفرم مشخص"""
        try:
            # جستجو در پلتفرم مشخص
            results = await self.search_manager.search(query, platform)
            
            if not results:
                # اگه پلتفرم مورد نظر نتیجه نداد، fallback
                await message.reply_text(f"⚠️ در {platform} پیدا نشد، جستجو در یوتیوب...")
                results = await self.search_manager.search(query, 'youtube')
            
            if not results:
                await message.reply_text("❌ موزیک مورد نظر پیدا نشد!")
                return
            
            song = results[0]
            
            # گرفتن لینک صوتی
            audio_url = await self.search_manager.get_audio_url(song.url, song.platform)
            if not audio_url:
                await message.reply_text("❌ خطا در دریافت لینک پخش!")
                return
            
            # پخش آهنگ
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
            logger.error(f"خطا در پخش پلتفرم: {e}")
            await message.reply_text("❌ خطایی رخ داد! لطفاً دوباره تلاش کنید.")
    
    async def handle_play_reply(self, message: Message):
        """مدیریت پخش با ریپلای"""
        try:
            msg = message.reply_to_message
            if msg and msg.text:
                # جستجو با متن پیام
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
            logger.error(f"خطا در پخش ریپلای: {e}")
            await message.reply_text("❌ خطایی رخ داد!")
    
    async def _send_play_message(self, message: Message, song_info):
        """ارسال پیام با اطلاعات آهنگ"""
        from utils import create_play_message
        
        # ساخت متن و دکمه‌ها
        text, keyboard = create_play_message(song_info, message.chat.id)
        
        await message.reply_text(
            text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    
    @staticmethod
    def _detect_platform(link: str) -> str:
        """تشخیص پلتفرم از لینک"""
        link_lower = link.lower()
        if 'youtube.com' in link_lower or 'youtu.be' in link_lower:
            return 'youtube'
        elif 'spotify.com' in link_lower:
            return 'spotify'
        elif 'soundcloud.com' in link_lower:
            return 'soundcloud'
        else:
            return 'default'