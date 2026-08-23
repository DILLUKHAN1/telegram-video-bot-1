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
# NIGHT VIDEOS
# LUXURY TELEGRAM VIDEO STREAMING BOT
# =========================================================


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

API_ID = os.getenv("API_ID")

API_HASH = os.getenv("API_HASH")

PORT = int(
    os.getenv(
        "PORT",
        "8080"
    )
)

WEB_URL = os.getenv("WEB_URL")

ADSGRAM_BLOCK_ID = os.getenv(
    "ADSGRAM_BLOCK_ID",
    "int-44048"
)


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
# RAILWAY PUBLIC URL
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
# Used for large-file streaming.
#
# Aiogram handles bot messages.
# Pyrogram handles Telegram media streaming.
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
# =========================================================

# 1 MiB chunks

CHUNK_SIZE = (
    1024 * 1024
)


# Maximum practical browser range

MAX_RANGE_REQUEST = (
    16 * 1024 * 1024
)


# =========================================================
# CREATE PLAY URL
# =========================================================

def make_play_url(
    file_id: str,
    size_bytes: int = 0,
    mime_type: str = "video/mp4",
    file_name: str = "video.mp4",
) -> str:

    params = (

        f"file_id="
        f"{quote(file_id, safe='')}"

        f"&size="
        f"{int(size_bytes)}"

        f"&mime="
        f"{quote(mime_type, safe='')}"

        f"&name="
        f"{quote(file_name, safe='')}"
    )

    return (

        f"{WEB_URL.rstrip('/')}"

        f"/watch?"

        f"{params}"
    )


# =========================================================
# /START
# =========================================================

@dp.message(CommandStart())
async def start(
    message: Message
):

    await message.answer(

        "🌙 NIGHT VIDEOS\n\n"

        "🎬 Video ya video file bhejo.\n\n"

        "Main tumhe Watch Now button dunga.\n\n"

        "▶️ Watch Now = NIGHT VIDEOS Mini App\n\n"

        "📡 Large files supported\n"
        "⏩ Range + Seek supported\n\n"

        "/start - Start\n"
        "/help - Help"
    )


# =========================================================
# /HELP
# =========================================================

@dp.message(Command("help"))
async def help_cmd(
    message: Message
):

    await message.answer(

        "🌙 NIGHT VIDEOS HELP\n\n"

        "1️⃣ Bot ko video bhejo\n"

        "2️⃣ Forwarded video bhi bhej sakte ho\n"

        "3️⃣ Watch Now button dabao\n"

        "4️⃣ Mini App open hoga\n"

        "5️⃣ Advertisement show ho sakta hai\n"

        "6️⃣ Advertisement complete hone ke baad "
        "video automatically play hoga\n\n"

        "📡 MTProto streaming\n"
        "⏩ Range support\n"
        "⏩ Seek support\n"
        "📁 Large video streaming"
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

        size_bytes
        / (1024 * 1024)

        if size_bytes

        else 0
    )


    # -----------------------------------------------------
    # PLAY URL
    # -----------------------------------------------------

    play_url = make_play_url(

        file_id=file_id,

        size_bytes=size_bytes,

        mime_type=mime_type,

        file_name=file_name,
    )


    # -----------------------------------------------------
    # BUTTON
    # -----------------------------------------------------

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="▶️ WATCH NOW",

                    web_app=WebAppInfo(

                        url=play_url

                    )
                )

            ]

        ]
    )


    # -----------------------------------------------------
    # SIZE
    # -----------------------------------------------------

    size_text = ""

    if size_bytes:

        size_text = (

            f"📁 Size: "
            f"{size_mb:.2f} MB\n"
        )


    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    await message.answer(

        "🌙 NIGHT VIDEOS\n\n"

        "✅ Video received!\n\n"

        f"{size_text}"

        "🚀 Large video streaming enabled\n"
        "⏩ Range + Seek enabled\n\n"

        "👇 Video dekhne ke liye "
        "WATCH NOW dabao.",

        reply_markup=keyboard,
    )


# =========================================================
# VIDEO RECEIVED
#
# This also works for forwarded videos because Telegram
# still provides message.video.
# =========================================================

