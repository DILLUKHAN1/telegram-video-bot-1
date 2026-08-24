import os
import json
import hmac
import hashlib
import base64
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
# NIGHT HUB
# SECURE ADMIN UPLOAD + VIDEO LIBRARY
# =========================================================


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
ADMIN_ID = os.getenv("ADMIN_ID")

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

# IMPORTANT:
# Railway/Replit environment variable me ye set karo.
#
# Example:
# WATCH_SECRET=some-long-random-secret
#
WATCH_SECRET = os.getenv(
    "WATCH_SECRET"
)

if not WATCH_SECRET:
    raise RuntimeError(
        "WATCH_SECRET environment variable is missing"
    )


# =========================================================
# CHECK REQUIRED VARIABLES
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

if not ADMIN_ID:
    raise RuntimeError(
        "ADMIN_ID environment variable is missing"
    )


try:
    ADMIN_ID = int(
        ADMIN_ID
    )
except ValueError:
    raise RuntimeError(
        "ADMIN_ID must be a Telegram numeric user ID"
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
# PYROGRAM
# LARGE FILE STREAMING
# =========================================================

mtproto = Client(

    "night_hub_mtproto",

    api_id=int(
        API_ID
    ),

    api_hash=API_HASH,

    bot_token=BOT_TOKEN,

    no_updates=True,

    in_memory=True,
)


# =========================================================
# STREAM SETTINGS
# =========================================================

CHUNK_SIZE = (
    1024 * 1024
)


# =========================================================
# VIDEO DATABASE
# =========================================================

VIDEO_DB = os.getenv(
    "VIDEO_DB",
    "videos.json"
)


def load_videos():

    if not os.path.exists(
        VIDEO_DB
    ):
        return []

    try:

        with open(
            VIDEO_DB,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

            if isinstance(
                data,
                list
            ):
                return data

    except Exception as error:

        print(
            "VIDEO DATABASE LOAD ERROR:",
            repr(error)
        )

    return []


videos = load_videos()


def save_videos():

    temp_file = (
        VIDEO_DB + ".tmp"
    )

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                videos,
                file,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_file,
            VIDEO_DB
        )

    except Exception as error:

        print(
            "VIDEO DATABASE SAVE ERROR:",
            repr(error)
        )


# =========================================================
# ADMIN UPLOAD STATE
# =========================================================

pending_videos = {}


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(
    user_id: int
) -> bool:

    return (
        user_id == ADMIN_ID
    )


# =========================================================
# SIGNED WATCH TOKEN
# =========================================================

def create_watch_token(
    video_index: int
) -> str:

    payload = (
        str(video_index)
    )

    signature = hmac.new(

        WATCH_SECRET.encode(
            "utf-8"
        ),

        payload.encode(
            "utf-8"
        ),

        hashlib.sha256

    ).hexdigest()

    raw = (
        payload
        + "."
        + signature
    )

    return base64.urlsafe_b64encode(
        raw.encode(
            "utf-8"
        )
    ).decode(
        "utf-8"
    )


def verify_watch_token(
    token: str
):

    try:

        decoded = base64.urlsafe_b64decode(
            token.encode(
                "utf-8"
            )
        ).decode(
            "utf-8"
        )

        payload, signature = (
            decoded.split(
                ".",
                1
            )
        )

        expected = hmac.new(

            WATCH_SECRET.encode(
                "utf-8"
            ),

            payload.encode(
                "utf-8"
            ),

            hashlib.sha256

        ).hexdigest()

        if not hmac.compare_digest(
            signature,
            expected
        ):

            return None

        index = int(
            payload
        )

        if index < 0:
            return None

        if index >= len(
            videos
        ):
            return None

        return index

    except Exception:

        return None


# =========================================================
# WATCH URL
# =========================================================

def make_watch_url(
    video_index: int
) -> str:

    token = create_watch_token(
        video_index
    )

    return (
        f"{WEB_URL.rstrip('/')}"
        f"/watch?t="
        f"{quote(token, safe='')}"
    )


# =========================================================
# WATCH BUTTON
# =========================================================

def make_watch_keyboard(
    video_index: int
):

    url = make_watch_url(
        video_index
    )

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="👉 𝐖𝐀𝐓𝐂𝐇 𝐍𝐎𝐖 👈",

                    web_app=WebAppInfo(
                        url=url
                    )

                )

            ]

        ]

    )


