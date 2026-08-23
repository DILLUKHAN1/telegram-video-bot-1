import os
import asyncio
import html
from urllib.parse import quote

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

from pyrogram import Client


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

PORT = int(os.getenv("PORT", "8080"))

WEB_URL = os.getenv("WEB_URL")

ADSGRAM_BLOCK_ID = os.getenv(
    "ADSGRAM_BLOCK_ID",
    "int-44048"
)


# =========================================================
# CHECK VARIABLES
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is missing"
    )

if not API_ID:
    raise RuntimeError(
        "API_ID environment variable is missing"
    )

if not API_HASH:
    raise RuntimeError(
        "API_HASH environment variable is missing"
    )


# =========================================================
# WEB URL
# =========================================================

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


# =========================================================
# BOT
# =========================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# =========================================================
# PYROGRAM MTProto
# =========================================================

mtproto = Client(
    "night_videos_mtproto",

    api_id=int(API_ID),

    api_hash=API_HASH,

    bot_token=BOT_TOKEN,

    no_updates=True,

    in_memory=True,
)


# =========================================================
# STREAM SETTINGS
#
# Pyrogram stream_media max chunk = 1 MiB
# =========================================================

CHUNK_SIZE = 1024 * 1024


# =========================================================
# CREATE PLAY URL
# =========================================================

def make_play_url(
    file_id: str,
    size_bytes: int = 0,
    mime_type: str = "video/mp4",
    file_name: str = "video.mp4",
) -> str:

    return (
        f"{WEB_URL.rstrip('/')}"
        f"/watch?"
        f"file_id={quote(file_id, safe='')}"
        f"&size={int(size_bytes)}"
        f"&mime={quote(mime_type, safe='')}"
        f"&name={quote(file_name, safe='')}"
    )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "🎬 NIGHT VIDEOS\n\n"
        "Video ya video file bhejo.\n\n"
        "Forward ki hui video bhi supported hai.\n\n"
        "Main tumhe ▶️ Play Online button dunga.\n\n"
        "▶️ Play Online = NIGHT VIDEOS Mini App\n\n"
        "/start - Start\n"
        "/help - Help"
    )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_cmd(message: Message):

    await message.answer(
        "📌 NIGHT VIDEOS HELP\n\n"

        "1️⃣ Video bhejo ya forward karo\n\n"
        "2️⃣ Bot Play Online button dega\n\n"
        "3️⃣ Play Online dabao\n\n"
        "4️⃣ AdsGram ad show hoga\n\n"
        "5️⃣ Ad ke baad video automatically play hoga\n\n"
        "6️⃣ Seek / Range requests supported hain\n\n"
        "🚀 Large video streaming enabled"
    )


# =========================================================
# SEND VIDEO RESULT
# =========================================================

async def send_received(
    message: Message,
    file_id: str,
    size_bytes: int = 0,
    mime_type: str = "video/mp4",
    file_name: str = "video.mp4",
):

    size_mb = (
        size_bytes / (1024 * 1024)
        if size_bytes
        else 0
    )

    play_url = make_play_url(
        file_id=file_id,
        size_bytes=size_bytes,
        mime_type=mime_type,
        file_name=file_name,
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️ Watch Now",
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

        "✅ Video received!\n\n"

        f"{size_text}"

        "🚀 Large video streaming enabled\n"

        "⏩ Range / Seek supported\n\n"

        "👇 Video dekhne ke liye "
        "Watch Now dabao.",
        reply_markup=keyboard,
    )


# =========================================================
# NORMAL VIDEO
#
# Forwarded videos also arrive here.
# =========================================================

@dp.message(F.video)
async def video_received(message: Message):

    video = message.video

    await send_received(
        message=message,

        file_id=video.file_id,

        size_bytes=(
            video.file_size or 0
        ),

        mime_type=(
            video.mime_type
            or "video/mp4"
        ),

        file_name=(
            video.file_name
            or "video.mp4"
        ),
    )


