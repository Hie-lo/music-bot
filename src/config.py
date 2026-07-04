import os
import json
from dotenv import load_dotenv
from typing import List, Dict

# بارگذاری متغیرهای محیطی
load_dotenv()

class Config:
    # تنظیمات تلگرام
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH")
    
    # تنظیمات اسپاتیفای
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    SPOTIFY_ENABLED = bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET)
    
    # ادمین‌های اصلی
    ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    
    # تنظیمات عمومی
    MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", 100))
    DEFAULT_SEARCH_LIMIT = int(os.getenv("DEFAULT_SEARCH_LIMIT", 5))
    
    # دیتابیس‌های درون‌حافظه
    PLAYLIST: Dict[int, List[Dict]] = {}  # key: chat_id, value: list of songs
    CALLS: Dict[int, object] = {}         # key: chat_id, value: pytgcalls instance
    CURRENT_SONG: Dict[int, Dict] = {}    # key: chat_id, value: current song info
    HISTORY: Dict[int, List[Dict]] = {}   # key: chat_id, value: history of songs
    
    # فایل‌های داده
    ADMINS_FILE = "data/admins.json"
    HISTORY_FILE = "data/history.json"
    
    @classmethod
    def load_admins(cls):
        """بارگذاری ادمین‌ها از فایل"""
        try:
            with open(cls.ADMINS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('admins', cls.ADMIN_IDS)
        except:
            return cls.ADMIN_IDS
    
    @classmethod
    def save_admins(cls, admin_list: List[int]):
        """ذخیره ادمین‌ها در فایل"""
        with open(cls.ADMINS_FILE, 'w') as f:
            json.dump({'admins': admin_list}, f, indent=2)