# =========================================================
# SEND ONE VIDEO TO USER
# =========================================================

async def send_video_card(
    message: Message,
    video_index: int
):

    if video_index < 0:
        return

    if video_index >= len(
        videos
    ):
        return

    data = videos[
        video_index
    ]

    cover_file_id = data.get(
        "cover_file_id"
    )

    keyboard = make_watch_keyboard(
        video_index
    )

    # -----------------------------------------------------
    # COVER PHOTO
    # -----------------------------------------------------

    if cover_file_id:

        try:

            await message.answer_photo(

                photo=cover_file_id,

                caption="",

                reply_markup=keyboard,

                protect_content=True

            )

            return

        except Exception as error:

            print(
                "COVER SEND ERROR:",
                repr(error)
            )

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    await message.answer(

        "🎬",

        reply_markup=keyboard,

        protect_content=True

    )


# =========================================================
# SEND ALL VIDEOS
# =========================================================

async def send_all_videos(
    message: Message
):

    total = len(
        videos
    )

    if total == 0:

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            "🎬 Abhi koi video available nahi hai.",

            parse_mode="HTML"

        )

        return


    await message.answer(

        "🌙 <b>NIGHT HUB</b>\n\n"

        f"🎬 <b>{total} videos available</b>\n\n"

        "👇 Video select karke "
        "<b>WATCH NOW</b> press karein.",

        parse_mode="HTML"

    )


    # -----------------------------------------------------
    # OLD TO NEW
    # -----------------------------------------------------

    for index in range(
        total
    ):

        try:

            await send_video_card(

                message,
                index

            )

            # Telegram flood protection
            await asyncio.sleep(
                0.15
            )

        except Exception as error:

            print(
                "VIDEO CARD ERROR:",
                repr(error)
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

    user_id = (
        message.from_user.id
    )

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    if is_admin(
        user_id
    ):

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            "👑 <b>ADMIN MODE</b>\n\n"

            "📹 New video add karne ke liye:\n"
            "/addvideo\n\n"

            "📚 Neeche current video library bhi "
            "dikhayi ja rahi hai.\n\n"

            "🔒 Upload access sirf aapke account ke liye enabled hai.",

            parse_mode="HTML"

        )

    else:

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            "🎬 Welcome!\n\n"

            "👇 Available videos neeche hain.\n\n"

            "👉 <b>WATCH NOW</b> par click karein.",

            parse_mode="HTML"

        )


    # -----------------------------------------------------
    # SHOW ALL SAVED VIDEOS
    # -----------------------------------------------------

    await send_all_videos(
        message
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

    user_id = (
        message.from_user.id
    )

    if is_admin(
        user_id
    ):

        await message.answer(

            "🌙 <b>NIGHT HUB ADMIN HELP</b>\n\n"

            "/addvideo - New video\n"
            "/cancel - Cancel upload\n"
            "/videos - Show all videos\n"
            "/help - Help\n\n"

            "Upload process:\n"
            "1️⃣ /addvideo\n"
            "2️⃣ Video / forwarded video\n"
            "3️⃣ Cover photo\n"
            "4️⃣ WATCH NOW generated",

            parse_mode="HTML"

        )

    else:

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            "👉 Available videos /start par mil jayengi.",

            parse_mode="HTML"

        )


# =========================================================
# VIDEOS COMMAND
# =========================================================

@dp.message(
    Command("videos")
)
async def videos_cmd(
    message: Message
):

    await send_all_videos(
        message
    )


# =========================================================
# ADD VIDEO
# =========================================================

@dp.message(
    Command("addvideo")
)
async def add_video_cmd(
    message: Message
):

    user_id = (
        message.from_user.id
    )

    # -----------------------------------------------------
    # HARD ADMIN LOCK
    # -----------------------------------------------------

    if not is_admin(
        user_id
    ):

        await message.answer(

            "❌ <b>ACCESS DENIED</b>\n\n"

            "Sirf Admin video upload kar sakta hai.",

            parse_mode="HTML"

        )

        return


    pending_videos[
        user_id
    ] = {

        "file_id": None,

        "file_size": 0,

        "mime_type": "video/mp4",

        "file_name": "video.mp4",

        "cover_file_id": None,

    }


    await message.answer(

        "👑 <b>ADMIN UPLOAD MODE</b>\n\n"

        "📹 Ab video ya forwarded video bhejo.\n\n"

        "Uske baad cover photo bhejna hai.",

        parse_mode="HTML"

    )