@dp.message(F.video)
async def video_received(
    message: Message
):

    video = message.video


    await send_received(

        message=message,

        file_id=video.file_id,

        size_bytes=(
            video.file_size
            or 0
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
# Works for:
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
#
# Also works when the document is forwarded.
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
    )


    is_video = (

        mime.startswith("video/")

        or

        filename_lower.endswith(
            video_extensions
        )
    )


    if is_video:

        await send_received(

            message=message,

            file_id=document.file_id,

            size_bytes=(
                document.file_size
                or 0
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

            "▶️ WATCH NOW sirf "
            "video files ke liye available hai."
        )


# =========================================================
# HEALTH
# =========================================================

async def health(
    request: web.Request
):

    return web.Response(

        text=(
            "NIGHT VIDEOS is running ✅"
        )
    )


# =========================================================
# LUXURY MINI APP PLAYER
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

            status=400
        )


    # -----------------------------------------------------
    # SIZE
    # -----------------------------------------------------

    try:

        size = int(

            request.query.get(
                "size",
                "0"
            )
        )

    except ValueError:

        size = 0


    # -----------------------------------------------------
    # MIME
    # -----------------------------------------------------

    mime_type = (

        request.query.get(

            "mime",

            "video/mp4"
        )
    )


    # -----------------------------------------------------
    # FILE NAME
    # -----------------------------------------------------

    file_name = (

        request.query.get(

            "name",

            "video.mp4"
        )
    )


    # -----------------------------------------------------
    # VIDEO URL
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # HUMAN SIZE
    # -----------------------------------------------------

    if size > 0:

        size_gb = (
            size
            / (1024 * 1024 * 1024)
        )

        size_mb = (
            size
            / (1024 * 1024)
        )

        if size_gb >= 1:

            size_text = (
                f"{size_gb:.2f} GB"
            )

        else:

            size_text = (
                f"{size_mb:.2f} MB"
            )

    else:

        size_text = "Unknown size"


    # =====================================================
    # LUXURY HTML
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


<!-- ===================================================
     TELEGRAM MINI APP
==================================================== -->

<script
    src="https://telegram.org/js/telegram-web-app.js">
</script>


<!-- ===================================================
     ADSGRAM
==================================================== -->

<script
    src="https://sad.adsgram.ai/js/sad.min.js">
</script>


<style>

/* =====================================================
   RESET
===================================================== */

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
            circle at 50% -10%,
            #3b146f 0%,
            #151020 28%,
            #08080d 60%,
            #030305 100%
        );

    color: white;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "SF Pro Display",
        "Segoe UI",
        Arial,
        sans-serif;
}}


body {{
    min-height: 100vh;

    overflow-x: hidden;
}}


/* =====================================================
   BACKGROUND GLOW
===================================================== */

body::before {{
    content: "";

    position: fixed;

    width: 300px;

    height: 300px;

    top: -120px;

    left: 50%;

    transform:
        translateX(-50%);

    background:
        radial-gradient(
            circle,
            rgba(
                139,
                44,
                255,
                0.30
            ),
            transparent 70%
        );

    filter:
        blur(25px);

    pointer-events: none;
}}


/* =====================================================
   MAIN
===================================================== */

.container {{

    width: 100%;

    min-height: 100vh;

    padding:
        calc(
            22px
            +
            env(
                safe-area-inset-top
            )
        )
        15px
        calc(
            28px
            +
            env(
                safe-area-inset-bottom
            )
        );

    display: flex;

    flex-direction: column;

    align-items: center;

}}


/* =====================================================
   TOP BADGE
===================================================== */

.top-badge {{

    display: flex;

    align-items: center;

    gap: 8px;

    padding:
        8px 15px;

    border-radius: 999px;

    background:
        rgba(
            255,
            255,
            255,
            0.055
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.10
        );

    box-shadow:
        inset
        0 1px 0
        rgba(
            255,
            255,
            255,
            0.08
        );

    backdrop-filter:
        blur(18px);

    -webkit-backdrop-filter:
        blur(18px);

    color:
        #d9c9ff;

    font-size:
        11px;

    font-weight:
        700;

    letter-spacing:
        1.5px;

    text-transform:
        uppercase;

}}


