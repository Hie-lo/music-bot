import asyncio
import logging
import os
import json
import traceback
from typing import Dict, List, Optional

from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# تلاش برای import pytgcalls
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import MediaStream
    from pytgcalls.exceptions import NoActiveGroupCall
    PYTGCALLS_AVAILABLE = True
except ImportError:
    PYTGCALLS_AVAILABLE = False
    logging.warning("⚠️ pytgcalls نصب نیست! پخش صدا کار نمی‌کند.")

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("SESSION_STRING")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("❌ اطلاعات API در فایل .env پیدا نشد!")

ADMINS_FILE = "admins.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/bot.log"), logging.StreamHandler()]
)
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

# ========== کلاس پخش ==========
class MusicPlayer:
    def __init__(self, app: Client):
        self.app = app
        self.queue = QueueManager()
        self.pytgcalls = None
        if PYTGCALLS_AVAILABLE:
            try:
                self.pytgcalls = PyTgCalls(app)
                logger.info("✅ pytgcalls آماده شد")
            except Exception as e:
                logger.error(f"❌ خطا در راه‌اندازی pytgcalls: {e}")

    async def start(self):
        if self.pytgcalls:
            try:
                await self.pytgcalls.start()
                logger.info("✅ pytgcalls راه‌اندازی شد")
            except Exception as e:
                logger.error(f"❌ خطا در start pytgcalls: {e}")

    async def join_call(self, chat_id: int):
        if not self.pytgcalls:
            raise Exception("pytgcalls در دسترس نیست")
        try:
            await self.pytgcalls.join_group_call(chat_id, MediaStream(""))
            logger.info(f"✅ به کال گروه {chat_id} پیوست")
        except NoActiveGroupCall:
            raise Exception("❗️ ابتدا یک کال صوتی در گروه شروع کنید.")
        except Exception as e:
            logger.error(f"❌ خطا در پیوستن به کال: {e}")
            raise

    async def leave_call(self, chat_id: int):
        if not self.pytgcalls:
            return
        try:
            await self.pytgcalls.leave_group_call(chat_id)
            logger.info(f"✅ از کال گروه {chat_id} خارج شد")
        except Exception as e:
            logger.error(f"❌ خطا در خروج از کال: {e}")

    async def play(self, chat_id: int, song: Dict, audio_url: str):
        if not self.pytgcalls:
            logger.warning("⚠️ pytgcalls در دسترس نیست - فقط شبیه‌سازی")
            pos = self.queue.add(chat_id, song)
            if pos == 0:
                return "در حال پخش (شبیه‌سازی)..."
            else:
                return f"به صف اضافه شد (موقعیت {pos})"

        try:
            pos = self.queue.add(chat_id, song)
            if pos == 0:
                await self.join_call(chat_id)
                await self.pytgcalls.change_stream(chat_id, MediaStream(audio_url))
                return "در حال پخش..."
            else:
                return f"به صف اضافه شد (موقعیت {pos})"
        except Exception as e:
            logger.error(f"خطا در پخش: {e}")
            raise

    async def pause(self, chat_id: int):
        if not self.pytgcalls:
            return "توقف (شبیه‌سازی)"
        try:
            await self.pytgcalls.pause_stream(chat_id)
            return "توقف"
        except Exception as e:
            logger.error(f"خطا در توقف: {e}")
            raise

    async def resume(self, chat_id: int):
        if not self.pytgcalls:
            return "ادامه (شبیه‌سازی)"
        try:
            await self.pytgcalls.resume_stream(chat_id)
            return "ادامه"
        except Exception as e:
            logger.error(f"خطا در ادامه: {e}")
            raise

    async def skip(self, chat_id: int):
        if not self.pytgcalls:
            next_song = self.queue.next(chat_id)
            return next_song

        try:
            next_song = self.queue.next(chat_id)
            if next_song:
                await self.pytgcalls.change_stream(chat_id, MediaStream(next_song["url"]))
                return next_song
            else:
                await self.leave_call(chat_id)
                self.queue.clear(chat_id)
                return None
        except Exception as e:
            logger.error(f"خطا در skip: {e}")
            raise

    async def stop(self, chat_id: int):
        await self.leave_call(chat_id)
        self.queue.clear(chat_id)
        return "توقف کامل"

    def get_queue_info(self, chat_id: int) -> str:
        return self.queue.get_info(chat_id)