# =========================================================
# CANCEL
# =========================================================

@dp.message(
    Command("cancel")
)
async def cancel_cmd(
    message: Message
):

    user_id = (
        message.from_user.id
    )

    if not is_admin(
        user_id
    ):
        return

    pending_videos.pop(
        user_id,
        None
    )

    await message.answer(
        "❌ Upload cancelled."
    )


# =========================================================
# VIDEO RECEIVED
#
# ONLY ADMIN
# =========================================================

@dp.message(
    F.video
)
async def video_received(
    message: Message
):

    user_id = (
        message.from_user.id
    )

    # =====================================================
    # HARD PUBLIC BLOCK
    # =====================================================

    if not is_admin(
        user_id
    ):

        await message.answer(

            "🔒 <b>UPLOAD DISABLED</b>\n\n"

            "Public users video upload nahi kar sakte.",

            parse_mode="HTML"

        )

        return


    # =====================================================
    # ADMIN MUST START /ADDVIDEO
    # =====================================================

    if user_id not in pending_videos:

        await message.answer(

            "⚠️ Pehle /addvideo command bhejo."

        )

        return


    video = message.video


    pending_videos[
        user_id
    ]["file_id"] = (
        video.file_id
    )


    pending_videos[
        user_id
    ]["file_size"] = (
        video.file_size or 0
    )


    pending_videos[
        user_id
    ]["mime_type"] = (

        video.mime_type
        or "video/mp4"

    )


    pending_videos[
        user_id
    ]["file_name"] = (

        video.file_name
        or "video.mp4"

    )


    # Telegram thumbnail
    try:

        if video.thumbnail:

            pending_videos[
                user_id
            ]["cover_file_id"] = (
                video.thumbnail.file_id
            )

    except Exception as error:

        print(
            "VIDEO THUMBNAIL ERROR:",
            repr(error)
        )


    await message.answer(

        "✅ <b>VIDEO RECEIVED</b>\n\n"

        f"📁 {video.file_name or 'video.mp4'}\n"

        f"📦 "
        f"{(video.file_size or 0) / (1024 * 1024):.2f} MB\n\n"

        "🖼️ Ab <b>Cover Photo</b> bhejo.\n\n"

        "Ya Telegram thumbnail use karna ho "
        "to /usecover bhejo.",

        parse_mode="HTML"

    )


# =========================================================
# DOCUMENT RECEIVED
#
# ONLY ADMIN
# Supports forwarded video files
# =========================================================

@dp.message(
    F.document
)
async def document_received(
    message: Message
):

    user_id = (
        message.from_user.id
    )

    # =====================================================
    # HARD PUBLIC BLOCK
    # =====================================================

    if not is_admin(
        user_id
    ):

        await message.answer(

            "🔒 <b>UPLOAD DISABLED</b>\n\n"

            "Public users video upload nahi kar sakte.",

            parse_mode="HTML"

        )

        return


    # =====================================================
    # ADMIN MUST START /ADDVIDEO
    # =====================================================

    if user_id not in pending_videos:

        await message.answer(

            "⚠️ Pehle /addvideo command bhejo."

        )

        return


    document = (
        message.document
    )


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

        mime.startswith(
            "video/"
        )

        or filename_lower.endswith(
            video_extensions
        )

    )


    if not is_video:

        await message.answer(

            "❌ Ye video file nahi lag rahi."

        )

        return


    pending_videos[
        user_id
    ]["file_id"] = (
        document.file_id
    )


    pending_videos[
        user_id
    ]["file_size"] = (
        document.file_size or 0
    )


    pending_videos[
        user_id
    ]["mime_type"] = (

        mime
        or "video/mp4"

    )


    pending_videos[
        user_id
    ]["file_name"] = (
        filename
    )


    # Telegram thumbnail
    try:

        if document.thumbnail:

            pending_videos[
                user_id
            ]["cover_file_id"] = (
                document.thumbnail.file_id
            )

    except Exception as error:

        print(
            "DOCUMENT THUMBNAIL ERROR:",
            repr(error)
        )


    await message.answer(

        "✅ <b>VIDEO FILE RECEIVED</b>\n\n"

        f"📁 {filename}\n"

        f"📦 "
        f"{(document.file_size or 0) / (1024 * 1024):.2f} MB\n\n"

        "🖼️ Ab <b>Cover Photo</b> bhejo.\n\n"

        "Ya Telegram thumbnail use karna ho "
        "to /usecover bhejo.",

        parse_mode="HTML"

    )