.status-dot {{

    width: 7px;

    height: 7px;

    border-radius: 50%;

    background:
        #a855f7;

    box-shadow:
        0 0 12px
        #a855f7;

}}


/* =====================================================
   LOGO
===================================================== */

.logo-wrap {{

    position: relative;

    width: 88px;

    height: 88px;

    margin-top: 20px;

    display: flex;

    align-items: center;

    justify-content: center;

}}


.logo-glow {{

    position: absolute;

    inset: 0;

    border-radius: 50%;

    background:
        linear-gradient(
            135deg,
            #a855f7,
            #6d28d9,
            #3b0764
        );

    filter:
        blur(18px);

    opacity:
        0.65;

}}


.logo {{

    position: relative;

    width: 82px;

    height: 82px;

    border-radius: 50%;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        linear-gradient(
            145deg,
            #9b4dff,
            #651fff 55%,
            #26005c
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.20
        );

    box-shadow:
        inset
        0 1px 0
        rgba(
            255,
            255,
            255,
            0.30
        ),

        0 15px 45px
        rgba(
            115,
            45,
            255,
            0.35
        );

    font-size:
        39px;

}}


/* =====================================================
   TITLE
===================================================== */

.title {{

    margin:
        15px 0 0;

    font-size:
        clamp(
            28px,
            8vw,
            40px
        );

    line-height:
        1.05;

    font-weight:
        900;

    letter-spacing:
        1px;

    text-align:
        center;

    background:
        linear-gradient(
            90deg,
            #ffffff,
            #d9c7ff,
            #ffffff
        );

    -webkit-background-clip:
        text;

    background-clip:
        text;

    color:
        transparent;

}}


.subtitle {{

    margin-top:
        9px;

    color:
        #9f9bab;

    font-size:
        14px;

    text-align:
        center;

}}


/* =====================================================
   FILE INFO
===================================================== */

.file-info {{

    width: 100%;

    max-width: 900px;

    margin-top:
        22px;

    padding:
        15px 17px;

    display:
        flex;

    align-items:
        center;

    gap:
        13px;

    border-radius:
        18px;

    background:
        linear-gradient(
            135deg,
            rgba(
                255,
                255,
                255,
                0.075
            ),
            rgba(
                255,
                255,
                255,
                0.025
            )
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.10
        );

    box-shadow:
        0 20px 60px
        rgba(
            0,
            0,
            0,
            0.30
        );

    backdrop-filter:
        blur(20px);

    -webkit-backdrop-filter:
        blur(20px);

}}


.file-icon {{

    width: 45px;

    height: 45px;

    flex-shrink: 0;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    border-radius:
        14px;

    background:
        rgba(
            139,
            92,
            246,
            0.18
        );

    font-size:
        21px;

}}


.file-details {{

    min-width: 0;

    flex: 1;

}}


.file-name {{

    overflow:
        hidden;

    white-space:
        nowrap;

    text-overflow:
        ellipsis;

    color:
        #f5f2ff;

    font-size:
        14px;

    font-weight:
        700;

}}


.file-meta {{

    margin-top:
        5px;

    color:
        #8f8b99;

    font-size:
        11px;

}}


/* =====================================================
   PLAYER CARD
===================================================== */

.player-card {{

    position:
        relative;

    width:
        100%;

    max-width:
        1000px;

    margin-top:
        16px;

    padding:
        7px;

    border-radius:
        24px;

    background:
        linear-gradient(
            145deg,
            rgba(
                255,
                255,
                255,
                0.11
            ),
            rgba(
                255,
                255,
                255,
                0.035
            )
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.12
        );

    box-shadow:
        0 30px 80px
        rgba(
            0,
            0,
            0,
            0.55
        ),

        0 0 50px
        rgba(
            104,
            35,
            255,
            0.08
        );

    backdrop-filter:
        blur(20px);

    -webkit-backdrop-filter:
        blur(20px);

}}


.player-inner {{

    position:
        relative;

    overflow:
        hidden;

    border-radius:
        18px;

    background:
        #000;

}}


