#!/bin/bash

echo "🚀 راه‌اندازی ربات موزیک پلیر..."

# ایجاد پوشه‌های مورد نیاز
mkdir -p src/handlers src/player src/search src/utils data logs

# ایجاد فایل‌های خالی مورد نیاز
touch data/admins.json
touch data/history.json
touch logs/bot.log

# نصب کتابخونه‌های سیستمی
echo "📦 نصب کتابخونه‌های سیستمی..."
apt-get update
apt-get install -y python3 python3-pip ffmpeg

# نصب کتابخونه‌های پایتون
echo "📦 نصب کتابخونه‌های پایتون..."
pip3 install -r requirements.txt

echo "✅ محیط آماده است!"
echo "برای اجرا: python3 src/main.py"