# =========================================================
# COVER PHOTO
#
# ONLY ADMIN
# =========================================================

@dp.message(
    F.photo
)
async def cover_received(
    message: Message
):

    user_id = (
        message.from_user.id
    )


    # -----------------------------------------------------
    # HARD ADMIN LOCK
    # -----------------------------------------------------

    if not is_admin(
        user_id
    ):

        await message.answer(

            "🔒 Sirf Admin cover photo upload kar sakta hai."

        )

        return


    # -----------------------------------------------------
    # CHECK PENDING
    # -----------------------------------------------------

    if user_id not in pending_videos:

        await message.answer(

            "⚠️ Pehle /addvideo se video add karo."

        )

        return


    photo = (
        message.photo[-1]
    )


    pending_videos[
        user_id
    ]["cover_file_id"] = (
        photo.file_id
    )


    await message.answer(

        "🖼️ <b>COVER RECEIVED</b>\n\n"

        "⏳ Video library me save ho rahi hai...",

        parse_mode="HTML"

    )


    await finalize_admin_video(
        message,
        user_id
    )


# =========================================================
# USE TELEGRAM THUMBNAIL
# =========================================================

@dp.message(
    Command("usecover")
)
async def use_cover_cmd(
    message: Message
):

    user_id = (
        message.from_user.id
    )


    if not is_admin(
        user_id
    ):
        return


    if user_id not in pending_videos:

        await message.answer(
            "❌ Pehle video bhejo."
        )

        return


    data = pending_videos[
        user_id
    ]


    if not data.get(
        "cover_file_id"
    ):

        await message.answer(

            "⚠️ Telegram thumbnail available nahi hai.\n\n"
            "Custom cover photo bhejo."

        )

        return


    await message.answer(

        "🖼️ Telegram thumbnail use ho raha hai...\n\n"
        "⏳ Please wait..."

    )


    await finalize_admin_video(
        message,
        user_id
    )


# =========================================================
# FINALIZE ADMIN VIDEO
# =========================================================

async def finalize_admin_video(
    message: Message,
    user_id: int
):

    if not is_admin(
        user_id
    ):
        return


    if user_id not in pending_videos:
        return


    data = pending_videos[
        user_id
    ]


    file_id = data.get(
        "file_id"
    )


    if not file_id:

        await message.answer(
            "❌ Video file missing."
        )

        return


    # -----------------------------------------------------
    # CREATE DATABASE RECORD
    # -----------------------------------------------------

    video_record = {

        "file_id":
            file_id,

        "file_size":
            int(
                data.get(
                    "file_size",
                    0
                )
            ),

        "mime_type":
            data.get(
                "mime_type",
                "video/mp4"
            ),

        "file_name":
            data.get(
                "file_name",
                "video.mp4"
            ),

        "cover_file_id":
            data.get(
                "cover_file_id"
            ),

    }


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    videos.append(
        video_record
    )


    save_videos()


    # -----------------------------------------------------
    # INDEX
    # -----------------------------------------------------

    video_index = (
        len(videos) - 1
    )


    # -----------------------------------------------------
    # CLEAR STATE
    # -----------------------------------------------------

    pending_videos.pop(
        user_id,
        None
    )


    # -----------------------------------------------------
    # SEND RESULT
    # -----------------------------------------------------

    await message.answer(

        "✅ <b>VIDEO ADDED SUCCESSFULLY</b>\n\n"

        f"🎬 Video #{video_index + 1}\n"

        "🖼️ Cover saved\n"
        "👉 WATCH NOW created\n"
        "💾 Permanently saved in video library\n\n"

        "👤 Ab koi bhi user /start karega "
        "to ye video uski video library me dikhegi.",

        parse_mode="HTML"

    )


    await send_video_card(
        message,
        video_index
    )


