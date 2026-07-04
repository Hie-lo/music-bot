from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict

def create_play_message(song_info: Dict, chat_id: int):
    """ساخت پیام پخش با دکمه‌ها"""
    
    # متن اصلی
    text = f"🎵 **در حال پخش:**\n\n"
    text += f"📌 **نام:** {song_info.get('title', 'Unknown')}\n"
    
    if song_info.get('artist'):
        text += f"🎤 **خواننده:** {song_info.get('artist')}\n"
    
    if song_info.get('duration'):
        minutes = song_info.get('duration') // 60
        seconds = song_info.get('duration') % 60
        text += f"⏱️ **زمان:** {minutes}:{seconds:02d}\n"
    
    if song_info.get('platform'):
        emoji = {
            'youtube': '▶️',
            'spotify': '🎵',
            'soundcloud': '☁️'
        }
        platform_name = song_info.get('platform', '').title()
        text += f"📱 **پلتفرم:** {emoji.get(song_info.get('platform'), '🔗')} {platform_name}\n"
    
    # دکمه‌های کنترلی
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸️ توقف", callback_data=f"pause_{chat_id}"),
            InlineKeyboardButton("▶️ ادامه", callback_data=f"resume_{chat_id}"),
        ],
        [
            InlineKeyboardButton("⏭️ بعدی", callback_data=f"skip_{chat_id}"),
            InlineKeyboardButton("⏹️ اتمام", callback_data=f"stop_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🔁 تکرار", callback_data=f"repeat_{chat_id}"),
            InlineKeyboardButton("📋 لیست پخش", callback_data=f"queue_{chat_id}"),
        ]
    ])
    
    return text, keyboard