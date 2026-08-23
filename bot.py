import os
import asyncio
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

# =========================================================
# ADSGRAM
#
# Interstitial example:
# ADSGRAM_BLOCK_ID=int-44048
#
# IMPORTANT:
# For "must watch ad till end", use a REWARD block ID
# from AdsGram instead of an int-xxxx Interstitial block.
# =========================================================

ADSGRAM_BLOCK_ID = os.getenv(
    "ADSGRAM_BLOCK_ID",
    "int-44048"
)


# =========================================================
# STREAM LIMITS
# =========================================================

CHUNK_SIZE = 1024 * 1024

# Maximum HTTP range returned per request.
# Browser will request more ranges while seeking.
MAX_RANGE_REQUEST = 16 * 1024 * 1024

# Target support: up to 2 GB.
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024


# =========================================================
# CHECK ENVIRONMENT VARIABLES
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
# AIROGRAM
# =========================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# =========================================================
# PYROGRAM MTProto
#
# Aiogram:
#   receives bot messages
#
# Pyrogram:
#   streams Telegram files
#
# This avoids using Bot API getFile() for video streaming.
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
# CREATE WATCH URL
# =========================================================

def make_play_url(
    file_id: str,
    size_bytes: int = 0,
    mime_type: str = "video/mp4",
    file_name: str = "video.mp4",
) -> str:

    params = (
        f"file_id={quote(file_id, safe='')}"
        f"&size={int(size_bytes)}"
        f"&mime={quote(mime_type, safe='')}"
        f"&name={quote(file_name, safe='')}"
    )

    return (
        f"{WEB_URL.rstrip('/')}"
        f"/watch?{params}"
    )


# =========================================================
# WATCH NOW KEYBOARD
# =========================================================

def watch_keyboard(
    file_id: str,
    size_bytes: int,
    mime_type: str,
    file_name: str,
) -> InlineKeyboardMarkup:

    play_url = make_play_url(
        file_id=file_id,
        size_bytes=size_bytes,
        mime_type=mime_type,
        file_name=file_name,
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👉 𝐖𝐀𝐓𝐂𝐇 𝐍𝐎𝐖 👈",
                    web_app=WebAppInfo(
                        url=play_url
                    ),
                )
            ]
        ]
    )


# =========================================================
# SEND ONLY WATCH NOW
#
# Telegram does not allow a bot to attach a new inline
# keyboard directly to another user's media message.
#
# Therefore the bot replies with an invisible character
# and the WATCH NOW button.
#
# No size/name/details are shown.
# =========================================================

async def send_watch_button(
    message: Message,
    file_id: str,
    size_bytes: int = 0,
    mime_type: str = "video/mp4",
    file_name: str = "video.mp4",
):

    # Protect against obviously invalid sizes.
    if size_bytes > MAX_FILE_SIZE:

        await message.answer(
            "❌ Ye file 2 GB se badi hai."
        )

        return

    keyboard = watch_keyboard(
        file_id=file_id,
        size_bytes=size_bytes,
        mime_type=mime_type,
        file_name=file_name,
    )

    # Invisible Unicode character.
    # Only the inline WATCH NOW button will be visible.
    invisible_text = "\u2063"

    try:

        await message.reply(
            invisible_text,
            reply_markup=keyboard,
        )

    except Exception as error:

        print(
            "WATCH BUTTON ERROR:",
            repr(error)
        )

        # Fallback
        await message.answer(
            "👉 𝐖𝐀𝐓𝐂𝐇 𝐍𝐎𝐖 👈",
            reply_markup=keyboard,
        )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(
    message: Message
):

    await message.answer(
        "🎬 NIGHT VIDEOS\n\n"
        "Video bhejo ya forward karo.\n\n"
        "👇 Uske niche WATCH NOW button milega."
    )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_cmd(
    message: Message
):

    await message.answer(
        "📌 NIGHT VIDEOS\n\n"
        "1️⃣ Video bhejo ya forward karo\n"
        "2️⃣ WATCH NOW dabao\n"
        "3️⃣ Ads show hoga\n"
        "4️⃣ Ad complete hone ke baad video play hoga\n"
        "5️⃣ Large videos ke liye MTProto streaming\n"
        "6️⃣ Range / Seek supported"
    )