# =========================================================
# DOCUMENT VIDEO
#
# Forwarded MKV/MP4/etc. files also arrive here.
# =========================================================

@dp.message(F.document)
async def document_received(message: Message):

    document = message.document

    mime = (
        document.mime_type
        or ""
    )

    filename = (
        document.file_name
        or "video"
    )

    filename_lower = filename.lower()

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
        ".ts",
        ".flv",
    )

    is_video = (
        mime.startswith("video/")
        or filename_lower.endswith(
            video_extensions
        )
    )

    if is_video:

        await send_received(
            message=message,

            file_id=document.file_id,

            size_bytes=(
                document.file_size or 0
            ),

            mime_type=(
                mime
                or "video/mp4"
            ),

            file_name=filename,
        )

    else:

        await message.answer(
            "📄 File received!\n\n"
            f"Name: {filename}\n\n"
            "▶️ Watch Now sirf "
            "video files ke liye available hai."
        )


# =========================================================
# HEALTH
# =========================================================

async def health(request: web.Request):

    return web.Response(
        text="NIGHT VIDEOS is running ✅"
    )


# =========================================================
# PLAYER
# =========================================================

async def player(request: web.Request):

    file_id = request.query.get(
        "file_id"
    )

    if not file_id:

        return web.Response(
            text="Missing file_id",
            status=400
        )

    try:

        size = int(
            request.query.get(
                "size",
                "0"
            )
        )

    except ValueError:

        size = 0

    mime_type = (
        request.query.get(
            "mime",
            "video/mp4"
        )
    )

    file_name = (
        request.query.get(
            "name",
            "video.mp4"
        )
    )

    # -----------------------------------------------------
    # Escape values before putting them inside HTML
    # -----------------------------------------------------

    safe_mime = html.escape(
        mime_type,
        quote=True
    )

    safe_name = html.escape(
        file_name,
        quote=True
    )

    video_url = (
        f"{request.scheme}://"
        f"{request.host}"
        f"/stream?"
        f"file_id="
        f"{quote(file_id, safe='')}"
        f"&size={size}"
        f"&mime="
        f"{quote(mime_type, safe='')}"
        f"&name="
        f"{quote(file_name, safe='')}"
    )

    safe_video_url = html.escape(
        video_url,
        quote=True
    )


    # =====================================================
    # HTML
    # =====================================================

    html_page = f"""
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


<script
    src="https://telegram.org/js/telegram-web-app.js">
</script>


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
        calc(22px + env(safe-area-inset-top))
        14px
        calc(28px + env(safe-area-inset-bottom));
}}

.logo {{
    width: 72px;
    height: 72px;

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
        rgba(126,55,255,0.45);

    font-size: 34px;

    margin-top: 8px;

    margin-bottom: 14px;
}}

.title {{
    margin: 0;

    font-size: 29px;

    font-weight: 800;

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

    margin-top: 25px;

    padding: 9px;

    background: #0d0d12;

    border: 1px solid #252531;

    border-radius: 20px;

    box-shadow:
        0 20px 60px
        rgba(0,0,0,0.45);
}}

video {{
    display: block;

    width: 100%;

    max-height: 72vh;

    background: black;

    border-radius: 14px;

    object-fit: contain;
}}

.play-button {{
    margin-top: 16px;

    padding: 15px 28px;

    border: 0;

    border-radius: 15px;

    color: white;

    font-size: 17px;

    font-weight: 700;

    background:
        linear-gradient(
            135deg,
            #8b2cff,
            #4c00ff
        );

    box-shadow:
        0 10px 30px
        rgba(100,40,255,0.25);
}}

.play-button:disabled {{
    opacity: 0.65;
}}

.status {{
    width: 100%;

    max-width: 1000px;

    margin-top: 15px;

    padding: 12px 15px;

    text-align: center;

    color: #aaaab7;

    font-size: 13px;
}}

.info {{
    margin-top: 10px;

    color: #777783;

    font-size: 11px;

    text-align: center;
}}

.brand {{
    margin-top: auto;

    padding-top: 35px;

    color: #686875;

    font-size: 12px;

    text-align: center;
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
                src="{safe_video_url}"
                type="{safe_mime}"
            >

            Your browser does not support
            HTML5 video.

        </video>

    </div>


    <button
        id="playButton"
        class="play-button"
    >
        ▶️ Play Video
    </button>


    <div
        id="status"
        class="status"
    >
        🎬 Press Play Video
    </div>


    <div class="info">
        📡 MTProto • Range • Seek • Large Files
    </div>


    <div class="brand">
        NIGHT VIDEOS
    </div>


</div>


<script>

/* =====================================================
   ELEMENTS
===================================================== */

const video =
    document.getElementById(
        "videoPlayer"
    );


const status =
    document.getElementById(
        "status"
    );


const playButton =
    document.getElementById(
        "playButton"
    );


/* =====================================================
   TELEGRAM MINI APP
===================================================== */

try {{

    if (
        window.Telegram &&
        window.Telegram.WebApp
    ) {{

        Telegram.WebApp.ready();

        Telegram.WebApp.expand();

    }}

}} catch (error) {{

    console.log(
        "Telegram WebApp error:",
        error
    );

}}


/* =====================================================
   ADSGRAM
===================================================== */

let adController = null;


try {{

    if (
        window.Adsgram &&
        "{ADSGRAM_BLOCK_ID}"
    ) {{

        adController =
            window.Adsgram.init({{
                blockId:
                    "{ADSGRAM_BLOCK_ID}"
            }});

    }}

}} catch (error) {{

    console.log(
        "AdsGram initialization error:",
        error
    );

}}


/* =====================================================
   SHOW AD
===================================================== */

async function showAd() {{

    if (!adController) {{

        return true;

    }}


    try {{

        status.textContent =
            "📺 Advertisement loading...";


        /*
         * Wait until AdsGram resolves.
         *
         * For Interstitial:
         * the promise can resolve when the ad
         * finishes OR is closed.
         */

        await adController.show();


        status.textContent =
            "✅ Advertisement finished";


        return true;


    }} catch (error) {{

        console.log(
            "AdsGram error:",
            error
        );


        /*
         * If advertisement is unavailable,
         * continue to the video.
         */

        status.textContent =
            "▶️ Starting video...";


        return true;

    }}

}}


/* =====================================================
   START VIDEO
===================================================== */

async function startVideo() {{

    try {{

        status.textContent =
            "▶️ Starting video...";


        /*
         * Load metadata first.
         */

        video.load();


        /*
         * Wait a little for browser
         * to prepare the media.
         */

        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    100
                )
        );


        await video.play();


        playButton.style.display =
            "none";


        status.textContent =
            "▶️ NIGHT VIDEOS";


    }} catch (error) {{

        console.log(
            "Video play error:",
            error
        );


        status.textContent =
            "▶️ Tap the video to start";


        playButton.disabled =
            false;


        playButton.textContent =
            "▶️ Play Video";

    }}

}}


/* =====================================================
   PLAY BUTTON
===================================================== */

playButton.addEventListener(
    "click",
    async function() {{

        playButton.disabled =
            true;

        playButton.textContent =
            "⏳ Loading...";


        /*
         * IMPORTANT:
         *
         * User clicks Play
         *       ↓
         * AdsGram
         *       ↓
         * Ad finishes/closes
         *       ↓
         * Video starts automatically
         */

        await showAd();


        await startVideo();

    }}
);


/* =====================================================
   VIDEO EVENTS
===================================================== */

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
            "✅ Video ready";

    }}
);


video.addEventListener(
    "canplay",
    function() {{

        status.textContent =
            "▶️ Ready to play";

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
    "pause",
    function() {{

        if (
            !video.ended
        ) {{

            status.textContent =
                "⏸️ Paused";

        }}

    }}
);


video.addEventListener(
    "ended",
    function() {{

        status.textContent =
            "✅ Video finished";

    }}
);


video.addEventListener(
    "error",
    function() {{

        console.log(
            "Video error:",
            video.error
        );


        status.textContent =
            "❌ Video could not be played";

    }}
);

</script>


</body>

</html>
"""


    return web.Response(
        text=html_page,
        content_type="text/html"
    )


