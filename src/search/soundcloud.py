import yt_dlp
from typing import List, Optional
from .base import BaseSearch, SearchResult
import logging

logger = logging.getLogger(__name__)

class SoundCloudSearch(BaseSearch):
    """موتور جستجوی ساندکلاد"""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
    
    async def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """جستجو در ساندکلاد"""
        try:
            search_query = f"scsearch{limit}:{query}"
            
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                if not info or 'entries' not in info:
                    return []
                
                results = []
                for entry in info['entries']:
                    if not entry:
                        continue
                    
                    result = SearchResult(
                        title=entry.get('title', 'Unknown'),
                        url=entry.get('url', ''),
                        duration=entry.get('duration', 0),
                        artist=entry.get('uploader', 'Unknown Artist'),
                        thumbnail=entry.get('thumbnail', ''),
                        platform='soundcloud'
                    )
                    results.append(result)
                
                return results[:limit]
                
        except Exception as e:
            logger.error(f"خطا در جستجوی ساندکلاد: {e}")
            return []
    
    async def get_audio_url(self, url: str) -> Optional[str]:
        """گرفتن لینک مستقیم صوتی از ساندکلاد"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'url' in info:
                    return info['url']
                
                return None
                
        except Exception as e:
            logger.error(f"خطا در گرفتن لینک صوتی ساندکلاد: {e}")
            return None