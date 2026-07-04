from abc import ABC, abstractmethod
from typing import Optional, Dict, List

class SearchResult:
    """کلاس برای ذخیره نتایج جستجو"""
    def __init__(self, title: str, url: str, duration: int, 
                 artist: str = "", thumbnail: str = "", 
                 platform: str = "unknown"):
        self.title = title
        self.url = url
        self.duration = duration
        self.artist = artist
        self.thumbnail = thumbnail
        self.platform = platform
    
    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "duration": self.duration,
            "artist": self.artist,
            "thumbnail": self.thumbnail,
            "platform": self.platform
        }

class BaseSearch(ABC):
    """کلاس پایه برای موتورهای جستجو"""
    
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """جستجو و برگرداندن نتایج"""
        pass
    
    @abstractmethod
    async def get_audio_url(self, url: str) -> Optional[str]:
        """گرفتن لینک مستقیم صوتی از لینک ویدیو/آهنگ"""
        pass