# =========================================================
# VIDEO RECEIVED
#
# This also handles forwarded videos because Telegram sends
# the video object in the update.
# =========================================================

@dp.message(F.video)
async def video_received(
    message: Message
):

    video = message.video

    await send_watch_button(
        message=message,
        file_id=video.file_id,
        size_bytes=video.file_size or 0,
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
# DOCUMENT RECEIVED
#
# Supports:
# MP4
# MKV
# WEBM
# MOV
# M4V
# AVI
# MPEG
# MPG
# 3GP
# TS
# FLV
# =========================================================

@dp.message(F.document)
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
        or "video"
    )

    filename_lower = (
        filename.lower()
    )

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
        ".m2ts",
        ".mts",
    )

    is_video = (
        mime.startswith("video/")
        or filename_lower.endswith(
            video_extensions
        )
    )

    if is_video:

        await send_watch_button(
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
            "📄 Ye video file nahi hai."
        )


# =========================================================
# HEALTH
# =========================================================

async def health(
    request: web.Request
):

    return web.Response(
        text="NIGHT VIDEOS is running ✅"
    )


# =========================================================
# PARSE HTTP RANGE
# =========================================================

def parse_range(
    range_header: str,
    file_size: int,
):

    if not range_header:

        return None

    if not range_header.startswith(
        "bytes="
    ):

        return None

    value = (
        range_header
       .replace(
            "bytes=",
            "",
            1,
        )
        .strip()
    )

    # Browser normally sends one range.
    # If multiple ranges are sent, use first one.
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

        # ---------------------------------------------
        # Suffix range
        # Example:
        # bytes=-500000
        # ---------------------------------------------

        if start_text == "":

            suffix_length = int(
                end_text
            )

            if suffix_length <= 0:

                return None

            if suffix_length > file_size:

                suffix_length = file_size

            start = (
                file_size
                - suffix_length
            )

            end = (
                file_size - 1
            )

        else:

            start = int(
                start_text
            )

            if start < 0:

                return None

            if start >= file_size:

                return None

            # -----------------------------------------
            # Open ended range
            # Example:
            # bytes=500000-
            # -----------------------------------------

            if end_text == "":

                end = (
                    file_size - 1
                )

            else:

                end = int(
                    end_text
                )

                if end >= file_size:

                    end = (
                        file_size - 1
                    )

            if end < start:

                return None

        # ---------------------------------------------
        # Limit each HTTP response.
        # Browser will make additional Range requests.
        # ---------------------------------------------

        maximum_end = (
            start
            + MAX_RANGE_REQUEST
            - 1
        )

        if end > maximum_end:

            end = maximum_end

        return start, end

    except ValueError:

        return None


# =========================================================
# MINI APP PLAYER
# =========================================================

