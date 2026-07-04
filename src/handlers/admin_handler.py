from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
import json
import logging

logger = logging.getLogger(__name__)

class AdminHandler:
    def __init__(self, app: Client):
        self.app = app
    
    def register_handlers(self):
        """ثبت هندلرهای مدیریتی"""
        
        @self.app.on_message(filters.command("افزودن ادمین موزیک") & filters.group)
        async def add_admin(client, message: Message):
            await self.add_admin(message)
        
        @self.app.on_message(filters.command("حذف ادمین موزیک") & filters.group)
        async def remove_admin(client, message: Message):
            await self.remove_admin(message)
        
        @self.app.on_message(filters.command("لیست ادمین‌ها") & filters.group)
        async def list_admins(client, message: Message):
            await self.list_admins(message)
    
    async def add_admin(self, message: Message):
        """افزودن ادمین جدید"""
        try:
            # چک کردن دسترسی ادمین
            if not await self.is_admin(message.from_user.id):
                await message.reply_text("❌ شما دسترسی مدیریت ندارید!")
                return
            
            # گرفتن ایدی از متن پیام
            parts = message.text.split()
            if len(parts) < 2:
                await message.reply_text("❌ دستور صحیح: `افزودن ادمین موزیک [ایدی]`")
                return
            
            # ایدی می‌تونه عدد یا ریپلای باشه
            if message.reply_to_message:
                # اگه ریپلای کرده، ایدی کاربر ریپلای شده رو بگیر
                user_id = message.reply_to_message.from_user.id
            else:
                user_id = int(parts[1])
            
            # بارگذاری لیست ادمین‌ها
            admins = self.load_admins()
            
            if user_id in admins:
                await message.reply_text(f"⚠️ کاربر `{user_id}` قبلاً ادمین است!")
                return
            
            # اضافه کردن به لیست
            admins.append(user_id)
            self.save_admins(admins)
            
            await message.reply_text(
                f"✅ کاربر `{user_id}` به لیست ادمین‌ها اضافه شد.\n"
                f"📊 تعداد ادمین‌ها: {len(admins)}"
            )
            
        except ValueError:
            await message.reply_text("❌ ایدی وارد شده معتبر نیست!")
        except Exception as e:
            logger.error(f"خطا در افزودن ادمین: {e}")
            await message.reply_text("❌ خطایی رخ داد! لطفاً دوباره تلاش کنید.")
    
    async def remove_admin(self, message: Message):
        """حذف ادمین"""
        try:
            # چک کردن دسترسی ادمین
            if not await self.is_admin(message.from_user.id):
                await message.reply_text("❌ شما دسترسی مدیریت ندارید!")
                return
            
            # گرفتن ایدی از متن پیام
            parts = message.text.split()
            if len(parts) < 2:
                await message.reply_text("❌ دستور صحیح: `حذف ادمین موزیک [ایدی]`")
                return
            
            # ایدی می‌تونه عدد یا ریپلای باشه
            if message.reply_to_message:
                user_id = message.reply_to_message.from_user.id
            else:
                user_id = int(parts[1])
            
            # بارگذاری لیست ادمین‌ها
            admins = self.load_admins()
            
            if user_id not in admins:
                await message.reply_text(f"⚠️ کاربر `{user_id}` ادمین نیست!")
                return
            
            # اگه کاربر اصلی هست، اجازه نده حذف بشه
            if user_id in Config.ADMIN_IDS:
                await message.reply_text("❌ نمی‌توانید ادمین اصلی را حذف کنید!")
                return
            
            # حذف از لیست
            admins.remove(user_id)
            self.save_admins(admins)
            
            await message.reply_text(
                f"✅ کاربر `{user_id}` از لیست ادمین‌ها حذف شد.\n"
                f"📊 تعداد ادمین‌ها: {len(admins)}"
            )
            
        except ValueError:
            await message.reply_text("❌ ایدی وارد شده معتبر نیست!")
        except Exception as e:
            logger.error(f"خطا در حذف ادمین: {e}")
            await message.reply_text("❌ خطایی رخ داد! لطفاً دوباره تلاش کنید.")
    
    async def list_admins(self, message: Message):
        """نمایش لیست ادمین‌ها"""
        try:
            admins = self.load_admins()
            
            if not admins:
                await message.reply_text("📋 لیست ادمین‌ها خالی است!")
                return
            
            text = "👑 **لیست ادمین‌های موزیک:**\n\n"
            
            for i, admin_id in enumerate(admins, 1):
                # تلاش برای گرفتن اسم کاربر
                try:
                    user = await self.app.get_users(admin_id)
                    name = user.first_name or f"کاربر {admin_id}"
                    username = f"@{user.username}" if user.username else ""
                    text += f"{i}. {name} {username}\n"
                    text += f"   🆔 `{admin_id}`\n"
                except:
                    text += f"{i}. کاربر با ایدی `{admin_id}`\n"
            
            await message.reply_text(text)
            
        except Exception as e:
            logger.error(f"خطا در نمایش لیست ادمین‌ها: {e}")
            await message.reply_text("❌ خطایی رخ داد!")
    
    async def is_admin(self, user_id: int) -> bool:
        """چک کردن اینکه کاربر ادمین هست یا نه"""
        admins = self.load_admins()
        return user_id in admins or user_id in Config.ADMIN_IDS
    
    def load_admins(self) -> list:
        """بارگذاری لیست ادمین‌ها از فایل"""
        try:
            with open(Config.ADMINS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('admins', Config.ADMIN_IDS)
        except:
            return Config.ADMIN_IDS
    
    def save_admins(self, admins: list):
        """ذخیره لیست ادمین‌ها در فایل"""
        try:
            with open(Config.ADMINS_FILE, 'w') as f:
                json.dump({'admins': admins}, f, indent=2)
        except Exception as e:
            logger.error(f"خطا در ذخیره ادمین‌ها: {e}")