import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import List, Optional
from .base import BaseSearch, SearchResult
from config import Config
import logging

logger = logging.getLogger(__name__)

class SpotifySearch(BaseSearch):
    """موتور جستجوی اسپاتیفای با fallback به یوتیوب"""
    
    def __init__(self):
        self.enabled = Config.SPOTIFY_ENABLED
        self.client = None
        
        if self.enabled:
            try:
                auth_manager = SpotifyClientCredentials(
                    client_id=Config.SPOTIFY_CLIENT_ID,
                    client_secret=Config.SPOTIFY_CLIENT_SECRET
                )
                self.client = spotipy.Spotify(auth_manager=auth_manager)
                logger.info("✅ اسپاتیفای با موفقیت راه‌اندازی شد")
            except Exception as e:
                logger.error(f"❌ خطا در راه‌اندازی اسپاتیفای: {e}")
                self.enabled = False
        else:
            logger.info("ℹ️ اسپاتیفای غیرفعال است - از یوتیوب به عنوان جایگزین استفاده می‌شود")
    
    async def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """جستجو در اسپاتیفای - در صورت غیرفعال بودن، fallback به یوتیوب"""
        
        # اگه اسپاتیفای غیرفعاله یا خطا داره، از یوتیوب استفاده کن
        if not self.enabled or not self.client:
            from .youtube import YouTubeSearch
            youtube = YouTubeSearch()
            logger.info(f"🔄 Fallback به یوتیوب برای جستجوی: {query}")
            return await youtube.search(query, limit)
        
        try:
            # جستجو در اسپاتیفای
            results = self.client.search(q=query, type='track', limit=limit)
            
            tracks = []
            for track in results.get('tracks', {}).get('items', []):
                artists = ', '.join([artist['name'] for artist in track['artists']])
                
                result = SearchResult(
                    title=track['name'],
                    url=track['external_urls']['spotify'],
                    duration=track['duration_ms'] // 1000,
                    artist=artists,
                    thumbnail=track['album']['images'][0]['url'] if track['album']['images'] else '',
                    platform='spotify'
                )
                tracks.append(result)
            
            return tracks
            
        except Exception as e:
            logger.error(f"خطا در جستجوی اسپاتیفای: {e}")
            # Fallback به یوتیوب
            from .youtube import YouTubeSearch
            youtube = YouTubeSearch()
            logger.info(f"🔄 Fallback به یوتیوب برای جستجوی: {query}")
            return await youtube.search(query, limit)
    
    async def get_audio_url(self, url: str) -> Optional[str]:
        """گرفتن لینک صوتی از اسپاتیفای (با fallback به یوتیوب)"""
        
        # اسپاتیفای لینک مستقیم صوتی نداره، باید از یوتیوب استفاده کنیم
        from .youtube import YouTubeSearch
        youtube = YouTubeSearch()
        
        # اسم آهنگ رو از لینک اسپاتیفای استخراج کن
        try:
            if self.enabled and self.client:
                # استخراج ID از لینک
                track_id = url.split('/track/')[1].split('?')[0]
                track = self.client.track(track_id)
                query = f"{track['name']} {track['artists'][0]['name']}"
                logger.info(f"🔄 جستجوی معادل یوتیوب برای: {query}")
                
                # جستجو در یوتیوب با نام آهنگ و آرتیست
                results = await youtube.search(query, limit=1)
                if results:
                    return await youtube.get_audio_url(results[0].url)
        except:
            pass
        
        # اگه هیچی کار نکرد، از خود لینک برای جستجو استفاده کن
        return await youtube.get_audio_url(url)