video {{

    display:
        block;

    width:
        100%;

    max-height:
        68vh;

    min-height:
        180px;

    background:
        #000;

    border-radius:
        18px;

    object-fit:
        contain;

}}


/* =====================================================
   STATUS
===================================================== */

.status {{

    width:
        100%;

    max-width:
        900px;

    margin-top:
        15px;

    padding:
        10px 14px;

    text-align:
        center;

    color:
        #a7a3b2;

    font-size:
        12px;

    font-weight:
        600;

}}


/* =====================================================
   PREMIUM PLAY BUTTON
===================================================== */

.play-button {{

    position:
        relative;

    overflow:
        hidden;

    width:
        100%;

    max-width:
        420px;

    margin-top:
        4px;

    padding:
        16px 24px;

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.18
        );

    border-radius:
        17px;

    color:
        white;

    font-size:
        15px;

    font-weight:
        800;

    letter-spacing:
        0.4px;

    background:
        linear-gradient(
            135deg,
            #a855f7,
            #7c3aed 50%,
            #4c1d95
        );

    box-shadow:
        0 15px 40px
        rgba(
            124,
            58,
            237,
            0.35
        );

    transition:
        transform 0.15s ease,
        opacity 0.15s ease;

}}


.play-button::before {{

    content: "";

    position:
        absolute;

    top:
        0;

    left:
        -100%;

    width:
        70%;

    height:
        100%;

    background:
        linear-gradient(
            90deg,
            transparent,
            rgba(
                255,
                255,
                255,
                0.18
            ),
            transparent
        );

    transform:
        skewX(-20deg);

    animation:
        shine 3.2s infinite;

}}


@keyframes shine {{

    0% {{
        left: -100%;
    }}

    55% {{
        left: 140%;
    }}

    100% {{
        left: 140%;
    }}

}}


.play-button:active {{

    transform:
        scale(
            0.98
        );

}}


.play-button:disabled {{

    opacity:
        0.65;

}}


/* =====================================================
   STREAM FEATURES
===================================================== */

.features {{

    display:
        flex;

    flex-wrap:
        wrap;

    justify-content:
        center;

    gap:
        8px;

    margin-top:
        13px;

}}


.feature {{

    padding:
        8px 11px;

    border-radius:
        999px;

    color:
        #a8a2b5;

    background:
        rgba(
            255,
            255,
            255,
            0.045
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.07
        );

    font-size:
        10px;

    font-weight:
        700;

}}


/* =====================================================
   BRAND
===================================================== */

.brand {{

    margin-top:
        auto;

    padding-top:
        38px;

    color:
        #55515f;

    font-size:
        11px;

    font-weight:
        700;

    letter-spacing:
        2px;

    text-align:
        center;

}}


/* =====================================================
   INFO
===================================================== */

.info {{

    margin-top:
        8px;

    color:
        #484451;

    font-size:
        10px;

    text-align:
        center;

}}


/* =====================================================
   LOADING ANIMATION
===================================================== */

.loading-dot {{

    display:
        inline-block;

    width:
        6px;

    height:
        6px;

    margin-left:
        3px;

    border-radius:
        50%;

    background:
        #a855f7;

    animation:
        pulse 1s infinite;

}}


@keyframes pulse {{

    0% {{
        opacity: 0.25;
    }}

    50% {{
        opacity: 1;
    }}

    100% {{
        opacity: 0.25;
    }}

}}


/* =====================================================
   MOBILE
===================================================== */

@media (
    max-width: 500px
) {{

    .container {{

        padding-left:
            11px;

        padding-right:
            11px;

    }}

    .player-card {{

        border-radius:
            21px;

    }}

    video {{

        min-height:
            165px;

        max-height:
            60vh;

    }}

    .title {{

        font-size:
            31px;

    }}

}}

</style>

</head>


<body>


