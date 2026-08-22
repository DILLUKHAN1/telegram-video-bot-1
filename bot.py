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
    WebAppInfo,
)


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

PORT = int(os.getenv("PORT", "8080"))

WEB_URL = os.getenv("WEB_URL")

# AdsGram Interstitial Block ID
ADSGRAM_BLOCK_ID = os.getenv(
    "ADSGRAM_BLOCK_ID",
    "int-44048"
)


if not WEB_URL:

    public_domain = os.getenv(
        "RAILWAY_PUBLIC_DOMAIN"
    )

    if public_domain:

        WEB_URL = (
            f"https://{public_domain}"
        )

    else:

        WEB_URL = (
            f"http://localhost:{PORT}"
        )


if not BOT_TOKEN:

    raise RuntimeError(
        "BOT_TOKEN environment variable is missing"
    )


# =========================================================
# BOT
# =========================================================

bot = Bot(
    BOT_TOKEN
)

dp = Dispatcher()

http_session = None


# =========================================================
# CREATE VIDEO URL
# =========================================================

def make_play_url(
    file_id: str
) -> str:

    return (
        f"{WEB_URL.rstrip('/')}/watch"
        f"?file_id={quote(file_id, safe='')}"
    )


# =========================================================
# START
# =========================================================

@dp.message(
    CommandStart()
)
async def start(
    message: Message
):

    await message.answer(
        "🎬 NIGHT VIDEOS\n\n"
        "Video ya video file bhejo.\n\n"
        "Main tumhe Play Online button dunga.\n\n"
        "▶️ Play Online = NIGHT VIDEOS Mini App\n\n"
        "/start - Start\n"
        "/help - Help"
    )


# =========================================================
# HELP
# =========================================================

@dp.message(
    Command("help")
)
async def help_cmd(
    message: Message
):

    await message.answer(
        "📌 NIGHT VIDEOS Help\n\n"
        "1️⃣ Bot ko video bhejo\n"
        "2️⃣ Play Online button dabao\n"
        "3️⃣ NIGHT VIDEOS Mini App open hoga\n"
        "4️⃣ Watch Video dabao\n"
        "5️⃣ Ad show hoga\n"
        "6️⃣ Ad ke baad video play hoga"
    )


# =========================================================
# SEND VIDEO RESULT
# =========================================================

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


    play_url = make_play_url(
        file_id
    )


    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="▶️ Play Online",

                    web_app=WebAppInfo(
                        url=play_url
                    )

                )

            ]

        ]

    )


    size_text = ""

    if size_bytes:

        size_text = (
            f"📁 Size: {size_mb:.2f} MB\n"
        )


    await message.answer(

        "🌙 NIGHT VIDEOS\n\n"
        "✅ Video received!\n"
        f"{size_text}\n"
        "👇 Video dekhne ke liye "
        "button dabao.",

        reply_markup=keyboard,

    )


# =========================================================
# VIDEO RECEIVED
# =========================================================

@dp.message(
    F.video
)
async def video_received(
    message: Message
):

    await send_received(

        message=message,

        file_id=message.video.file_id,

        size_bytes=(
            message.video.file_size
            or 0
        ),

    )


# =========================================================
# DOCUMENT / VIDEO FILE
# =========================================================

@dp.message(
    F.document
)
async def document_received(
    message: Message
):

    document = message.document

    mime = (
        document.mime_type
        or ""
    )

    filename = (
        document.file_name
        or ""
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
        or filename.endswith(
            video_extensions
        )

    ):

        await send_received(

            message=message,

            file_id=document.file_id,

            size_bytes=(
                document.file_size
                or 0
            ),

        )

    else:

        await message.answer(

            "📄 File received!\n\n"

            f"Name: "
            f"{document.file_name or 'unknown'}\n\n"

            "▶️ Play Online sirf video "
            "files ke liye available hai."

        )


# =========================================================
# HEALTH
# =========================================================

async def health(
    request: web.Request
):

    return web.Response(

        text=(
            "NIGHT VIDEOS "
            "is running ✅"
        )

    )