async def player(
    request: web.Request
):

    file_id = (
        request.query.get(
            "file_id"
        )
    )

    if not file_id:

        return web.Response(
            text="Missing file_id",
            status=400,
        )

    try:

        size = int(
            request.query.get(
                "size",
                "0",
            )
        )

    except ValueError:

        size = 0

    if size <= 0:

        return web.Response(
            text="Invalid file size",
            status=400,
        )

    if size > MAX_FILE_SIZE:

        return web.Response(
            text="File is larger than 2 GB",
            status=413,
        )

    mime_type = (
        request.query.get(
            "mime",
            "video/mp4",
        )
    )

    file_name = (
        request.query.get(
            "name",
            "video.mp4",
        )
    )

    # URL used by HTML5 video element.
    stream_url = (
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

    # =====================================================
    # LUXURY MINI APP
    #
    # IMPORTANT:
    # The video source is NOT loaded immediately.
    #
    # WATCH NOW -> ADSGRAM -> AD FINISHED -> set src ->
    # video.load() -> video.play()
    #
    # This prevents the video from starting before the ad.
    # =====================================================

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
    content="#07070c"
>

<title>NIGHT VIDEOS</title>


<!-- Telegram Mini App -->

<script
    src="https://telegram.org/js/telegram-web-app.js">
</script>


<!-- AdsGram -->

<script
    src="https://sad.adsgram.ai/js/sad.min.js">
</script>


<style>

* {{
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
}}

html,
body {{
    margin: 0;
    padding: 0;

    width: 100%;
    min-height: 100%;

    background:
        radial-gradient(
            circle at 15% 0%,
            #35205f 0%,
            transparent 38%
        ),
        radial-gradient(
            circle at 90% 15%,
            #181c4b 0%,
            transparent 35%
        ),
        linear-gradient(
            180deg,
            #08080f 0%,
            #040408 100%
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
    overflow-x: hidden;
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
        calc(30px + env(safe-area-inset-bottom));
}}

.logo {{
    width: 78px;
    height: 78px;

    margin-top: 8px;

    border-radius: 50%;

    display: flex;
    align-items: center;
    justify-content: center;

    font-size: 38px;

    background:
        linear-gradient(
            135deg,
            #a32cff,
            #4b00ff
        );

    box-shadow:
        0 0 45px
        rgba(132, 45, 255, 0.48),
        inset 0 1px 1px
        rgba(255,255,255,0.25);
}}

.title {{
    margin: 16px 0 0;

    font-size: 30px;

    line-height: 1;

    font-weight: 900;

    letter-spacing: 1px;

    text-align: center;
}}

.subtitle {{
    margin-top: 9px;

    color: #9999a9;

    font-size: 14px;

    font-weight: 600;

    text-align: center;
}}

.player-card {{
    width: 100%;

    max-width: 1000px;

    margin-top: 28px;

    padding: 8px;

    border-radius: 24px;

    background:
        linear-gradient(
            145deg,
            rgba(255,255,255,0.10),
            rgba(255,255,255,0.025)
        );

    border:
        1px solid
        rgba(255,255,255,0.12);

    box-shadow:
        0 30px 80px
        rgba(0,0,0,0.55);
}}

video {{
    display: block;

    width: 100%;

    max-height: 72vh;

    min-height: 220px;

    background: #000;

    border-radius: 18px;

    object-fit: contain;
}}

.loading-screen {{
    width: 100%;

    min-height: 220px;

    border-radius: 18px;

    display: flex;

    align-items: center;
    justify-content: center;

    flex-direction: column;

    background:
        radial-gradient(
            circle,
            #171226 0%,
            #07070b 70%
        );
}}

.loading-icon {{
    font-size: 46px;

    margin-bottom: 12px;
}}

.loading-text {{
    color: #a8a8b6;

    font-size: 14px;

    font-weight: 600;
}}

.status {{
    width: 100%;

    max-width: 900px;

    margin-top: 17px;

    text-align: center;

    color: #9d9dac;

    font-size: 13px;

    font-weight: 600;
}}

.features {{
    margin-top: 18px;

    color: #777786;

    font-size: 12px;

    text-align: center;

    letter-spacing: 0.2px;
}}

.brand {{
    margin-top: auto;

    padding-top: 45px;

    color: #555563;

    font-size: 12px;

    font-weight: 700;

    letter-spacing: 1px;
}}

.hidden {{
    display: none !important;
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
        🌙 Premium Video Streaming
    </div>


    <div class="player-card">


        <div
            id="loadingScreen"
            class="loading-screen"
        >

            <div class="loading-icon">
                🔒
            </div>

            <div class="loading-text">
                Advertisement required
            </div>

        </div>


        <video
            id="videoPlayer"
            class="hidden"
            controls
            playsinline
            webkit-playsinline
            preload="metadata"
            controlsList="nodownload"
        >

            Your browser does not support
            HTML5 video.

        </video>


    </div>


    <div
        id="status"
        class="status"
    >
        📺 Preparing advertisement...
    </div>


    <div class="features">
        📡 MTProto &nbsp;•&nbsp;
        Range &nbsp;•&nbsp;
        Seek &nbsp;•&nbsp;
        Large Files
    </div>


    <div class="brand">
        NIGHT VIDEOS
    </div>


</div>


<script>

/* =====================================================
   CONFIG
===================================================== */

const STREAM_URL =
    "{stream_url}";

const ADSGRAM_BLOCK_ID =
    "{ADSGRAM_BLOCK_ID}";


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

        try {{

            Telegram.WebApp.setHeaderColor(
                "#08080f"
            );

            Telegram.WebApp.setBackgroundColor(
                "#08080f"
            );

        }} catch (error) {{

            console.log(
                "Telegram color error:",
                error
            );

        }}

    }}

}} catch (error) {{

    console.log(
        "Telegram WebApp error:",
        error
    );

}}


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

