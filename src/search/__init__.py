from .youtube import YouTubeSearch
from .spotify import SpotifySearch
from .soundcloud import SoundCloudSearch
from .base import SearchResult
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class SearchManager:
    """مدیریت جستجو در همه پلتفرم‌ها"""
    
    def __init__(self):
        self.youtube = YouTubeSearch()
        self.spotify = SpotifySearch()
        self.soundcloud = SoundCloudSearch()
        self.search_engines = {
            'youtube': self.youtube,
            'spotify': self.spotify,
            'soundcloud': self.soundcloud,
            'default': self.youtube  # پیش‌فرض
        }
    
    async def search(self, query: str, platform: str = 'default', limit: int = 5) -> List[SearchResult]:
        """جستجو در پلتفرم مشخص شده"""
        engine = self.search_engines.get(platform.lower(), self.search_engines['default'])
        logger.info(f"🔍 جستجو در {platform}: {query}")
        return await engine.search(query, limit)
    
    async def get_audio_url(self, url: str, platform: str = 'default') -> Optional[str]:
        """گرفتن لینک صوتی از هر پلتفرم"""
        engine = self.search_engines.get(platform.lower(), self.search_engines['default'])
        return await engine.get_audio_url(url)
    
    async def search_with_fallback(self, query: str, preferred_platform: str = None, limit: int = 5) -> List[SearchResult]:
        """جستجو با fallback - اگه پلتفرم مورد نظر کار نکرد، بره سراغ بعدی"""
        platforms = ['spotify', 'youtube', 'soundcloud']
        
        # اگه پلتفرم ترجیحی مشخص شده، اول اون رو امتحان کن
        if preferred_platform and preferred_platform.lower() in platforms:
            platforms.remove(preferred_platform.lower())
            platforms.insert(0, preferred_platform.lower())
        
        for platform in platforms:
            engine = self.search_engines.get(platform)
            if not engine:
                continue
            
            try:
                results = await engine.search(query, limit)
                if results:
                    logger.info(f"✅ نتایج پیدا شد در {platform}")
                    return results
            except Exception as e:
                logger.warning(f"⚠️ خطا در جستجوی {platform}: {e}")
                continue
        
        return []