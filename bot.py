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
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🎬 NIGHT VIDEOS\n\n"
        "Video ya video file bhejo.\n"
        "Main aapko Play Online button dunga.\n\n"
        "/start - Start\n"
        "/help - Help"
    )


# =========================
# HELP
# =========================

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "📌 NIGHT VIDEOS Help\n\n"
        "• Video bhejo\n"
        "• ▶️ Play Online button dabao\n"
        "• Android aur iPhone dono par play karo"
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
        "🎬 NIGHT VIDEOS\n"
        f"🆔 File ID: {file_id}",
        reply_markup=keyboard,
    )


# =========================
# TELEGRAM VIDEO
# =========================

@dp.message(F.video)
async def video_received(message: Message):

    await send_received(
        message,
        message.video.file_id,
        message.video.file_size or 0,
    )


# =========================
# DOCUMENT VIDEO
# =========================

@dp.message(F.document)
async def document_received(message: Message):

    document = message.document

    mime = document.mime_type or ""
    filename = (document.file_name or "").lower()

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
            "📄 यह video file नहीं है."
        )


# =========================
# HEALTH
# =========================

async def health(request: web.Request):

    return web.Response(
        text="NIGHT VIDEOS is running ✅"
    )


# =========================
# VIDEO PLAYER
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

<meta charset="utf-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<meta name="theme-color" content="#08080c">

<title>NIGHT VIDEOS</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: #08080c;
    color: white;
    font-family: Arial, sans-serif;
}}

.wrap {{
    min-height: 100vh;
    padding: 35px 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
}}

h1 {{
    margin: 15px 0 25px;
    font-size: 28px;
    text-align: center;
}}

.player {{
    width: 100%;
    max-width: 900px;
    background: #000;
    border-radius: 14px;
    overflow: hidden;
}}

video {{
    display: block;
    width: 100%;
    height: auto;
    max-height: 75vh;
    background: #000;
}}

.note {{
    margin-top: 16px;
    color: #999;
    font-size: 14px;
    text-align: center;
}}

</style>

</head>

<body>

<div class="wrap">

<h1>🎬 NIGHT VIDEOS</h1>

<div class="player">

<video
    id="videoPlayer"
    controls
    playsinline
    webkit-playsinline
    preload="metadata"
    controlsList="nodownload"
    src="{video_url}">
</video>

</div>

<div class="note">
▶️ NIGHT VIDEOS • Play Online
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
# RANGE VIDEO STREAM
# iOS + ANDROID SUPPORT
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

    # Get Telegram file path
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

    except Exception as e:

        print("Telegram API error:", e)

        return web.Response(
            text="Could not contact Telegram",
            status=502
        )

    if (
        not data.get("ok")
        or not data.get("result", {}).get("file_path")
    ):

        return web.Response(
            text="Telegram file not found",
            status=404
        )

    file_path = data["result"]["file_path"]

    telegram_file_url = (
        f"https://api.telegram.org/"
        f"file/bot{BOT_TOKEN}/{file_path}"
    )

    # Browser Range request
    range_header = request.headers.get("Range")

    headers = {}

    if range_header:
        headers["Range"] = range_header

    try:

        async with http_session.get(
            telegram_file_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=None),
        ) as upstream:

            if upstream.status not in (200, 206):

                return web.Response(
                    text="Could not download video from Telegram",
                    status=502
                )

            response_headers = {
                "Content-Type": upstream.headers.get(
                    "Content-Type",
                    "video/mp4"
                ),
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-store",
            }

            # Important for iOS/Safari
            if upstream.headers.get("Content-Length"):
                response_headers["Content-Length"] = (
                    upstream.headers["Content-Length"]
                )

            if upstream.headers.get("Content-Range"):
                response_headers["Content-Range"] = (
                    upstream.headers["Content-Range"]
                )

            response = web.StreamResponse(
                status=upstream.status,
                headers=response_headers,
            )

            await response.prepare(request)

            try:

                async for chunk in upstream.content.iter_chunked(
                    256 * 1024
                ):
                    await response.write(chunk)

            except (ConnectionResetError, asyncio.CancelledError):

                raise

            finally:

                try:
                    await response.write_eof()
                except Exception:
                    pass

            return response

    except asyncio.CancelledError:

        raise

    except Exception as e:

        print("Streaming error:", e)

        return web.Response(
            text="Video streaming failed",
            status=502
        )


# =========================
# WEB SERVER
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
        "NIGHT VIDEOS bot starting..."
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
