import yt_dlp
from typing import List, Optional
from .base import BaseSearch, SearchResult
import logging

logger = logging.getLogger(__name__)

class YouTubeSearch(BaseSearch):
    """موتور جستجوی یوتیوب"""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }
    
    async def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """جستجو در یوتیوب"""
        try:
            search_query = f"ytsearch{limit}:{query}"
            
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                if not info or 'entries' not in info:
                    return []
                
                results = []
                for entry in info['entries']:
                    if not entry:
                        continue
                    
                    duration = entry.get('duration', 0)
                    # فقط آهنگ‌های کمتر از ۱ ساعت
                    if duration and duration > 3600:
                        continue
                    
                    result = SearchResult(
                        title=entry.get('title', 'Unknown'),
                        url=entry.get('url') or f"https://youtube.com/watch?v={entry.get('id', '')}",
                        duration=duration or 0,
                        artist=entry.get('uploader', 'Unknown Artist'),
                        thumbnail=entry.get('thumbnail', ''),
                        platform='youtube'
                    )
                    results.append(result)
                
                return results[:limit]
                
        except Exception as e:
            logger.error(f"خطا در جستجوی یوتیوب: {e}")
            return []
    
    async def get_audio_url(self, url: str) -> Optional[str]:
        """گرفتن لینک مستقیم صوتی از ویدیوی یوتیوب"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'extractaudio': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'url' in info:
                    return info['url']
                
                # اگه فرمت‌های مختلف داره
                if 'formats' in info:
                    # اولویت با بهترین کیفیت صوتی
                    for fmt in info['formats']:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            return fmt['url']
                    
                    # اگه صوتی خالص نبود، بهترین فرمت ممکن
                    return info['formats'][-1]['url']
                
                return None
                
        except Exception as e:
            logger.error(f"خطا در گرفتن لینک صوتی: {e}")
            return None