const loadingScreen =
    document.getElementById(
        "loadingScreen"
    );


/* =====================================================
   ADSGRAM
===================================================== */

let adController = null;


function initializeAds() {{

    try {{

        if (
            !window.Adsgram
            ||
            !ADSGRAM_BLOCK_ID
        ) {{

            console.log(
                "AdsGram is not available"
            );

            return false;

        }}


        adController =
            window.Adsgram.init({{
                blockId:
                    ADSGRAM_BLOCK_ID
            }});


        return true;

    }} catch (error) {{

        console.log(
            "AdsGram init error:",
            error
        );

        return false;

    }}

}}


/* =====================================================
   LOAD VIDEO AFTER AD
===================================================== */

async function startVideo() {{

    try {{

        status.textContent =
            "▶️ Starting video...";


        /*
         * IMPORTANT:
         * The source is added only AFTER the ad.
         */

        video.src =
            STREAM_URL;


        video.classList.remove(
            "hidden"
        );


        loadingScreen.classList.add(
            "hidden"
        );


        video.load();


        /*
         * Try automatic playback.
         */

        try {{

            await video.play();

        }} catch (playError) {{

            console.log(
                "Autoplay blocked:",
                playError
            );


            status.textContent =
                "▶️ Tap the video to play";

        }}

    }} catch (error) {{

        console.log(
            "Video start error:",
            error
        );


        status.textContent =
            "❌ Video could not be started";

    }}

}}


/* =====================================================
   SHOW ADSGRAM
===================================================== */

async function showAdvertisement() {{

    const adsAvailable =
        initializeAds();


    /*
     * If AdsGram is unavailable, don't permanently
     * lock the player.
     */

    if (!adsAvailable) {{

        status.textContent =
            "▶️ Starting video...";

        await startVideo();

        return;

    }}


    try {{

        status.textContent =
            "📺 Loading advertisement...";


        /*
         * AdsGram show() returns a Promise.
         *
         * Reward block:
         * resolves after the user watches the ad.
         *
         * Interstitial:
         * can resolve when the user closes it.
         */

        const result =
            await adController.show();


        console.log(
            "AdsGram result:",
            result
        );


        status.textContent =
            "✅ Advertisement finished";


        /*
         * Small UI delay.
         */

        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    250
                )
        );


        /*
         * Automatically start video.
         */

        await startVideo();


    }} catch (error) {{

        console.log(
            "AdsGram show error:",
            error
        );


        /*
         * If ad fails/no ad exists,
         * start video instead of leaving
         * the user on a broken page.
         */

        status.textContent =
            "▶️ Starting video...";


        await startVideo();

    }}

}}


/* =====================================================
   START AD AUTOMATICALLY
===================================================== */

window.addEventListener(
    "load",
    function() {{

        setTimeout(
            showAdvertisement,
            350
        );

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
            "▶️ Ready";

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

        if (!video.ended) {{

            status.textContent =
                "⏸️ Paused";

        }}

    }}
);


video.addEventListener(
    "seeking",
    function() {{

        status.textContent =
            "🔄 Seeking...";

    }}
);


