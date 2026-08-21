import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎬 Telegram Video Bot\n\n"
        "Video ya file bhejo, main use receive karunga.\n\n"
        "/start - Start\n/help - Help"
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "📌 Help\n\n"
        "• Video bhejo → bot receive karega\n"
        "• Document/video file bhejo → bot receive karega\n"
        "• Railway par BOT_TOKEN variable set karna zaroori hai."
    )

@dp.message(F.video)
async def video_received(message: Message):
    size_mb = (message.video.file_size or 0) / (1024 * 1024)
    await message.answer(
        f"✅ Video received!\n📁 Size: {size_mb:.2f} MB\n"
        f"🆔 File ID: {message.video.file_id}"
    )

@dp.message(F.document)
async def document_received(message: Message):
    await message.answer(
        f"✅ File received!\n"
        f"📄 Name: {message.document.file_name or 'unknown'}\n"
        f"🆔 File ID: {message.document.file_id}"
    )

async def health(request):
    return web.Response(text="Telegram Video Bot is running.")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Health server running on port {PORT}")

async def main():
    await start_web_server()
    print("Telegram bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