# ========== کلاس جستجو ==========
class SearchManager:
    async def search(self, query: str) -> Optional[Dict]:
        logger.info(f"🔍 جستجو برای: {query}")
        return {
            "title": f"🎵 {query}",
            "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
            "duration": 180,
            "artist": "Unknown Artist",
            "platform": "youtube"
        }

# ========== راه‌اندازی ==========
app = Client(
    "music_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    session_string=SESSION_STRING if SESSION_STRING else None
)

player = MusicPlayer(app)
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

@app.on_message(filters.private & filters.command("start"))
async def start_private(client, message: Message):
    txt = "🎵 **ربات موزیک پلیر**\n\n📌 **دستورات:**\n• `پخش [نام]`\n• `پخش لینک [لینک]`\n• `توقف` / `ادامه` / `بعدی` / `اتمام`\n• `لیست پخش`\n• `افزودن ادمین موزیک [ایدی]`"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("➕ افزودن به گروه", url="https://t.me/Player_Boy_bot?startgroup=true")]])
    await message.reply_text(txt, reply_markup=kb)

@app.on_message(filters.private & filters.text)
async def private_text(client, message: Message):
    await message.reply_text("✅ پیامت دریافت شد! برای راهنما /start بفرست.")

@app.on_message(filters.group & filters.text & filters.regex(r'^پخش .+'))
async def play_command(client, message: Message):
    try:
        query = message.text[3:].strip()
        if not query:
            await message.reply_text("❌ نام موزیک را وارد کن")
            return

        msg = await message.reply_text(f"🔍 در حال جستجوی: {query}")
        song = await searcher.search(query)
        if not song:
            await msg.edit_text("❌ پیدا نشد")
            return

        result = await player.play(message.chat.id, song, song["url"])
        txt, kb = create_play_message(song, message.chat.id)
        await msg.edit_text(txt, reply_markup=kb)
        logger.info(f"✅ {result}")
    except Exception as e:
        logger.error(f"خطا در پخش: {e}\n{traceback.format_exc()}")
        await message.reply_text(f"❌ خطا: {str(e)[:100]}")

@app.on_message(filters.group & filters.text & filters.regex(r'^(توقف|ادامه|بعدی|اتمام|لیست پخش)$'))
async def control_commands(client, message: Message):
    text = message.text
    chat_id = message.chat.id
    try:
        if text == "توقف":
            result = await player.pause(chat_id)
            await message.reply_text(f"⏸️ {result}")
        elif text == "ادامه":
            result = await player.resume(chat_id)
            await message.reply_text(f"▶️ {result}")
        elif text == "بعدی":
            s = await player.skip(chat_id)
            if s:
                await message.reply_text(f"⏭️ {s.get('title')}")
            else:
                await message.reply_text("⏹️ پایان لیست")
        elif text == "اتمام":
            result = await player.stop(chat_id)
            await message.reply_text(f"⏹️ {result}")
        elif text == "لیست پخش":
            info = player.get_queue_info(chat_id)
            await message.reply_text(info)
    except Exception as e:
        logger.error(f"خطا در کنترل: {e}\n{traceback.format_exc()}")
        await message.reply_text(f"❌ خطا: {str(e)[:100]}")

@app.on_message(filters.group & filters.text & filters.regex(r'^(افزودن ادمین موزیک|حذف ادمین موزیک|لیست ادمین‌ها)'))
async def admin_commands(client, message: Message):
    text = message.text
    if text.startswith("افزودن ادمین موزیک "):
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

@app.on_message(filters.group & filters.text & filters.regex(r'^پخش$') & filters.reply)
async def play_reply(client, message: Message):
    replied = message.reply_to_message
    if replied and replied.text:
        msg = await message.reply_text(f"🔍 جستجو: {replied.text[:30]}...")
        song = await searcher.search(replied.text)
        if song:
            await player.play(message.chat.id, song, song["url"])
            txt, kb = create_play_message(song, message.chat.id)
            await msg.edit_text(txt, reply_markup=kb)
        else:
            await msg.edit_text("❌ پیدا نشد")

@app.on_callback_query()
async def callbacks(client, cq: CallbackQuery):
    try:
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
    except Exception as e:
        logger.error(f"خطا در callback: {e}\n{traceback.format_exc()}")
        await cq.answer("❌ خطا", show_alert=True)

# ========== اجرا ==========
async def main():
    await app.start()
    await player.start()
    logger.info("🚀 ربات راه‌اندازی شد!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ خاموش شد")
    except Exception as e:
        logger.error(f"❌ خطا: {e}\n{traceback.format_exc()}")