video.addEventListener(
    "seeked",
    function() {{

        status.textContent =
            "▶️ NIGHT VIDEOS";

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
            "HTML5 video error:",
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
        text=html,
        content_type="text/html",
    )


# =========================================================
# VIDEO STREAM
# =========================================================

async def stream_video(
    request: web.Request
):

    file_id = (
        request.query.get(
            "file_id"
        )
    )

    if not file_id:

        return web.Response(
            text="Missing file_id",
            status=400,
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
            status=400,
        )


    if file_size > MAX_FILE_SIZE:

        return web.Response(
            text="File is larger than 2 GB",
            status=413,
        )


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


    # =====================================================
    # RANGE HEADER
    # =====================================================

    range_header = (
        request.headers.get(
            "Range"
        )
    )


    requested_range = parse_range(
        range_header,
        file_size,
    )


    # =====================================================
    # INVALID RANGE
    # =====================================================

    if range_header and not requested_range:

        return web.Response(
            status=416,
            headers={
                "Content-Range":
                    f"bytes */{file_size}",
                "Accept-Ranges":
                    "bytes",
            },
        )


    # =====================================================
    # HEAD
    # =====================================================

    if request.method == "HEAD":

        if requested_range:

            start_byte, end_byte = (
                requested_range
            )

            content_length = (
                end_byte
                - start_byte
                + 1
            )

            headers = {

                "Content-Type":
                    mime_type,

                "Content-Length":
                    str(content_length),

                "Accept-Ranges":
                    "bytes",

                "Content-Range":
                    (
                        f"bytes "
                        f"{start_byte}-"
                        f"{end_byte}/"
                        f"{file_size}"
                    ),

                "Cache-Control":
                    "no-cache",

            }

            return web.Response(
                status=206,
                headers=headers,
            )


        headers = {

            "Content-Type":
                mime_type,

            "Content-Length":
                str(file_size),

            "Accept-Ranges":
                "bytes",

            "Cache-Control":
                "no-cache",

        }

        return web.Response(
            status=200,
            headers=headers,
        )


    # =====================================================
    # DETERMINE RANGE
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

        end_byte = (
            file_size - 1
        )

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
                "inline; "
                "filename*=UTF-8''"
                f"{quote(file_name)}"
            ),

        "Cache-Control":
            "no-cache, no-store, must-revalidate",

        "Pragma":
            "no-cache",

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


    # =====================================================
    # CREATE STREAM RESPONSE
    # =====================================================

    response = web.StreamResponse(
        status=status_code,
        headers=headers,
    )


    await response.prepare(
        request
    )


    # =====================================================
    # PYROGRAM CHUNK CALCULATION
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
    # STREAM TELEGRAM FILE
    # =====================================================

    try:

        chunk_number = 0


        async for chunk in (
            mtproto.stream_media(
                file_id,
                offset=first_chunk,
                limit=chunks_needed,
            )
        ):

            if bytes_remaining <= 0:

                break


            # ---------------------------------------------
            # Remove bytes before requested range
            # ---------------------------------------------

            if chunk_number == 0:

                if inner_offset:

                    chunk = (
                        chunk[
                            inner_offset:
                        ]
                    )


            # ---------------------------------------------
            # Don't send more than requested
            # ---------------------------------------------

            if len(chunk) > bytes_remaining:

                chunk = (
                    chunk[
                        :bytes_remaining
                    ]
                )


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


        try:

            await response.write_eof()

        except Exception:

            pass


        return response


    except asyncio.CancelledError:

        # Browser stopped/seeked/closed.
        # This is normal.

        print(
            "Stream cancelled by browser."
        )

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
        client_max_size=
            1024
            * 1024
            * 1024
            * 10
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


    # MINI APP
    app.router.add_get(
        "/watch",
        player
    )


    # VIDEO STREAM
    app.router.add_route(
        "GET",
        "/stream",
        stream_video
    )


    # HEAD
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
        "      NIGHT VIDEOS SERVER"
    )

    print(
        "======================================"
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
        "90MB: ENABLED"
    )

    print(
        "2GB: ENABLED"
    )

    print(
        "RANGE: ENABLED"
    )

    print(
        "SEEK: ENABLED"
    )

    print(
        f"AdsGram: {ADSGRAM_BLOCK_ID}"
    )

    print(
        "WATCH NOW: ENABLED"
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
        "Starting Telegram MTProto..."
    )


    await mtproto.start()


    print(
        "Telegram MTProto started ✅"
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