# =========================================================
# PLAYER
# =========================================================

async def player(
    request: web.Request
):

    file_id = request.query.get(
        "file_id"
    )


    if not file_id:

        return web.Response(

            text="Missing file_id",

            status=400

        )


    video_url = (

        f"{request.scheme}://"
        f"{request.host}"
        f"/stream?file_id="
        f"{quote(file_id, safe='')}"

    )


    html = f"""

<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width,
    initial-scale=1.0,
    viewport-fit=cover"
>

<meta
    name="theme-color"
    content="#050509"
>

<title>NIGHT VIDEOS</title>


<!-- Telegram Mini App SDK -->

<script
    src="https://telegram.org/js/telegram-web-app.js">
</script>


<!-- AdsGram SDK -->

<script
    src="https://sad.adsgram.ai/js/sad.min.js">
</script>


<style>

* {{
    box-sizing: border-box;
}}

html,
body {{

    margin: 0;
    padding: 0;

    width: 100%;
    min-height: 100%;

    background:
        radial-gradient(
            circle at top,
            #17172a 0%,
            #08080d 45%,
            #030305 100%
        );

    color: white;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;

}}

body {{
    min-height: 100vh;
}}

.container {{

    width: 100%;
    min-height: 100vh;

    display: flex;

    flex-direction: column;

    align-items: center;

    padding:
        calc(
            22px +
            env(safe-area-inset-top)
        )
        14px
        calc(
            28px +
            env(safe-area-inset-bottom)
        );

}}

.logo {{

    width: 74px;
    height: 74px;

    border-radius: 50%;

    display: flex;

    align-items: center;
    justify-content: center;

    background:
        linear-gradient(
            135deg,
            #8b2cff,
            #4c00ff
        );

    box-shadow:
        0 0 30px
        rgba(
            126,
            55,
            255,
            0.45
        );

    font-size: 36px;

    margin-top: 8px;
    margin-bottom: 14px;

}}

.title {{

    margin: 0;

    font-size: 30px;

    font-weight: 800;

    letter-spacing: 0.5px;

    text-align: center;

}}

.subtitle {{

    margin-top: 7px;

    color: #a7a7b5;

    font-size: 14px;

    text-align: center;

}}

.player-card {{

    width: 100%;

    max-width: 1000px;

    margin-top: 28px;

    padding: 10px;

    background: #0d0d12;

    border:
        1px solid #252531;

    border-radius: 20px;

    box-shadow:
        0 20px 60px
        rgba(0,0,0,0.45);

    position: relative;

}}

video {{

    display: block;

    width: 100%;

    max-height: 75vh;

    background: black;

    border-radius: 14px;

    object-fit: contain;

}}

.watch-overlay {{

    position: absolute;

    inset: 10px;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        rgba(0,0,0,0.45);

    border-radius: 14px;

    z-index: 10;

}}

.watch-button {{

    border: 0;

    border-radius: 999px;

    padding:
        15px 28px;

    font-size: 16px;

    font-weight: 800;

    color: white;

    background:
        linear-gradient(
            135deg,
            #8b2cff,
            #4c00ff
        );

    box-shadow:
        0 10px 35px
        rgba(
            112,
            40,
            255,
            0.45
        );

}}

.watch-button:disabled {{

    opacity: 0.6;

}}

.status {{

    width: 100%;

    max-width: 1000px;

    margin-top: 15px;

    padding: 12px 15px;

    text-align: center;

    color: #a9a9b5;

    font-size: 13px;

}}

.brand {{

    margin-top: auto;

    padding-top: 35px;

    color: #686875;

    font-size: 12px;

    text-align: center;

}}

.error {{

    color: #ff7b7b;

}}

</style>

</head>


<body>


<div class="container">


    <div class="logo">
        🎬
    </div>


    <h1 class="title">
        NIGHT VIDEOS
    </h1>


    <div class="subtitle">
        🌙 Watch videos online
    </div>


    <div class="player-card">


        <video

            id="videoPlayer"

            controls

            playsinline

            webkit-playsinline

            preload="metadata"

            controlsList="nodownload"

        >

            <source

                src="{video_url}"

                type="video/mp4"

            >

            Your browser does not support
            HTML5 video.

        </video>


        <div
            id="watchOverlay"
            class="watch-overlay"
        >

            <button
                id="watchButton"
                class="watch-button"
            >

                ▶️ Watch Video

            </button>

        </div>


    </div>


    <div
        id="status"
        class="status"
    >

        👆 Watch Video dabao

    </div>


    <div class="brand">

        NIGHT VIDEOS

    </div>


</div>


<script>


// ========================================================
// TELEGRAM WEB APP
// ========================================================

try {{

    if (
        window.Telegram &&
        window.Telegram.WebApp
    ) {{

        window.Telegram.WebApp.ready();

        window.Telegram.WebApp.expand();

    }}

}} catch (e) {{

    console.log(
        "Telegram SDK error:",
        e
    );

}}


// ========================================================
// VIDEO
// ========================================================

const video =
    document.getElementById(
        "videoPlayer"
    );


const status =
    document.getElementById(
        "status"
    );


const overlay =
    document.getElementById(
        "watchOverlay"
    );


const watchButton =
    document.getElementById(
        "watchButton"
    );


// ========================================================
// ADSGRAM
// ========================================================

let adController = null;


try {{

    if (
        window.Adsgram
    ) {{

        adController =
            window.Adsgram.init({{

                blockId:
                    "{ADSGRAM_BLOCK_ID}",

                debug: false

            }});

        console.log(
            "AdsGram initialized"
        );

    }} else {{

        console.error(
            "AdsGram SDK not loaded"
        );

    }}

}} catch (error) {{

    console.error(
        "AdsGram init error:",
        error
    );

}}


// ========================================================
// SHOW AD
// ========================================================

async function showAd() {{

    if (!adController) {{

        console.warn(
            "AdsGram controller unavailable"
        );

        return false;

    }}


    try {{

        status.textContent =
            "📢 Advertisement...";

        watchButton.disabled =
            true;


        await adController.show();


        console.log(
            "AdsGram ad completed"
        );


        return true;

    }} catch (error) {{

        console.warn(
            "AdsGram ad error:",
            error
        );


        // If no ad is available,
        // continue with the video.

        return false;

    }} finally {{

        watchButton.disabled =
            false;

    }}

}}


// ========================================================
// START VIDEO
// ========================================================

async function startVideo() {{

    watchButton.disabled =
        true;


    status.textContent =
        "📢 Loading advertisement...";


    // ====================================================
    // ADSGRAM
    // ====================================================

    await showAd();


    // ====================================================
    // HIDE OVERLAY
    // ====================================================

    overlay.style.display =
        "none";


    status.textContent =
        "⏳ Loading video...";


    // ====================================================
    // PLAY
    // ====================================================

    try {{

        await video.play();


        status.textContent =
            "▶️ NIGHT VIDEOS";

    }} catch (error) {{

        console.warn(
            "Autoplay/play error:",
            error
        );


        status.textContent =
            "▶️ Press Play to start video";

    }}

}}


// ========================================================
// BUTTON
// ========================================================

watchButton.addEventListener(
    "click",
    startVideo
);


// ========================================================
// VIDEO EVENTS
// ========================================================

video.addEventListener(
    "loadstart",
    function() {{

        status.textContent =
            "⏳ Loading video...";

    }}
);


video.addEventListener(
    "loadedmetadata",
    function() {{

        status.textContent =
            "👆 Watch Video dabao";

    }}
);


video.addEventListener(
    "playing",
    function() {{

        status.textContent =
            "▶️ NIGHT VIDEOS";

    }}
);


video.addEventListener(
    "waiting",
    function() {{

        status.textContent =
            "⏳ Buffering...";

    }}
);


video.addEventListener(
    "canplay",
    function() {{

        if (
            overlay.style.display
            !== "none"
        ) {{

            status.textContent =
                "👆 Watch Video dabao";

        }}

    }}
);


video.addEventListener(
    "error",
    function() {{

        status.textContent =
            "❌ Video could not be played";

        status.classList.add(
            "error"
        );

    }}
);


</script>


</body>

</html>

"""


    return web.Response(

        text=html,

        content_type="text/html"

    )


