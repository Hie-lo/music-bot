from pyrogram import Client
from pytgcalls import PyTgCalls
from typing import Optional, Dict
from .queue_manager import QueueManager
import logging

logger = logging.getLogger(__name__)

class MusicPlayer:
    """موتور اصلی پخش موسیقی"""
    
    def __init__(self, app: Client):
        self.app = app
        self.queue_manager = QueueManager()
        self.current_call: Dict[int, bool] = {}
        self.pytgcalls = None
        
    async def start(self):
        """شروع pytgcalls"""
        try:
            self.pytgcalls = PyTgCalls(self.app)
            await self.pytgcalls.start()
            logger.info("✅ Pytgcalls راه‌اندازی شد")
            return True
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی pytgcalls: {e}")
            return False
    
    async def join_call(self, chat_id: int):
        """پیوستن به کال صوتی"""
        try:
            if chat_id not in self.current_call or not self.current_call[chat_id]:
                await self.pytgcalls.join_group_call(chat_id)
                self.current_call[chat_id] = True
                logger.info(f"✅ به کال گروه {chat_id} پیوست")
            return True
        except Exception as e:
            logger.error(f"❌ خطا در پیوستن به کال {chat_id}: {e}")
            return False
    
    async def leave_call(self, chat_id: int):
        """خروج از کال صوتی"""
        try:
            if chat_id in self.current_call and self.current_call[chat_id]:
                await self.pytgcalls.leave_group_call(chat_id)
                self.current_call[chat_id] = False
                await self.queue_manager.clear_queue(chat_id)
                logger.info(f"✅ از کال گروه {chat_id} خارج شد")
            return True
        except Exception as e:
            logger.error(f"❌ خطا در خروج از کال {chat_id}: {e}")
            return False
    
    async def play_song(self, chat_id: int, song_url: str, song_info: Dict):
        """پخش یک آهنگ"""
        try:
            # اگه در کال نیستیم، بپیوندیم
            if chat_id not in self.current_call or not self.current_call[chat_id]:
                await self.join_call(chat_id)
            
            # ذخیره اطلاعات آهنگ در صف
            position = await self.queue_manager.add_to_queue(chat_id, song_info)
            
            # اگه موقعیت 0 باشه (همون آهنگ در حال پخش)
            if position == 0:
                # پخش آهنگ
                await self.pytgcalls.change_stream(chat_id, song_url)
                logger.info(f"🎵 در حال پخش: {song_info.get('title')} در گروه {chat_id}")
            else:
                logger.info(f"🎵 آهنگ به صف اضافه شد: {song_info.get('title')} (موقعیت {position})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در پخش آهنگ: {e}")
            return False
    
    async def pause_song(self, chat_id: int):
        """مکث کردن پخش"""
        try:
            if chat_id in self.current_call and self.current_call[chat_id]:
                await self.pytgcalls.pause_stream(chat_id)
                self.queue_manager.is_paused[chat_id] = True
                logger.info(f"⏸️ پخش متوقف شد در گروه {chat_id}")
                return True
        except Exception as e:
            logger.error(f"❌ خطا در توقف پخش: {e}")
            return False
    
    async def resume_song(self, chat_id: int):
        """ادامه پخش"""
        try:
            if chat_id in self.current_call and self.current_call[chat_id]:
                await self.pytgcalls.resume_stream(chat_id)
                self.queue_manager.is_paused[chat_id] = False
                logger.info(f"▶️ پخش ادامه یافت در گروه {chat_id}")
                return True
        except Exception as e:
            logger.error(f"❌ خطا در ادامه پخش: {e}")
            return False
    
    async def skip_song(self, chat_id: int):
        """رد شدن از آهنگ فعلی"""
        try:
            # گرفتن آهنگ بعدی
            next_song = await self.queue_manager.get_next_song(chat_id)
            
            if next_song:
                # گرفتن لینک صوتی آهنگ بعدی
                from search import SearchManager
                search_manager = SearchManager()
                
                audio_url = await search_manager.get_audio_url(
                    next_song.get('url'), 
                    next_song.get('platform', 'youtube')
                )
                
                if audio_url:
                    await self.pytgcalls.change_stream(chat_id, audio_url)
                    logger.info(f"⏭️ پخش آهنگ بعدی: {next_song.get('title')}")
                    return next_song
                else:
                    # اگه نتونست لینک بگیره، دوباره تلاش کن
                    return await self.skip_song(chat_id)
            else:
                # اگه آهنگ بعدی نبود، از کال خارج شو
                await self.leave_call(chat_id)
                return None
                
        except Exception as e:
            logger.error(f"❌ خطا در رد شدن از آهنگ: {e}")
            return None
    
    async def stop_song(self, chat_id: int):
        """توقف کامل پخش"""
        try:
            await self.leave_call(chat_id)
            await self.queue_manager.clear_queue(chat_id)
            logger.info(f"⏹️ پخش متوقف شد در گروه {chat_id}")
            return True
        except Exception as e:
            logger.error(f"❌ خطا در توقف پخش: {e}")
            return False
    
    async def get_current_song(self, chat_id: int) -> Optional[Dict]:
        """گرفتن آهنگ در حال پخش"""
        return self.queue_manager.current_song.get(chat_id)
    
    async def get_queue(self, chat_id: int) -> list:
        """گرفتن لیست پخش"""
        return self.queue_manager.get_queue(chat_id)