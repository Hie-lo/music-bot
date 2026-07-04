#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# اضافه کردن مسیر src به sys.path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# تغییر دایرکتوری به src
os.chdir(src_path)

# اجرای main
if __name__ == "__main__":
    import importlib.util
    import asyncio

    main_file = src_path / "main.py"
    spec = importlib.util.spec_from_file_location("main", main_file)
    main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main)

    bot = main.MusicBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("⏹️ ربات متوقف شد")