# =========================================================
# VIDEO STREAM
# =========================================================

async def stream_video(
    request: web.Request
):

    global http_session


    file_id = request.query.get(
        "file_id"
    )


    if not file_id:

        return web.Response(

            text="Missing file_id",

            status=400

        )


    # =====================================================
    # SESSION
    # =====================================================

    if (

        http_session is None
        or http_session.closed

    ):

        http_session = (
            aiohttp.ClientSession()
        )


    # =====================================================
    # TELEGRAM getFile
    # =====================================================

    api_url = (

        "https://api.telegram.org/"
        f"bot{BOT_TOKEN}/getFile"

    )


    try:

        async with http_session.get(

            api_url,

            params={{
                "file_id": file_id
            }},

            timeout=aiohttp.ClientTimeout(
                total=30
            ),

        ) as response:


            data = (
                await response.json()
            )


    except Exception as error:

        print(
            "Telegram getFile error:",
            error
        )


        return web.Response(

            text=(
                "Could not contact Telegram"
            ),

            status=502

        )


    # =====================================================
    # CHECK
    # =====================================================

    if (

        not data.get("ok")
        or not data.get(
            "result",
            {}
        ).get("file_path")

    ):

        return web.Response(

            text=(
                "Telegram could not "
                "download this file."
            ),

            status=404

        )


    file_path = (
        data["result"]["file_path"]
    )


    # =====================================================
    # TELEGRAM FILE URL
    # =====================================================

    telegram_file_url = (

        "https://api.telegram.org/"
        f"file/bot{BOT_TOKEN}/"
        f"{file_path}"

    )


    # =====================================================
    # STREAM
    # =====================================================

    try:

        async with http_session.get(

            telegram_file_url,

            timeout=aiohttp.ClientTimeout(
                total=None
            ),

        ) as upstream:


            if upstream.status != 200:

                return web.Response(

                    text=(
                        "Could not download "
                        "video from Telegram."
                    ),

                    status=502

                )


            content_type = (

                upstream.headers.get(
                    "Content-Type",
                    "video/mp4"
                )

            )


            content_length = (

                upstream.headers.get(
                    "Content-Length"
                )

            )


            headers = {{

                "Content-Type":
                    content_type,

                "Cache-Control":
                    "no-store",

                "Accept-Ranges":
                    "none",

            }}


            if content_length:

                headers[
                    "Content-Length"
                ] = content_length


            response = (
                web.StreamResponse(
                    status=200,
                    headers=headers
                )
            )


            await response.prepare(
                request
            )


            async for chunk in (

                upstream.content
                .iter_chunked(
                    1024 * 256
                )

            ):

                await response.write(
                    chunk
                )


            await response.write_eof()


            return response


    except asyncio.CancelledError:

        raise


    except Exception as error:

        print(
            "Streaming error:",
            error
        )


        return web.Response(

            text=(
                "Video streaming failed"
            ),

            status=502

        )


# =========================================================
# WEB SERVER
# =========================================================

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


    runner = web.AppRunner(
        app
    )


    await runner.setup()


    site = web.TCPSite(

        runner,

        "0.0.0.0",

        PORT

    )


    await site.start()


    print(
        "================================"
    )

    print(
        "NIGHT VIDEOS WEB SERVER STARTED"
    )

    print(
        f"PORT: {PORT}"
    )

    print(
        f"WEB_URL: {WEB_URL}"
    )

    print(
        f"ADSGRAM: {ADSGRAM_BLOCK_ID}"
    )

    print(
        "================================"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    await start_web_server()


    print(
        "NIGHT VIDEOS BOT STARTING..."
    )


    try:

        await dp.start_polling(
            bot
        )

    finally:

        if (
            http_session
            and not http_session.closed
        ):

            await http_session.close()


        await bot.session.close()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "Bot stopped."
        )