# =========================================================
# RANGE PARSER
# =========================================================

def parse_range(
    range_header: str,
    file_size: int
):

    if not range_header:
        return None

    if not range_header.startswith(
        "bytes="
    ):
        return None

    value = (
        range_header[
            len("bytes="):
        ]
        .strip()
    )

    if "," in value:

        value = value.split(
            ",",
            1
        )[0]

    parts = value.split(
        "-",
        1
    )

    if len(parts) != 2:
        return None

    start_text = parts[0].strip()
    end_text = parts[1].strip()

    try:

        # -------------------------------------------------
        # Suffix range
        # Example: bytes=-500000
        # -------------------------------------------------

        if start_text == "":

            suffix_length = int(
                end_text
            )

            if suffix_length <= 0:
                return None

            suffix_length = min(
                suffix_length,
                file_size
            )

            start = (
                file_size
                - suffix_length
            )

            end = file_size - 1

            return start, end


        # -------------------------------------------------
        # Normal range
        # Example: bytes=1000-5000
        # -------------------------------------------------

        start = int(
            start_text
        )

        if start < 0:
            return None

        if start >= file_size:
            return None

        if end_text == "":

            end = file_size - 1

        else:

            end = int(
                end_text
            )

            end = min(
                end,
                file_size - 1
            )

        if end < start:
            return None

        return start, end

    except ValueError:

        return None