# =========================================================
# PLAYER PAGE
# =========================================================

async def player(
    request: web.Request
):

    token = (
        request.query.get(
            "t"
        )
    )


    if not token:

        return web.Response(

            text="Invalid watch link",

            status=403

        )


    video_index = verify_watch_token(
        token
    )


    if video_index is None:

        return web.Response(

            text="Invalid or expired watch link",

            status=403

        )


    data = videos[
        video_index
    ]


    file_id = data.get(
        "file_id"
    )


    size = int(
        data.get(
            "file_size",
            0
        )
    )


    mime_type = data.get(
        "mime_type",
        "video/mp4"
    )


    file_name = data.get(
        "file_name",
        "video.mp4"
    )


    stream_url = (

        f"{request.scheme}://"
        f"{request.host}"
        f"/stream?"
        f"t="
        f"{quote(token, safe='')}"

    )


    # =====================================================
    # PLAYER HTML
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
maximum-scale=1.0,
viewport-fit=cover"
>

<meta
name="theme-color"
content="#050507"
>

<title>NIGHT HUB</title>

<script src="https://telegram.org/js/telegram-web-app.js"></script>

<script src="https://sad.adsgram.ai/js/sad.min.js"></script>

<style>

* {{
    box-sizing: border-box;
}}

html,
body {{
    margin: 0;
    padding: 0;
    min-height: 100%;

    background:
        radial-gradient(
            circle at 20% 0%,
            #291640 0%,
            #0b0810 35%,
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
    min-height: 100vh;

    display: flex;
    flex-direction: column;

    align-items: center;

    padding:
        calc(16px + env(safe-area-inset-top))
        10px
        calc(24px + env(safe-area-inset-bottom));
}}

.header {{
    width: 100%;
    max-width: 1100px;

    text-align: center;
}}

.logo {{
    width: 62px;
    height: 62px;

    margin: 0 auto 10px;

    display: flex;
    align-items: center;
    justify-content: center;

    border-radius: 20px;

    background:
        linear-gradient(
            135deg,
            #a855f7,
            #4c1d95
        );

    box-shadow:
        0 15px 45px
        rgba(168,85,247,.35);

    font-size: 30px;
}}

.title {{
    margin: 0;

    font-size: 27px;
    font-weight: 900;

    letter-spacing: 1px;
}}

.subtitle {{
    margin-top: 5px;

    font-size: 12px;

    color: #96929f;
}}

.player-card {{
    width: 100%;
    max-width: 1100px;

    margin-top: 20px;

    padding: 7px;

    border-radius: 22px;

    background:
        rgba(255,255,255,.06);

    border:
        1px solid
        rgba(255,255,255,.09);

    box-shadow:
        0 25px 90px
        rgba(0,0,0,.6);

    backdrop-filter:
        blur(20px);
}}

.video-container {{
    width: 100%;

    background: #000;

    border-radius: 17px;

    overflow: hidden;
}}

video {{
    width: 100%;

    display: block;

    background: #000;

    object-fit: contain;

    max-height: 78vh;
}}

.status {{
    margin-top: 12px;

    font-size: 12px;

    color: #92909d;

    text-align: center;
}}

.badges {{
    margin-top: 10px;

    display: flex;

    justify-content: center;

    gap: 7px;

    flex-wrap: wrap;
}}

.badge {{
    padding: 6px 10px;

    border-radius: 999px;

    background:
        rgba(168,85,247,.10);

    border:
        1px solid
        rgba(168,85,247,.18);

    color: #c7a7ff;

    font-size: 10px;
}}

.ad-screen {{
    position: fixed;

    inset: 0;

    z-index: 9999;

    display: none;

    align-items: center;
    justify-content: center;

    background:
        radial-gradient(
            circle at top,
            #27143c,
            #050507 70%
        );
}}

.ad-box {{
    width: calc(100% - 40px);

    max-width: 420px;

    padding: 32px 22px;

    text-align: center;

    border-radius: 25px;

    background:
        rgba(255,255,255,.055);

    border:
        1px solid
        rgba(255,255,255,.10);

    box-shadow:
        0 30px 100px
        rgba(0,0,0,.65);
}}

.ad-icon {{
    font-size: 46px;
    margin-bottom: 12px;
}}

.ad-title {{
    font-size: 22px;
    font-weight: 800;
}}

.ad-status {{
    margin-top: 8px;

    color: #aaa6b3;

    font-size: 13px;

    line-height: 1.5;
}}

.footer {{
    margin-top: auto;

    padding-top: 30px;

    color: #55515d;

    font-size: 10px;

    letter-spacing: .6px;
}}

</style>

</head>

<body>

<div class="container">

    <div class="header">

        <div class="logo">
            🎬
        </div>

        <h1 class="title">
            NIGHT HUB
        </h1>

        <div class="subtitle">
            Premium Online Video
        </div>

    </div>


    <div class="player-card">

        <div class="video-container">

            <video
                id="videoPlayer"
                controls
                playsinline
                webkit-playsinline
                preload="metadata"
                controlsList="nodownload"
            >

                <source
                    src="{stream_url}"
                    type="{mime_type}"
                >

            </video>

        </div>

    </div>


    <div
        id="status"
        class="status"
    >
        ⏳ Preparing video...
    </div>


    <div class="badges">

        <div class="badge">
            HD+
        </div>

        <div class="badge">
            SEEK
        </div>

        <div class="badge">
            RANGE
        </div>

        <div class="badge">
            LARGE FILE
        </div>

    </div>


    <div class="footer">
        NIGHT HUB
    </div>

</div>


<div
    id="adScreen"
    class="ad-screen"
>

    <div class="ad-box">

        <div class="ad-icon">
            📺
        </div>

        <div class="ad-title">
            Advertisement
        </div>

        <div
            id="adStatus"
            class="ad-status"
        >
            Loading advertisement...
        </div>

    </div>

</div>


<script>


/* =====================================================
   TELEGRAM
===================================================== */

try {{

    if (
        window.Telegram &&
        window.Telegram.WebApp
    ) {{

        Telegram.WebApp.ready();

        Telegram.WebApp.expand();

    }}

}} catch(error) {{

    console.log(error);

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

const adScreen =
    document.getElementById(
        "adScreen"
    );

const adStatus =
    document.getElementById(
        "adStatus"
    );


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

}} catch(error) {{

    console.log(
        "AdsGram error:",
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

        adScreen.style.display =
            "flex";

        adStatus.textContent =
            "📺 Advertisement loading...";

        await adController.show();

        adStatus.textContent =
            "✅ Advertisement finished";

        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    500
                )
        );

        adScreen.style.display =
            "none";

        return true;

    }} catch(error) {{

        console.log(
            "AdsGram show error:",
            error
        );

        adStatus.textContent =
            "▶️ Starting video...";

        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    300
                )
        );

        adScreen.style.display =
            "none";

        return true;

    }}

}}


