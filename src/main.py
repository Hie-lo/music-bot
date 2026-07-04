import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from search import SearchManager
from player import MusicPlayer
import json
import re

# ایجاد پوشه
os.makedirs('logs', exist_ok=True)

# لاگ ساده
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

search_manager = SearchManager()
music_player = None

class MusicBot:
    def __init__(self):
        self.app = Client(
            "musicbot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        global music_player
        music_player = MusicPlayer(self.app)
        self.music_player = music_player
        self.search_manager = search_manager
    
    async def start(self):
        logger.info("🚀 ربات شروع به کار کرد")
        self.register_handlers()
        await self.app.start()
        bot = await self.app.get_me()
        logger.info(f"✅ @{bot.username} فعال شد")
        await asyncio.Event().wait()
    
    def register_handlers(self):
        """هندلر ساده برای همه پیام‌ها"""
        
        # ===== دریافت همه پیام‌ها =====
        @self.app.on_message()
        async def all_messages(client, message: Message):
            # فقط پیام‌های متنی در گروه
            if message.chat.type in ["group", "supergroup"] and message.text:
                logger.info(f"📩 {message.text[:50]}...")
                await self.process_command(message)
            
            # پیام خصوصی
            elif message.chat.type == "private" and message.text:
                if message.text.startswith("/start"):
                    await self.send_welcome(message)
        
        # ===== دکمه‌ها =====
        @self.app.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            await self.handle_callback(callback_query)
        
        logger.info("✅ هندلر ثبت شد")
    
    async def process_command(self, message: Message):
        """پردازش دستورات"""
        text = message.text or ""
        
        # پخش معمولی
        if text.startswith("پخش "):
            await self.handle_play(message, text[3:].strip())
            return
        
        # پخش لینک
        if text.startswith("پخش لینک "):
            await self.handle_play_link(message, text[8:].strip())
            return
        
        # پخش در پلتفرم خاص
        match = re.match(r'^پخش (یوتیوب|اسپاتیفای|ساندکلاد) (.+)$', text)
        if match:
            await self.handle_play_platform(message, match.group(1), match.group(2))
            return
        
        # کنترل
        if text == "توقف":
            await self.pause_song(message)
        elif text == "ادامه":
            await self.resume_song(message)
        elif text == "بعدی":
            await self.skip_song(message)
        elif text == "اتمام":
            await self.stop_song(message)
        elif text == "لیست پخش":
            await self.show_queue(message)
        
        # مدیریت
        elif text.startswith("افزودن ادمین موزیک "):
            await self.add_admin(message)
        elif text.startswith("حذف ادمین موزیک "):
            await self.remove_admin(message)
        elif text == "لیست ادمین‌ها":
            await self.list_admins(message)
        
        # ریپلای
        elif text == "پخش" and message.reply_to_message:
            await self.handle_play_reply(message)
    
    # ===== توابع اصلی =====
    
    async def handle_play(self, message: Message, query: str):
        msg = await message.reply_text(f"🔍 {query}")
        results = await self.search_manager.search_with_fallback(query)
        if not results:
            await msg.edit_text("❌ پیدا نشد")
            return
        song = results[0]
        audio_url = await self.search_manager.get_audio_url(song.url, song.platform)
        if not audio_url:
            await msg.edit_text("❌ خطا")
            return
        await self.music_player.play_song(message.chat.id, audio_url, song.to_dict())
        await self._send_play_message(message, song)
        await msg.delete()
    
    async def handle_play_link(self, message: Message, link: str):
        platform = self._detect_platform(link)
        audio_url = await self.search_manager.get_audio_url(link, platform)
        if not audio_url:
            await message.reply_text("❌ خطا")
            return
        song_info = {'title': '🎵 لینک', 'url': link, 'duration': 0, 'artist': 'Unknown', 'platform': platform}
        await self.music_player.play_song(message.chat.id, audio_url, song_info)
        await self._send_play_message(message, song_info)
    
    async def handle_play_platform(self, message: Message, platform: str, query: str):
        results = await self.search_manager.search(query, platform)
        if not results:
            results = await self.search_manager.search(query, 'youtube')
        if not results:
            await message.reply_text("❌ پیدا نشد")
            return
        song = results[0]
        audio_url = await self.search_manager.get_audio_url(song.url, song.platform)
        if not audio_url:
            await message.reply_text("❌ خطا")
            return
        await self.music_player.play_song(message.chat.id, audio_url, song.to_dict())
        await self._send_play_message(message, song)
    
    async def handle_play_reply(self, message: Message):
        msg = message.reply_to_message
        if msg and msg.text:
            results = await self.search_manager.search_with_fallback(msg.text)
            if results:
                song = results[0]
                audio_url = await self.search_manager.get_audio_url(song.url, song.platform)
                if audio_url:
                    await self.music_player.play_song(message.chat.id, audio_url, song.to_dict())
                    await self._send_play_message(message, song)
    
    # ===== کنترل =====
    async def pause_song(self, m):
        ok = await self.music_player.pause_song(m.chat.id)
        await m.reply_text("⏸️ توقف" if ok else "❌")
    async def resume_song(self, m):
        ok = await self.music_player.resume_song(m.chat.id)
        await m.reply_text("▶️ ادامه" if ok else "❌")
    async def skip_song(self, m):
        s = await self.music_player.skip_song(m.chat.id)
        await m.reply_text(f"⏭️ {s.get('title')}" if s else "⏹️ پایان")
    async def stop_song(self, m):
        await self.music_player.stop_song(m.chat.id)
        await m.reply_text("⏹️ توقف")
    async def show_queue(self, m):
        await m.reply_text(self.music_player.queue_manager.get_queue_info(m.chat.id))
    
    # ===== مدیریت =====
    async def add_admin(self, m):
        parts = m.text.split()
        uid = int(parts[1]) if len(parts) > 1 and not m.reply_to_message else (m.reply_to_message.from_user.id if m.reply_to_message else None)
        if not uid:
            await m.reply_text("❌ دستور: افزودن ادمین موزیک [ایدی]")
            return
        admins = []
        try:
            with open(Config.ADMINS_FILE, 'r') as f:
                admins = json.load(f).get('admins', [])
        except: pass
        if uid in admins:
            await m.reply_text("⚠️ قبلاً ادمین است")
            return
        admins.append(uid)
        with open(Config.ADMINS_FILE, 'w') as f:
            json.dump({'admins': admins}, f, indent=2)
        await m.reply_text(f"✅ ادمین شد: `{uid}`")
    
    async def remove_admin(self, m):
        parts = m.text.split()
        uid = int(parts[1]) if len(parts) > 1 and not m.reply_to_message else (m.reply_to_message.from_user.id if m.reply_to_message else None)
        if not uid:
            await m.reply_text("❌ دستور: حذف ادمین موزیک [ایدی]")
            return
        admins = []
        try:
            with open(Config.ADMINS_FILE, 'r') as f:
                admins = json.load(f).get('admins', [])
        except: pass
        if uid not in admins:
            await m.reply_text("⚠️ ادمین نیست")
            return
        admins.remove(uid)
        with open(Config.ADMINS_FILE, 'w') as f:
            json.dump({'admins': admins}, f, indent=2)
        await m.reply_text(f"✅ حذف شد: `{uid}`")
    
    async def list_admins(self, m):
        admins = []
        try:
            with open(Config.ADMINS_FILE, 'r') as f:
                admins = json.load(f).get('admins', [])
        except: pass
        if not admins:
            await m.reply_text("📋 لیست خالی")
            return
        txt = "👑 ادمین‌ها:\n"
        for i, uid in enumerate(admins, 1):
            try:
                u = await self.app.get_users(uid)
                txt += f"{i}. {u.first_name} (`{uid}`)\n"
            except:
                txt += f"{i}. `{uid}`\n"
        await m.reply_text(txt)
    
    # ===== کمکی =====
    async def _send_play_message(self, m, song):
        from utils import create_play_message
        text, kb = create_play_message(song, m.chat.id)
        await m.reply_text(text, reply_markup=kb)
    
    async def handle_callback(self, cq):
        data = cq.data
        cid = cq.message.chat.id
        if data.startswith("pause"):
            await self.music_player.pause_song(cid)
            await cq.answer("⏸️")
        elif data.startswith("resume"):
            await self.music_player.resume_song(cid)
            await cq.answer("▶️")
        elif data.startswith("skip"):
            s = await self.music_player.skip_song(cid)
            await cq.answer(f"⏭️ {s.get('title')[:20]}" if s else "پایان")
        elif data.startswith("stop"):
            await self.music_player.stop_song(cid)
            await cq.answer("⏹️")
        elif data.startswith("queue"):
            await cq.answer("📋")
            await cq.message.reply_text(self.music_player.queue_manager.get_queue_info(cid))
        elif data == "help":
            await cq.answer("📖")
            await cq.message.reply_text("راهنما:\nپخش [نام]\nپخش لینک [لینک]\nپخش یوتیوب [نام]\nتوقف / ادامه / بعدی / اتمام")
        elif data == "status":
            await cq.answer("✅ آنلاین")
    
    async def send_welcome(self, m):
        txt = "🎵 ربات موزیک پلیر\n\nدستورات:\nپخش [نام]\nپخش لینک [لینک]\nپخش یوتیوب [نام]\nتوقف / ادامه / بعدی / اتمام"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ افزودن به گروه", url="https://t.me/Player_Boy_bot?startgroup=true")],
            [InlineKeyboardButton("📖 راهنما", callback_data="help"), InlineKeyboardButton("📊 وضعیت", callback_data="status")]
        ])
        await m.reply_text(txt, reply_markup=kb)
    
    def _detect_platform(self, link):
        if 'youtube' in link or 'youtu.be' in link: return 'youtube'
        if 'spotify' in link: return 'spotify'
        if 'soundcloud' in link: return 'soundcloud'
        return 'default'

if __name__ == "__main__":
    bot = MusicBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("⏹️ خاموش شد")
    except Exception as e:
        logger.error(f"❌ {e}")