<div class="container">


    <!-- ===============================================
         TOP BADGE
    ================================================ -->

    <div class="top-badge">

        <span class="status-dot"></span>

        NIGHT VIDEOS PREMIUM

    </div>


    <!-- ===============================================
         LOGO
    ================================================ -->

    <div class="logo-wrap">

        <div class="logo-glow"></div>

        <div class="logo">

            🎬

        </div>

    </div>


    <!-- ===============================================
         TITLE
    ================================================ -->

    <h1 class="title">

        NIGHT VIDEOS

    </h1>


    <div class="subtitle">

        🌙 Premium online video experience

    </div>


    <!-- ===============================================
         FILE INFO
    ================================================ -->

    <div class="file-info">

        <div class="file-icon">

            🎞️

        </div>


        <div class="file-details">

            <div class="file-name">

                {file_name}

            </div>


            <div class="file-meta">

                📁 {size_text}
                &nbsp; • &nbsp;
                🎬 {mime_type}

            </div>

        </div>

    </div>


    <!-- ===============================================
         VIDEO
    ================================================ -->

    <div class="player-card">

        <div class="player-inner">

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

                    type="{mime_type}"

                >

                Your browser does not support
                HTML5 video.

            </video>

        </div>

    </div>


    <!-- ===============================================
         PLAY BUTTON
    ================================================ -->

    <button

        id="playButton"

        class="play-button"

    >

        ▶️ WATCH VIDEO

    </button>


    <!-- ===============================================
         STATUS
    ================================================ -->

    <div

        id="status"

        class="status"

    >

        ⏳ Preparing secure stream...

    </div>


    <!-- ===============================================
         FEATURES
    ================================================ -->

    <div class="features">

        <div class="feature">

            📡 MTProto

        </div>

        <div class="feature">

            ⏩ Range

        </div>

        <div class="feature">

            🎯 Seek

        </div>

        <div class="feature">

            📁 Large Files

        </div>

    </div>


    <!-- ===============================================
         BRAND
    ================================================ -->

    <div class="brand">

        NIGHT VIDEOS

    </div>


    <div class="info">

        Premium Telegram Mini App

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
        "AdsGram init error:",
        error
    );

}}


/* =====================================================
   SHOW AD
===================================================== */

async function showAd() {{

    if (!adController) {{

        return;

    }}


    try {{

        status.textContent =
            "📺 Advertisement loading...";


        await adController.show();


        status.textContent =
            "✅ Advertisement finished";

    }} catch (error) {{

        console.log(
            "AdsGram error:",
            error
        );

        /*
         * If ad is unavailable, video is still
         * allowed to continue.
         */

        status.textContent =
            "▶️ Starting video...";

    }}

}}


/* =====================================================
   PLAY VIDEO
===================================================== */

