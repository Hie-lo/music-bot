import asyncio
import logging
import os
import re
import json
from typing import Dict, List, Optional

from dotenv import load_dotenv  # ← اضافه شده برای خواندن env
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ========== بارگذاری فایل .env ==========
load_dotenv()  # این خط فایل .env را پیدا و بارگذاری می‌کند

# ========== دریافت اطلاعات از محیط ==========
API_ID = int(os.getenv("API_ID", 0))  # پیش‌فرض 0 در صورت نبودن
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# بررسی وجود اطلاعات (برای اطمینان)
if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("❌ اطلاعات API_ID، API_HASH یا BOT_TOKEN در فایل .env پیدا نشد!")

ADMINS_FILE = "admins.json"

# ========== لاگ ==========
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ========== کلاس مدیریت صف ==========
class QueueManager:
    def __init__(self):
        self.queues: Dict[int, List[Dict]] = {}
        self.current: Dict[int, Optional[Dict]] = {}

    def get_queue(self, chat_id: int) -> List[Dict]:
        if chat_id not in self.queues:
            self.queues[chat_id] = []
        return self.queues[chat_id]

    def add(self, chat_id: int, song: Dict) -> int:
        queue = self.get_queue(chat_id)
        if not queue and not self.current.get(chat_id):
            self.current[chat_id] = song
            return 0
        queue.append(song)
        return len(queue)

    def next(self, chat_id: int) -> Optional[Dict]:
        queue = self.get_queue(chat_id)
        if queue:
            self.current[chat_id] = queue.pop(0)
            return self.current[chat_id]
        self.current[chat_id] = None
        return None

    def clear(self, chat_id: int):
        self.queues[chat_id] = []
        self.current[chat_id] = None

    def get_info(self, chat_id: int) -> str:
        queue = self.get_queue(chat_id)
        current = self.current.get(chat_id)
        if not current and not queue:
            return "📋 لیست پخش خالی است"
        txt = "🎵 **در حال پخش:**\n"
        if current:
            txt += f"• {current.get('title', 'Unknown')}\n"
        if queue:
            txt += f"\n⏳ **صف ({len(queue)}):**\n"
            for i, s in enumerate(queue[:5], 1):
                txt += f"{i}. {s.get('title', 'Unknown')}\n"
            if len(queue) > 5:
                txt += f"... و {len(queue)-5} تا دیگر"
        return txt

# ========== کلاس پخش (ساده) ==========
class MusicPlayer:
    def __init__(self):
        self.queue = QueueManager()

    async def play(self, chat_id: int, song: Dict):
        pos = self.queue.add(chat_id, song)
        if pos == 0:
            logger.info(f"🎵 در حال پخش: {song.get('title')}")
        else:
            logger.info(f"➕ به صف اضافه شد: {song.get('title')} (موقعیت {pos})")

    async def pause(self, chat_id: int):
        logger.info(f"⏸️ توقف در {chat_id}")

    async def resume(self, chat_id: int):
        logger.info(f"▶️ ادامه در {chat_id}")

    async def skip(self, chat_id: int) -> Optional[Dict]:
        return self.queue.next(chat_id)

    async def stop(self, chat_id: int):
        self.queue.clear(chat_id)
        logger.info(f"⏹️ توقف کامل در {chat_id}")

    def get_queue_info(self, chat_id: int) -> str:
        return self.queue.get_info(chat_id)

# ========== کلاس جستجو (ساده) ==========
class SearchManager:
    async def search(self, query: str) -> List[Dict]:
        # شبیه‌سازی جستجو - در نسخه واقعی از yt-dlp استفاده کن
        return [{
            "title": f"🎵 {query}",
            "url": f"https://youtube.com/watch?v=test_{query}",
            "duration": 180,
            "artist": "Unknown",
            "platform": "youtube"
        }]

# ========== ربات اصلی ==========
app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
player = MusicPlayer()
searcher = SearchManager()

# ========== توابع کمکی ==========
def load_admins() -> List[int]:
    try:
        with open(ADMINS_FILE, "r") as f:
            return json.load(f).get("admins", [])
    except:
        return []

def save_admins(admins: List[int]):
    with open(ADMINS_FILE, "w") as f:
        json.dump({"admins": admins}, f)

def create_play_message(song: Dict, chat_id: int):
    text = f"🎵 **{song.get('title', 'Unknown')}**\n"
    text += f"🎤 {song.get('artist', 'Unknown')}\n"
    if song.get("duration"):
        m, s = divmod(song["duration"], 60)
        text += f"⏱️ {m}:{s:02d}\n"
    text += f"📱 {song.get('platform', 'unknown').title()}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏸️ توقف", callback_data=f"pause_{chat_id}"),
         InlineKeyboardButton("▶️ ادامه", callback_data=f"resume_{chat_id}")],
        [InlineKeyboardButton("⏭️ بعدی", callback_data=f"skip_{chat_id}"),
         InlineKeyboardButton("⏹️ اتمام", callback_data=f"stop_{chat_id}")],
        [InlineKeyboardButton("📋 لیست", callback_data=f"queue_{chat_id}")]
    ])
    return text, kb

