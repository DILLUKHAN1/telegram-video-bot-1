import os
import asyncio
from urllib.parse import quote

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

# Railway normally provides RAILWAY_PUBLIC_DOMAIN.
# You can also set WEB_URL manually in Railway Variables.
WEB_URL = os.getenv("WEB_URL")

if not WEB_URL:
    public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    WEB_URL = (
        f"https://{public_domain}"
        if public_domain
        else f"http://localhost:{PORT}"
    )

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")


bot = Bot(BOT_TOKEN)
dp = Dispatcher()

http_session = None


def make_play_url(file_id: str) -> str:
    return (
        f"{WEB_URL.rstrip('/')}/watch"
        f"?file_id={quote(file_id, safe='')}"
    )


# =========================
# /start
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎬 Telegram Video Bot\n\n"
        "Video ya video file bhejo, main receive karke "
        "Play Online button dunga.\n\n"
        "/start - Start\n"
        "/help - Help"
    )


# =========================
# /help
# =========================

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "📌 Help\n\n"
        "• Video bhejo → bot receive karega\n"
        "• Video ke saath ▶️ Play Online button milega\n"
        "• Button dabao → web video player khulega"
    )


# =========================
# SEND VIDEO RESULT
# =========================

async def send_received(
    message: Message,
    file_id: str,
    size_bytes: int = 0
):
    size_mb = (
        size_bytes / (1024 * 1024)
        if size_bytes
        else 0
    )

    play_url = make_play_url(file_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️ Play Online",
                    url=play_url
                )
            ]
        ]
    )

    size_text = (
        f"📁 Size: {size_mb:.2f} MB\n"
        if size_bytes
        else ""
    )

    await message.answer(
        "✅ Video received!\n"
        f"{size_text}"
        f"🆔 File ID: {file_id}",
        reply_markup=keyboard,
    )


# =========================
# VIDEO RECEIVED
# =========================

@dp.message(F.video)
async def video_received(message: Message):

    await send_received(
        message,
        message.video.file_id,
        message.video.file_size or 0,
    )


# =========================
# DOCUMENT / VIDEO FILE
# =========================

@dp.message(F.document)
async def document_received(message: Message):

    document = message.document

    mime = document.mime_type or ""

    filename = (
        document.file_name or ""
    ).lower()

    video_extensions = (
        ".mp4",
        ".mkv",
        ".webm",
        ".mov",
        ".m4v",
        ".avi",
        ".mpeg",
        ".mpg",
        ".3gp",
    )

    if (
        mime.startswith("video/")
        or filename.endswith(video_extensions)
    ):

        await send_received(
            message,
            document.file_id,
            document.file_size or 0,
        )

    else:

        await message.answer(
            "✅ File received!\n\n"
            f"📄 Name: "
            f"{document.file_name or 'unknown'}\n"
            f"🆔 File ID: "
            f"{document.file_id}\n\n"
            "▶️ Play Online sirf video files "
            "ke liye available hai."
        )


# =========================
# HEALTH CHECK
# =========================

async def health(request: web.Request):

    return web.Response(
        text="Telegram Video Bot is running ✅"
    )


# =========================
# WEB VIDEO PLAYER
# =========================

async def player(request: web.Request):

    file_id = request.query.get("file_id")

    if not file_id:

        return web.Response(
            text="Missing file_id",
            status=400
        )

    video_url = (
        f"{request.scheme}://{request.host}"
        f"/stream?file_id="
        f"{quote(file_id, safe='')}"
    )

    html = f"""<!doctype html>

<html>

<head>

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>Play Online</title>

<style>

body {{
    margin: 0;
    background: #0b0b0f;
    color: white;
    font-family: Arial, sans-serif;
}}

.wrap {{
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 20px;
    box-sizing: border-box;
}}

h1 {{
    margin: 0 0 18px;
    font-size: 24px;
}}

video {{
    width: min(100%, 900px);
    max-height: 80vh;
    background: #000;
    border-radius: 14px;
}}

.note {{
    margin-top: 12px;
    color: #aaa;
    font-size: 13px;
}}

</style>

</head>

<body>

<div class="wrap">

<h1>🎬 Telegram Video Player</h1>

<video
    controls
    playsinline
    preload="metadata"
    src="{video_url}">
</video>

<div class="note">
Play Online
</div>

</div>

</body>

</html>
"""

    return web.Response(
        text=html,
        content_type="text/html"
    )


# =========================
# VIDEO STREAM PROXY
# =========================

async def stream_video(request: web.Request):

    global http_session

    file_id = request.query.get("file_id")

    if not file_id:

        return web.Response(
            text="Missing file_id",
            status=400
        )

    if http_session is None:

        http_session = aiohttp.ClientSession()

    # Ask Telegram for the real file path
    api_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/getFile"
    )

    try:

        async with http_session.get(
            api_url,
            params={"file_id": file_id},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:

            data = await response.json()

    except Exception:

        return web.Response(
            text="Could not contact Telegram",
            status=502
        )

    if (
        not data.get("ok")
        or not data.get("result", {}).get("file_path")
    ):

        return web.Response(
            text=(
                "Telegram could not find this file. "
                "The file may be unavailable."
            ),
            status=404
        )

    file_path = data["result"]["file_path"]

    telegram_file_url = (
        f"https://api.telegram.org/"
        f"file/bot{BOT_TOKEN}/{file_path}"
    )

    try:

        async with http_session.get(
            telegram_file_url,
            timeout=aiohttp.ClientTimeout(total=None),
        ) as upstream:

            if upstream.status != 200:

                return web.Response(
                    text=(
                        "Could not download video "
                        "from Telegram"
                    ),
                    status=502
                )

            content_type = (
                upstream.headers.get(
                    "Content-Type",
                    "video/mp4"
                )
            )

            response = web.StreamResponse(
                status=200,
                headers={
                    "Content-Type": content_type,
                    "Cache-Control": "no-store",
                    "Accept-Ranges": "none",
                },
            )

            await response.prepare(request)

            async for chunk in upstream.content.iter_chunked(
                1024 * 256
            ):

                await response.write(chunk)

            await response.write_eof()

            return response

    except asyncio.CancelledError:

        raise

    except Exception:

        return web.Response(
            text="Video streaming failed",
            status=502
        )


# =========================
# START WEB SERVER
# =========================

async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health
    )

    app.router.add_get(
        "/health",
        health
    )

    app.router.add_get(
        "/watch",
        player
    )

    app.router.add_get(
        "/stream",
        stream_video
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    print(
        f"Web server running on port {PORT}"
    )

    print(
        f"WEB_URL: {WEB_URL}"
    )


# =========================
# MAIN
# =========================

async def main():

    await start_web_server()

    print(
        "Telegram bot starting..."
    )

    await dp.start_polling(bot)


if __name__ == "__main__":

    try:

        asyncio.run(main())

    finally:

        if (
            http_session
            and not http_session.closed
        ):

            asyncio.run(
                http_session.close()
            )