async function startVideo() {{

    try {{

        status.textContent =
            "▶️ Starting video...";


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
            "▶️ Tap the video to play";

        playButton.disabled =
            false;

        playButton.textContent =
            "▶️ WATCH VIDEO";

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
            "⏳ PLEASE WAIT...";


        /*
         * Advertisement first.
         */

        await showAd();


        /*
         * Automatically play video
         * after advertisement.
         */

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
            "⏳ Connecting to stream...";

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

        if (
            video.paused
        ) {{

            status.textContent =
                "▶️ Ready to play";

        }}

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

    "seeking",

    function() {{

        status.textContent =
            "⏩ Seeking...";

    }}

);


video.addEventListener(

    "seeked",

    function() {{

        if (
            !video.paused
        ) {{

            status.textContent =
                "▶️ NIGHT VIDEOS";

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

        text=html,

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

        range_header

        .replace(
            "bytes=",
            "",
            1
        )

        .strip()
    )


    # -----------------------------------------------------
    # Browser may send multiple ranges.
    # We use first range.
    # -----------------------------------------------------

    if "," in value:

        value = (

            value.split(
                ",",
                1
            )[0]
        )


    parts = value.split(
        "-",
        1
    )


    if len(parts) != 2:

        return None


    start_text = (
        parts[0].strip()
    )


    end_text = (
        parts[1].strip()
    )


    try:

        # -------------------------------------------------
        # SUFFIX RANGE
        # Example:
        # bytes=-1000
        # -------------------------------------------------

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

                file_size
                - 1
            )


        else:

            # ---------------------------------------------
            # NORMAL RANGE
            # ---------------------------------------------

            start = int(
                start_text
            )


            if start < 0:

                return None


            if start >= file_size:

                return None


            if end_text == "":

                end = (

                    file_size
                    - 1
                )

            else:

                end = int(
                    end_text
                )


                if end >= file_size:

                    end = (

                        file_size
                        - 1
                    )


            if end < start:

                return None


        return (
            start,
            end
        )


    except ValueError:

        return None


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

            status=400
        )


    # -----------------------------------------------------
    # FILE SIZE
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # MIME
    # -----------------------------------------------------

    mime_type = (

        request.query.get(

            "mime",

            "video/mp4"
        )
    )


    # -----------------------------------------------------
    # FILE NAME
    # -----------------------------------------------------

    file_name = (

        request.query.get(

            "name",

            "video.mp4"
        )
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
    # RANGE RESPONSE
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

            file_size
            - 1
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
                f'inline; filename="{file_name}"'
            ),

        "Cache-Control":
            "no-cache",

        "X-Content-Type-Options":
            "nosniff",

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

        headers=headers
    )


    await response.prepare(
        request
    )


    # =====================================================
    # CALCULATE TELEGRAM CHUNK
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

            +

            content_length

            +

            CHUNK_SIZE

            - 1

        )

        // CHUNK_SIZE
    )


    # =====================================================
    # STREAM FROM TELEGRAM
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


            # -------------------------------------------------
            # FIRST CHUNK OFFSET
            # -------------------------------------------------

            if chunk_number == 0:

                if inner_offset:

                    chunk = (

                        chunk[
                            inner_offset:
                        ]

                    )


            # -------------------------------------------------
            # LIMIT TO REQUESTED RANGE
            # -------------------------------------------------

            if (

                len(chunk)

                >

                bytes_remaining

            ):

                chunk = (

                    chunk[
                        :bytes_remaining
                    ]

                )


            if not chunk:

                break


            # -------------------------------------------------
            # SEND
            # -------------------------------------------------

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

        # Browser stopped/seeked/closed stream.

        raise


    except Exception as error:

        print(
            "================================"
        )

        print(
            "MTProto STREAMING ERROR"
        )

        print(
            repr(error)
        )

        print(
            "================================"
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

            10
            * 1024
            * 1024
            * 1024
    )


    # -----------------------------------------------------
    # HOME
    # -----------------------------------------------------

    app.router.add_get(

        "/",

        health
    )


    # -----------------------------------------------------
    # HEALTH
    # -----------------------------------------------------

    app.router.add_get(

        "/health",

        health
    )


    # -----------------------------------------------------
    # MINI APP
    # -----------------------------------------------------

    app.router.add_get(

        "/watch",

        player
    )


    # -----------------------------------------------------
    # STREAM
    # -----------------------------------------------------

    app.router.add_route(

        "GET",

        "/stream",

        stream_video
    )


    app.router.add_route(

        "HEAD",

        "/stream",

        stream_video
    )


    # -----------------------------------------------------
    # RUNNER
    # -----------------------------------------------------

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
        "🌙 NIGHT VIDEOS WEB SERVER STARTED"
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
        "Large video streaming: ENABLED"
    )

    print(
        "Range: ENABLED"
    )

    print(
        "Seek: ENABLED"
    )

    print(
        "Forwarded videos: ENABLED"
    )

    print(
        "Luxury Mini App: ENABLED"
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

    # -----------------------------------------------------
    # START MTProto
    # -----------------------------------------------------

    print(
        "Starting Telegram MTProto client..."
    )


    await mtproto.start()


    print(
        "Telegram MTProto client started ✅"
    )


    # -----------------------------------------------------
    # START WEB SERVER
    # -----------------------------------------------------

    await start_web_server()


    # -----------------------------------------------------
    # START BOT
    # -----------------------------------------------------

    print(
        "Starting NIGHT VIDEOS bot..."
    )


    try:

        await dp.start_polling(
            bot
        )


    finally:

        print(
            "Stopping bot..."
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
            "🌙 NIGHT VIDEOS stopped."
        )