# =========================================================
# STREAM VIDEO
# =========================================================

async def stream_video(
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


    # =====================================================
    # FILE SIZE
    # =====================================================

    try:

        file_size = int(
            request.query.get(
                "size",
                "0"
            )
        )

    except ValueError:

        file_size = 0


    if file_size <= 0:

        return web.Response(
            text="Invalid file size",
            status=400
        )


    # =====================================================
    # MIME
    # =====================================================

    mime_type = (
        request.query.get(
            "mime",
            "video/mp4"
        )
    )


    # =====================================================
    # FILE NAME
    # =====================================================

    file_name = (
        request.query.get(
            "name",
            "video.mp4"
        )
    )


    # Prevent header injection
    file_name = (
        file_name
        .replace("\r", "")
        .replace("\n", "")
        .replace('"', "")
    )


    # =====================================================
    # RANGE
    # =====================================================

    range_header = (
        request.headers.get(
            "Range"
        )
    )


    requested_range = parse_range(
        range_header,
        file_size
    )


    # =====================================================
    # HEAD
    # =====================================================

    if request.method == "HEAD":

        headers = {

            "Content-Type":
                mime_type,

            "Content-Length":
                str(file_size),

            "Accept-Ranges":
                "bytes",

            "Content-Disposition":
                (
                    f'inline; filename="{file_name}"'
                ),

            "Cache-Control":
                "no-cache",

        }

        return web.Response(
            status=200,
            headers=headers
        )


    # =====================================================
    # DETERMINE BYTE RANGE
    # =====================================================

    if requested_range:

        start_byte, end_byte = (
            requested_range
        )

        content_length = (
            end_byte
            - start_byte
            + 1
        )

        status_code = 206

    else:

        start_byte = 0

        end_byte = file_size - 1

        content_length = file_size

        status_code = 200


    # =====================================================
    # RESPONSE HEADERS
    # =====================================================

    headers = {

        "Content-Type":
            mime_type,

        "Content-Length":
            str(content_length),

        "Accept-Ranges":
            "bytes",

        "Content-Disposition":
            (
                f'inline; filename="{file_name}"'
            ),

        "Cache-Control":
            "no-cache, no-store",

        "X-Content-Type-Options":
            "nosniff",

        "Access-Control-Allow-Origin":
            "*",

    }


    if status_code == 206:

        headers["Content-Range"] = (
            f"bytes "
            f"{start_byte}-"
            f"{end_byte}/"
            f"{file_size}"
        )


    response = web.StreamResponse(
        status=status_code,
        headers=headers
    )


    await response.prepare(
        request
    )


    # =====================================================
    # PYROGRAM CHUNK POSITION
    #
    # Pyrogram:
    # offset = number of 1 MiB chunks to skip
    # =====================================================

    first_chunk = (
        start_byte
        // CHUNK_SIZE
    )


    inner_offset = (
        start_byte
        % CHUNK_SIZE
    )


    bytes_remaining = (
        content_length
    )


    chunks_needed = (
        (
            inner_offset
            + content_length
            + CHUNK_SIZE
            - 1
        )
        // CHUNK_SIZE
    )


    # =====================================================
    # STREAM
    # =====================================================

    try:

        chunk_number = 0


        async for chunk in mtproto.stream_media(
            file_id,
            offset=first_chunk,
            limit=chunks_needed,
        ):

            if bytes_remaining <= 0:
                break


            # ---------------------------------------------
            # Remove bytes before requested range
            # ---------------------------------------------

            if chunk_number == 0:

                if inner_offset:

                    chunk = chunk[
                        inner_offset:
                    ]


            # ---------------------------------------------
            # Don't exceed requested length
            # ---------------------------------------------

            if len(chunk) > bytes_remaining:

                chunk = chunk[
                    :bytes_remaining
                ]


            if not chunk:
                break


            await response.write(
                chunk
            )


            bytes_remaining -= (
                len(chunk)
            )


            chunk_number += 1


            if bytes_remaining <= 0:
                break


        await response.write_eof()


        return response


    except asyncio.CancelledError:

        # Browser closed/seeked connection.
        # Normal behavior.

        raise


    except Exception as error:

        print(
            "======================================"
        )

        print(
            "MTProto STREAMING ERROR"
        )

        print(
            repr(error)
        )

        print(
            "======================================"
        )


        try:

            await response.write_eof()

        except Exception:

            pass


        return response


# =========================================================
# WEB SERVER
# =========================================================

async def start_web_server():

    app = web.Application(
        client_max_size=10 * 1024 * 1024 * 1024
    )


    # HOME
    app.router.add_get(
        "/",
        health
    )


    # HEALTH
    app.router.add_get(
        "/health",
        health
    )


    # PLAYER
    app.router.add_get(
        "/watch",
        player
    )


    # STREAM GET
    app.router.add_route(
        "GET",
        "/stream",
        stream_video
    )


    # STREAM HEAD
    app.router.add_route(
        "HEAD",
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
        "======================================"
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
        "MTProto: ENABLED"
    )

    print(
        "LARGE STREAMING: ENABLED"
    )

    print(
        "RANGE / SEEK: ENABLED"
    )

    print(
        "FORWARDED VIDEO: ENABLED"
    )

    print(
        f"AdsGram Block: {ADSGRAM_BLOCK_ID}"
    )

    print(
        "======================================"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    # =====================================================
    # START MTProto
    # =====================================================

    print(
        "Starting Telegram MTProto client..."
    )


    await mtproto.start()


    print(
        "Telegram MTProto client started ✅"
    )


    # =====================================================
    # START WEB SERVER
    # =====================================================

    await start_web_server()


    # =====================================================
    # START BOT
    # =====================================================

    print(
        "Starting NIGHT VIDEOS bot..."
    )


    try:

        await dp.start_polling(
            bot
        )

    finally:

        print(
            "Stopping NIGHT VIDEOS..." 
        )


        try:

            await bot.session.close()

        except Exception:

            pass


        try:

            await mtproto.stop()

        except Exception:

            pass


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
            "NIGHT VIDEOS stopped."
        )
