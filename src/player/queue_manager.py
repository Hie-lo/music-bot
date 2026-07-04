from typing import List, Dict, Optional
import asyncio
from config import Config
import logging

logger = logging.getLogger(__name__)

class QueueManager:
    """مدیریت صف پخش"""
    
    def __init__(self):
        self.queues: Dict[int, List[Dict]] = {}
        self.current_song: Dict[int, Dict] = {}
        self.is_playing: Dict[int, bool] = {}
        self.is_paused: Dict[int, bool] = {}
        self.lock = asyncio.Lock()
    
    def get_queue(self, chat_id: int) -> List[Dict]:
        """گرفتن صف یک گروه"""
        if chat_id not in self.queues:
            self.queues[chat_id] = []
        return self.queues[chat_id]
    
    async def add_to_queue(self, chat_id: int, song: Dict) -> int:
        """اضافه کردن آهنگ به صف"""
        async with self.lock:
            queue = self.get_queue(chat_id)
            
            # اگه صف خالیه و چیزی در حال پخش نیست، مستقیماً پخش کن
            if not queue and not self.is_playing.get(chat_id, False):
                self.current_song[chat_id] = song
                self.is_playing[chat_id] = True
                self.is_paused[chat_id] = False
                return 0  # موقعیت ۰ = در حال پخش
            
            # در غیر این صورت به صف اضافه کن
            queue.append(song)
            return len(queue)  # موقعیت در صف
    
    async def get_next_song(self, chat_id: int) -> Optional[Dict]:
        """گرفتن آهنگ بعدی از صف"""
        async with self.lock:
            queue = self.get_queue(chat_id)
            
            if queue:
                next_song = queue.pop(0)
                self.current_song[chat_id] = next_song
                self.is_playing[chat_id] = True
                self.is_paused[chat_id] = False
                return next_song
            
            # اگه صف خالیه
            self.current_song[chat_id] = None
            self.is_playing[chat_id] = False
            self.is_paused[chat_id] = False
            return None
    
    async def clear_queue(self, chat_id: int):
        """پاک کردن صف"""
        async with self.lock:
            if chat_id in self.queues:
                self.queues[chat_id] = []
            self.current_song[chat_id] = None
            self.is_playing[chat_id] = False
            self.is_paused[chat_id] = False
    
    async def skip_song(self, chat_id: int) -> Optional[Dict]:
        """رد شدن از آهنگ فعلی و رفتن به آهنگ بعدی"""
        return await self.get_next_song(chat_id)
    
    def get_queue_info(self, chat_id: int, limit: int = 10) -> str:
        """گرفتن اطلاعات صف به صورت متن"""
        queue = self.get_queue(chat_id)
        current = self.current_song.get(chat_id)
        
        if not current and not queue:
            return "📋 لیست پخش خالی است!"
        
        text = "📋 **لیست پخش:**\n\n"
        
        # آهنگ در حال پخش
        if current:
            text += f"🎵 **در حال پخش:**\n"
            text += f"└ {current.get('title', 'Unknown')}\n"
            if current.get('artist'):
                text += f"  └ {current.get('artist')}\n"
            text += f"  └ ⏱️ {self._format_duration(current.get('duration', 0))}\n\n"
        
        # آهنگ‌های صف
        if queue:
            text += f"⏳ **صف پخش ({len(queue)} آهنگ):**\n"
            for i, song in enumerate(queue[:limit], 1):
                text += f"{i}. {song.get('title', 'Unknown')}"
                if song.get('artist'):
                    text += f" - {song.get('artist')}"
                text += f" ({self._format_duration(song.get('duration', 0))})\n"
            
            if len(queue) > limit:
                text += f"\n... و {len(queue) - limit} آهنگ دیگر"
        
        return text
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """تبدیل ثانیه به فرمت دقیقه:ثانیه"""
        if not seconds:
            return "0:00"
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"