# ========== هندلرها ==========
@app.on_message()
async def all_messages(client, message: Message):
    logger.info(f"📩 {message.text} | چت: {message.chat.id} | نوع: {message.chat.type}")

    if not message.text:
        return

    # پاسخ تست (برای اطمینان از دریافت)
    if message.chat.type == "private" and not message.text.startswith("/"):
        await message.reply_text("✅ پیامت دریافت شد! برای راهنما /start بفرست.")

    # پردازش دستورات گروه
    if message.chat.type in ["group", "supergroup"]:
        text = message.text

        # پخش
        if text.startswith("پخش "):
            query = text[3:].strip()
            if not query:
                await message.reply_text("❌ نام موزیک را وارد کن")
                return
            await message.reply_text(f"🔍 در حال جستجوی: {query}")
            results = await searcher.search(query)
            if not results:
                await message.reply_text("❌ پیدا نشد")
                return
            song = results[0]
            await player.play(message.chat.id, song)
            txt, kb = create_play_message(song, message.chat.id)
            await message.reply_text(txt, reply_markup=kb)

        # کنترل
        elif text == "توقف":
            await player.pause(message.chat.id)
            await message.reply_text("⏸️ توقف")
        elif text == "ادامه":
            await player.resume(message.chat.id)
            await message.reply_text("▶️ ادامه")
        elif text == "بعدی":
            s = await player.skip(message.chat.id)
            if s:
                await message.reply_text(f"⏭️ {s.get('title')}")
            else:
                await message.reply_text("⏹️ پایان لیست")
        elif text == "اتمام":
            await player.stop(message.chat.id)
            await message.reply_text("⏹️ توقف کامل")
        elif text == "لیست پخش":
            info = player.get_queue_info(message.chat.id)
            await message.reply_text(info)

        # ادمین
        elif text.startswith("افزودن ادمین موزیک "):
            parts = text.split()
            if len(parts) < 2:
                await message.reply_text("❌ دستور: افزودن ادمین موزیک [ایدی]")
                return
            try:
                uid = int(parts[1])
            except:
                await message.reply_text("❌ ایدی نامعتبر")
                return
            admins = load_admins()
            if uid in admins:
                await message.reply_text("⚠️ قبلاً ادمین است")
                return
            admins.append(uid)
            save_admins(admins)
            await message.reply_text(f"✅ ادمین شد: `{uid}`")

        elif text.startswith("حذف ادمین موزیک "):
            parts = text.split()
            if len(parts) < 2:
                await message.reply_text("❌ دستور: حذف ادمین موزیک [ایدی]")
                return
            try:
                uid = int(parts[1])
            except:
                await message.reply_text("❌ ایدی نامعتبر")
                return
            admins = load_admins()
            if uid not in admins:
                await message.reply_text("⚠️ ادمین نیست")
                return
            admins.remove(uid)
            save_admins(admins)
            await message.reply_text(f"✅ حذف شد: `{uid}`")

        elif text == "لیست ادمین‌ها":
            admins = load_admins()
            if not admins:
                await message.reply_text("📋 لیست خالی")
                return
            txt = "👑 **ادمین‌ها:**\n"
            for i, uid in enumerate(admins, 1):
                try:
                    u = await app.get_users(uid)
                    txt += f"{i}. {u.first_name} (`{uid}`)\n"
                except:
                    txt += f"{i}. `{uid}`\n"
            await message.reply_text(txt)

        # ریپلای
        elif text == "پخش" and message.reply_to_message:
            replied = message.reply_to_message
            if replied and replied.text:
                results = await searcher.search(replied.text)
                if results:
                    song = results[0]
                    await player.play(message.chat.id, song)
                    txt, kb = create_play_message(song, message.chat.id)
                    await message.reply_text(txt, reply_markup=kb)

    # دستور start در پیوی
    elif message.chat.type == "private" and message.text.startswith("/start"):
        txt = (
            "🎵 **ربات موزیک پلیر**\n\n"
            "📌 **دستورات:**\n"
            "• `پخش [نام]`\n"
            "• `پخش لینک [لینک]`\n"
            "• `توقف` / `ادامه` / `بعدی` / `اتمام`\n"
            "• `لیست پخش`\n"
            "• `افزودن ادمین موزیک [ایدی]`"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ افزودن به گروه", url="https://t.me/Player_Boy_bot?startgroup=true")]
        ])
        await message.reply_text(txt, reply_markup=kb)

# ========== دکمه‌ها ==========
@app.on_callback_query()
async def callbacks(client, cq: CallbackQuery):
    data = cq.data
    chat_id = cq.message.chat.id
    if data.startswith("pause"):
        await player.pause(chat_id)
        await cq.answer("⏸️")
    elif data.startswith("resume"):
        await player.resume(chat_id)
        await cq.answer("▶️")
    elif data.startswith("skip"):
        s = await player.skip(chat_id)
        await cq.answer(f"⏭️ {s.get('title')[:20]}" if s else "پایان")
    elif data.startswith("stop"):
        await player.stop(chat_id)
        await cq.answer("⏹️")
    elif data.startswith("queue"):
        await cq.answer("📋")
        await cq.message.reply_text(player.get_queue_info(chat_id))

# ========== اجرا ==========
if __name__ == "__main__":
    print("🚀 ربات یکپارچه با .env در حال اجرا...")
    app.run()