/* =====================================================
   START
===================================================== */

let started = false;

async function startVideo() {{

    if (started) {{
        return;
    }}

    started = true;

    status.textContent =
        "📺 Advertisement...";

    await showAd();

    status.textContent =
        "▶️ Starting video...";

    try {{

        await video.play();

        status.textContent =
            "▶️ NIGHT HUB";

    }} catch(error) {{

        console.log(
            "Autoplay blocked:",
            error
        );

        status.textContent =
            "▶️ Tap play to start";

    }}

}}


/* =====================================================
   FIRST USER INTERACTION
===================================================== */

document.addEventListener(
    "click",
    function() {{

        if (!started) {{

            startVideo();

        }}

    }},
    {{
        once: true
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
    "playing",
    function() {{

        status.textContent =
            "▶️ NIGHT HUB";

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

        status.textContent =
            "⏸️ Paused";

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
        # SUFFIX
        # -------------------------------------------------

        if start_text == "":

            suffix_length = int(
                end_text
            )

            if suffix_length <= 0:
                return None

            if suffix_length > file_size:

                suffix_length = (
                    file_size
                )

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

        return (
            start,
            end
        )

    except ValueError:

        return None


# =========================================================
# STREAM VIDEO
# =========================================================

async def stream_video(
    request: web.Request
):

    token = (
        request.query.get(
            "t"
        )
    )

    if not token:

        return web.Response(
            text="Forbidden",
            status=403
        )


    video_index = verify_watch_token(
        token
    )


    if video_index is None:

        return web.Response(
            text="Invalid watch token",
            status=403
        )


    data = videos[
        video_index
    ]


    file_id = data.get(
        "file_id"
    )


    file_size = int(
        data.get(
            "file_size",
            0
        )
    )


    mime_type = data.get(
        "mime_type",
        "video/mp4"
    )


    file_name = data.get(
        "file_name",
        "video.mp4"
    )


    if not file_id:

        return web.Response(
            text="Missing file",
            status=404
        )


    if file_size <= 0:

        return web.Response(
            text="Invalid file size",
            status=400
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
                    f'inline; '
                    f'filename="{file_name}"'
                ),

            "Cache-Control":
                "no-cache",

            "X-Content-Type-Options":
                "nosniff",

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
            file_size - 1
        )

        content_length = file_size

        status_code = 200


    # =====================================================
    # HEADERS
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
                f'inline; '
                f'filename="{file_name}"'
            ),

        "Cache-Control":
            "no-cache",

        "X-Content-Type-Options":
            "nosniff",

        "Access-Control-Allow-Origin":
            "*",

        "Access-Control-Allow-Headers":
            "Range",

        "Access-Control-Expose-Headers":
            (
                "Content-Length, "
                "Content-Range, "
                "Accept-Ranges"
            ),

    }


    if status_code == 206:

        headers[
            "Content-Range"
        ] = (

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
    # PYROGRAM OFFSET
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


    if chunks_needed <= 0:

        chunks_needed = 1


    # =====================================================
    # STREAM
    # =====================================================

    try:

        chunk_number = 0


        async for chunk in (

            mtproto.stream_media(

                file_id,

                offset=first_chunk,

                limit=chunks_needed

            )

        ):

            if bytes_remaining <= 0:
                break


            # ------------------------------------------------
            # REMOVE OFFSET FROM FIRST CHUNK
            # ------------------------------------------------

            if chunk_number == 0:

                if inner_offset:

                    chunk = chunk[
                        inner_offset:
                    ]


            # ------------------------------------------------
            # NEVER SEND MORE THAN REQUESTED
            # ------------------------------------------------

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


        try:

            await response.write_eof()

        except Exception:

            pass


        return response


    except asyncio.CancelledError:

        # Browser seek/pause/close.
        # Normal behaviour.

        raise


    except Exception as error:

        print(
            "======================================"
        )

        print(
            "NIGHT HUB STREAM ERROR"
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
# HEALTH
# =========================================================

async def health(
    request: web.Request
):

    return web.Response(
        text="NIGHT HUB is running ✅"
    )


# =========================================================
# WEB SERVER
# =========================================================

async def start_web_server():

    app = web.Application(

        client_max_size=(
            10
            * 1024
            * 1024
            * 1024
        )

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
        "=========================================="
    )

    print(
        "🌙 NIGHT HUB WEB SERVER STARTED"
    )

    print(
        f"PORT: {PORT}"
    )

    print(
        f"WEB_URL: {WEB_URL}"
    )

    print(
        f"VIDEOS IN DATABASE: {len(videos)}"
    )

    print(
        "ADMIN ONLY UPLOAD: ENABLED"
    )

    print(
        "VIDEO LIBRARY: ENABLED"
    )

    print(
        "COVER SYSTEM: ENABLED"
    )

    print(
        "WATCH NOW: ENABLED"
    )

    print(
        "SIGNED WATCH LINKS: ENABLED"
    )

    print(
        "RANGE/SEEK: ENABLED"
    )

    print(
        "LARGE FILE STREAMING: ENABLED"
    )

    print(
        f"AdsGram Block: {ADSGRAM_BLOCK_ID}"
    )

    print(
        "=========================================="
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    # -----------------------------------------------------
    # START MTProto
    # -----------------------------------------------------

    print(
        "Starting Telegram MTProto..."
    )


    await mtproto.start()


    print(
        "Telegram MTProto started ✅"
    )


    # -----------------------------------------------------
    # WEB
    # -----------------------------------------------------

    await start_web_server()


    # -----------------------------------------------------
    # BOT
    # -----------------------------------------------------

    print(
        "Starting NIGHT HUB bot..."
    )


    try:

        await dp.start_polling(
            bot
        )

    finally:

        print(
            "Stopping NIGHT HUB..."
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
            "NIGHT HUB stopped."
        )
