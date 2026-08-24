import os
import asyncio
import time
import hmac
import hashlib
from urllib.parse import quote, urlencode

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
# COMPLETE SECURE BOT.PY
# =========================================================


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
ADMIN_ID = os.getenv("ADMIN_ID")

PORT = int(os.getenv("PORT", "8080"))

WEB_URL = os.getenv("WEB_URL")

ADSGRAM_BLOCK_ID = os.getenv(
    "ADSGRAM_BLOCK_ID",
    "int-44048"
)

# Secret used to protect WATCH / STREAM URLs.
# Railway Environment Variable recommended:
# STREAM_SECRET
STREAM_SECRET = os.getenv("STREAM_SECRET")

if not STREAM_SECRET:
    STREAM_SECRET = BOT_TOKEN


# =========================================================
# REQUIRED VARIABLES
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
    API_ID = int(API_ID)
except ValueError:
    raise RuntimeError(
        "API_ID must be numeric"
    )


try:
    ADMIN_ID = int(ADMIN_ID)
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


WEB_URL = WEB_URL.rstrip("/")


# =========================================================
# AIROGRAM
# =========================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# =========================================================
# PYROGRAM
# =========================================================

mtproto = Client(
    "night_hub_mtproto",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    no_updates=True,
    in_memory=True,
)


# =========================================================
# STREAM SETTINGS
# =========================================================

CHUNK_SIZE = 1024 * 1024

MAX_RANGE_REQUEST = 16 * 1024 * 1024

TOKEN_EXPIRY = 24 * 60 * 60


# =========================================================
# ADMIN UPLOAD STATE
#
# IMPORTANT:
#
# Video processing starts ONLY after /addvideo.
# =========================================================

pending_videos = {}


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id: int) -> bool:

    return user_id == ADMIN_ID


# =========================================================
# UPLOAD STATE CREATOR
# =========================================================

def create_upload_state():

    return {
        "active": True,
        "file_id": None,
        "file_size": 0,
        "mime_type": "video/mp4",
        "file_name": "video.mp4",
        "cover_file_id": None,
    }


# =========================================================
# SECURITY TOKEN
# =========================================================

def create_signature(
    file_id: str,
    size: int,
    mime: str,
    name: str,
    expires: int,
) -> str:

    raw = (
        f"{file_id}|"
        f"{size}|"
        f"{mime}|"
        f"{name}|"
        f"{expires}"
    )

    signature = hmac.new(
        STREAM_SECRET.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return signature


# =========================================================
# VERIFY SIGNATURE
# =========================================================

def verify_signature(
    file_id: str,
    size: int,
    mime: str,
    name: str,
    expires: int,
    signature: str,
) -> bool:

    if not signature:
        return False

    if expires <= 0:
        return False

    if int(time.time()) > expires:
        return False

    expected = create_signature(
        file_id=file_id,
        size=size,
        mime=mime,
        name=name,
        expires=expires,
    )

    return hmac.compare_digest(
        expected,
        signature,
    )


# =========================================================
# MAKE SECURE PLAY URL
# =========================================================

def make_play_url(
    file_id: str,
    size_bytes: int = 0,
    mime_type: str = "video/mp4",
    file_name: str = "video.mp4",
) -> str:

    expires = (
        int(time.time())
        + TOKEN_EXPIRY
    )

    signature = create_signature(
        file_id=file_id,
        size=size_bytes,
        mime=mime_type,
        name=file_name,
        expires=expires,
    )

    params = urlencode(
        {
            "file_id": file_id,
            "size": int(size_bytes),
            "mime": mime_type,
            "name": file_name,
            "expires": expires,
            "sig": signature,
        }
    )

    return (
        f"{WEB_URL}/watch?"
        f"{params}"
    )


# =========================================================
# EXTRACT AND VERIFY WATCH PARAMETERS
# =========================================================

def get_secure_params(request):

    file_id = request.query.get(
        "file_id"
    )

    if not file_id:
        return None

    try:

        size = int(
            request.query.get(
                "size",
                "0"
            )
        )

    except ValueError:

        return None

    mime = request.query.get(
        "mime",
        "video/mp4"
    )

    name = request.query.get(
        "name",
        "video.mp4"
    )

    try:

        expires = int(
            request.query.get(
                "expires",
                "0"
            )
        )

    except ValueError:

        return None

    signature = request.query.get(
        "sig",
        ""
    )

    if not verify_signature(
        file_id=file_id,
        size=size,
        mime=mime,
        name=name,
        expires=expires,
        signature=signature,
    ):

        return None

    return {
        "file_id": file_id,
        "size": size,
        "mime": mime,
        "name": name,
        "expires": expires,
        "sig": signature,
    }


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(
    message: Message
):

    user_id = message.from_user.id

    if is_admin(user_id):

        await message.answer(
            "🌙 <b>NIGHT HUB</b>\n\n"
            "👑 <b>ADMIN MODE</b>\n\n"
            "📹 Video upload ke liye:\n"
            "<code>/addvideo</code>\n\n"
            "Uske baad:\n"
            "1️⃣ Video bhejo\n"
            "2️⃣ Cover Photo bhejo\n"
            "3️⃣ Bot WATCH NOW banayega\n\n"
            "Commands:\n"
            "/addvideo\n"
            "/cancel\n"
            "/usecover\n"
            "/help",
            parse_mode="HTML",
        )

    else:

        await message.answer(
            "🌙 <b>NIGHT HUB</b>\n\n"
            "🎬 <b>Welcome!</b>\n\n"
            "Video dekhne ke liye "
            "👉 <b>WATCH NOW</b> button use karein.\n\n"
            "🔒 Video upload access "
            "sirf Admin ke liye hai.",
            parse_mode="HTML",
        )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_cmd(
    message: Message
):

    user_id = message.from_user.id

    if is_admin(user_id):

        await message.answer(
            "🌙 <b>NIGHT HUB ADMIN HELP</b>\n\n"
            "📌 Upload process:\n\n"
            "1️⃣ <code>/addvideo</code>\n"
            "2️⃣ Video ya forwarded video bhejo\n"
            "3️⃣ Cover Photo bhejo\n"
            "4️⃣ WATCH NOW automatically create hoga\n\n"
            "Commands:\n"
            "• /start\n"
            "• /addvideo\n"
            "• /cancel\n"
            "• /usecover\n"
            "• /help",
            parse_mode="HTML",
        )

    else:

        await message.answer(
            "🌙 <b>NIGHT HUB</b>\n\n"
            "👉 WATCH NOW button se video open karein.",
            parse_mode="HTML",
        )


# =========================================================
# ADD VIDEO
# =========================================================

@dp.message(Command("addvideo"))
async def add_video_cmd(
    message: Message
):

    user_id = message.from_user.id

    # -----------------------------------------------------
    # STRICT ADMIN CHECK
    # -----------------------------------------------------

    if not is_admin(user_id):

        await message.answer(
            "❌ <b>ACCESS DENIED</b>\n\n"
            "Sirf NIGHT HUB Admin "
            "video upload kar sakta hai.",
            parse_mode="HTML",
        )

        return

    # -----------------------------------------------------
    # CREATE NEW UPLOAD SESSION
    # -----------------------------------------------------

    pending_videos[user_id] = (
        create_upload_state()
    )

    await message.answer(
        "👑 <b>ADMIN UPLOAD MODE</b>\n\n"
        "✅ Upload mode active hai.\n\n"
        "📹 Ab video ya forwarded video bhejo.\n\n"
        "Video receive hone ke baad "
        "main Cover Photo maangunga.\n\n"
        "❌ Cancel karne ke liye:\n"
        "<code>/cancel</code>",
        parse_mode="HTML",
    )


# =========================================================
# CANCEL
# =========================================================

@dp.message(Command("cancel"))
async def cancel_cmd(
    message: Message
):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    if user_id in pending_videos:

        del pending_videos[user_id]

        await message.answer(
            "❌ <b>UPLOAD CANCELLED</b>",
            parse_mode="HTML",
        )

    else:

        await message.answer(
            "ℹ️ Koi active upload session nahi hai."
        )


# =========================================================
# SEND WATCH NOW
# =========================================================

async def send_watch_result(
    message: Message,
    file_id: str,
    size_bytes: int,
    mime_type: str,
    file_name: str,
    cover_file_id: str = None,
):

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
                    text="👉 𝐖𝐀𝐓𝐂𝐇 𝐍𝐎𝐖 👈",
                    web_app=WebAppInfo(
                        url=play_url
                    ),
                )
            ]
        ]
    )

    # -----------------------------------------------------
    # CUSTOM COVER
    # -----------------------------------------------------

    if cover_file_id:

        try:

            await message.answer_photo(
                photo=cover_file_id,
                caption=(
                    "🌙 <b>NIGHT HUB</b>\n\n"
                    "🎬 <b>Video Ready</b>\n\n"
                    "👇 Watch karne ke liye "
                    "<b>WATCH NOW</b> dabayein."
                ),
                reply_markup=keyboard,
                protect_content=True,
                parse_mode="HTML",
            )

            return

        except Exception as error:

            print(
                "Custom cover error:",
                repr(error),
            )

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    await message.answer(
        "🌙 <b>NIGHT HUB</b>\n\n"
        "🎬 <b>Video Ready</b>\n\n"
        "👇 Video dekhne ke liye "
        "<b>WATCH NOW</b> dabayein.",
        reply_markup=keyboard,
        parse_mode="HTML",
        protect_content=True,
    )


# =========================================================
# FINALIZE ADMIN VIDEO
# =========================================================

async def finalize_admin_video(
    message: Message,
    user_id: int,
):

    if not is_admin(user_id):
        return

    if user_id not in pending_videos:
        return

    data = pending_videos[user_id]

    file_id = data.get(
        "file_id"
    )

    if not file_id:

        await message.answer(
            "❌ Video information missing."
        )

        return

    file_size = data.get(
        "file_size",
        0,
    )

    mime_type = data.get(
        "mime_type",
        "video/mp4",
    )

    file_name = data.get(
        "file_name",
        "video.mp4",
    )

    cover_file_id = data.get(
        "cover_file_id"
    )

    # -----------------------------------------------------
    # DELETE SESSION
    # -----------------------------------------------------

    del pending_videos[user_id]

    # -----------------------------------------------------
    # CREATE WATCH NOW
    # -----------------------------------------------------

    await send_watch_result(
        message=message,
        file_id=file_id,
        size_bytes=file_size,
        mime_type=mime_type,
        file_name=file_name,
        cover_file_id=cover_file_id,
    )


# =========================================================
# VIDEO RECEIVED
#
# IMPORTANT:
# Admin MUST use /addvideo first.
# =========================================================

@dp.message(F.video)
async def video_received(
    message: Message
):

    user_id = message.from_user.id

    # -----------------------------------------------------
    # NORMAL USER
    # -----------------------------------------------------

    if not is_admin(user_id):

        await message.answer(
            "🔒 <b>UPLOAD DISABLED</b>\n\n"
            "Sirf NIGHT HUB Admin "
            "videos upload kar sakta hai.",
            parse_mode="HTML",
        )

        return

    # -----------------------------------------------------
    # ADMIN BUT NO ACTIVE SESSION
    # -----------------------------------------------------

    if user_id not in pending_videos:

        await message.answer(
            "⚠️ <b>UPLOAD MODE OFF</b>\n\n"
            "Pehle <code>/addvideo</code> bhejo.",
            parse_mode="HTML",
        )

        return

    # -----------------------------------------------------
    # GET VIDEO
    # -----------------------------------------------------

    video = message.video

    pending_videos[user_id]["file_id"] = (
        video.file_id
    )

    pending_videos[user_id]["file_size"] = (
        video.file_size or 0
    )

    pending_videos[user_id]["mime_type"] = (
        video.mime_type or "video/mp4"
    )

    pending_videos[user_id]["file_name"] = (
        video.file_name or "video.mp4"
    )

    # -----------------------------------------------------
    # TELEGRAM THUMBNAIL
    # -----------------------------------------------------

    try:

        if video.thumbnail:

            pending_videos[user_id][
                "cover_file_id"
            ] = video.thumbnail.file_id

    except Exception as error:

        print(
            "Video thumbnail error:",
            repr(error),
        )

    # -----------------------------------------------------
    # ASK COVER
    # -----------------------------------------------------

    await message.answer(
        "✅ <b>VIDEO RECEIVED</b>\n\n"
        f"📁 <b>{video.file_name or 'video.mp4'}</b>\n"
        f"📦 Size: "
        f"{(video.file_size or 0) / (1024 * 1024):.2f} MB\n\n"
        "🖼️ Ab <b>Cover Photo</b> bhejo.\n\n"
        "Agar Telegram thumbnail use karna hai:\n"
        "<code>/usecover</code>",
        parse_mode="HTML",
    )


# =========================================================
# DOCUMENT VIDEO
#
# Supports forwarded video files as Documents.
# =========================================================

@dp.message(F.document)
async def document_received(
    message: Message
):

    user_id = message.from_user.id

    # -----------------------------------------------------
    # NORMAL USER
    # -----------------------------------------------------

    if not is_admin(user_id):

        await message.answer(
            "🔒 <b>UPLOAD DISABLED</b>\n\n"
            "Sirf NIGHT HUB Admin "
            "videos upload kar sakta hai.",
            parse_mode="HTML",
        )

        return

    # -----------------------------------------------------
    # ADMIN BUT NO ACTIVE SESSION
    # -----------------------------------------------------

    if user_id not in pending_videos:

        await message.answer(
            "⚠️ <b>UPLOAD MODE OFF</b>\n\n"
            "Pehle <code>/addvideo</code> bhejo.",
            parse_mode="HTML",
        )

        return

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
        or filename_lower.endswith(
            video_extensions
        )
    )

    if not is_video:

        await message.answer(
            "📄 File received.\n\n"
            "❌ Ye video file nahi lag rahi."
        )

        return

    # -----------------------------------------------------
    # SAVE FILE
    # -----------------------------------------------------

    pending_videos[user_id]["file_id"] = (
        document.file_id
    )

    pending_videos[user_id]["file_size"] = (
        document.file_size or 0
    )

    pending_videos[user_id]["mime_type"] = (
        mime or "video/mp4"
    )

    pending_videos[user_id]["file_name"] = (
        filename
    )

    # -----------------------------------------------------
    # DOCUMENT THUMBNAIL
    # -----------------------------------------------------

    try:

        if document.thumbnail:

            pending_videos[user_id][
                "cover_file_id"
            ] = document.thumbnail.file_id

    except Exception as error:

        print(
            "Document thumbnail error:",
            repr(error),
        )

    await message.answer(
        "✅ <b>VIDEO FILE RECEIVED</b>\n\n"
        f"📁 <b>{filename}</b>\n"
        f"📦 Size: "
        f"{(document.file_size or 0) / (1024 * 1024):.2f} MB\n\n"
        "🖼️ Ab <b>Cover Photo</b> bhejo.\n\n"
        "Telegram thumbnail use karna hai:\n"
        "<code>/usecover</code>",
        parse_mode="HTML",
    )


# =========================================================
# COVER PHOTO
# =========================================================

@dp.message(F.photo)
async def cover_received(
    message: Message
):

    user_id = message.from_user.id

    # -----------------------------------------------------
    # NORMAL USER
    # -----------------------------------------------------

    if not is_admin(user_id):

        await message.answer(
            "🔒 Sirf Admin cover upload kar sakta hai."
        )

        return

    # -----------------------------------------------------
    # NO ACTIVE SESSION
    # -----------------------------------------------------

    if user_id not in pending_videos:

        await message.answer(
            "⚠️ Pehle <code>/addvideo</code> bhejo.",
            parse_mode="HTML",
        )

        return

    # -----------------------------------------------------
    # GET HIGHEST QUALITY PHOTO
    # -----------------------------------------------------

    photo = message.photo[-1]

    pending_videos[user_id][
        "cover_file_id"
    ] = photo.file_id

    await message.answer(
        "🖼️ <b>COVER RECEIVED</b>\n\n"
        "⏳ Creating WATCH NOW...\n\n"
        "Please wait...",
        parse_mode="HTML",
    )

    await finalize_admin_video(
        message=message,
        user_id=user_id,
    )


# =========================================================
# USE TELEGRAM COVER
# =========================================================

@dp.message(Command("usecover"))
async def use_cover_cmd(
    message: Message
):

    user_id = message.from_user.id

    if not is_admin(user_id):
        return

    if user_id not in pending_videos:

        await message.answer(
            "❌ Pehle <code>/addvideo</code> "
            "aur video bhejo.",
            parse_mode="HTML",
        )

        return

    data = pending_videos[user_id]

    if not data.get("cover_file_id"):

        await message.answer(
            "⚠️ Telegram thumbnail available nahi hai.\n\n"
            "Please custom Cover Photo bhejo."
        )

        return

    await message.answer(
        "🖼️ Telegram thumbnail ko Cover ke "
        "roop mein use kiya ja raha hai...\n\n"
        "⏳ Please wait..."
    )

    await finalize_admin_video(
        message=message,
        user_id=user_id,
    )


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
# MINI APP PLAYER
# =========================================================

async def player(
    request: web.Request
):

    params = get_secure_params(
        request
    )

    if not params:

        return web.Response(
            text="Invalid or expired video link.",
            status=403,
        )

    file_id = params["file_id"]
    size = params["size"]
    mime_type = params["mime"]
    file_name = params["name"]
    expires = params["expires"]
    signature = params["sig"]

    # -----------------------------------------------------
    # SECURE STREAM URL
    # -----------------------------------------------------

    stream_params = urlencode(
        {
            "file_id": file_id,
            "size": size,
            "mime": mime_type,
            "name": file_name,
            "expires": expires,
            "sig": signature,
        }
    )

    video_url = (
        f"{request.scheme}://"
        f"{request.host}"
        f"/stream?"
        f"{stream_params}"
    )

    # =====================================================
    # MINI APP HTML
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
            circle at 20% 0%,
            #26183d 0%,
            #0b0911 35%,
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
    overflow-x: hidden;
}}

.container {{
    width: 100%;
    min-height: 100vh;

    display: flex;
    flex-direction: column;
    align-items: center;

    padding:
        calc(18px + env(safe-area-inset-top))
        12px
        calc(24px + env(safe-area-inset-bottom));
}}

.header {{
    width: 100%;
    max-width: 1000px;

    display: flex;
    align-items: center;
    justify-content: center;

    flex-direction: column;
}}

.logo {{
    width: 68px;
    height: 68px;

    border-radius: 22px;

    display: flex;
    align-items: center;
    justify-content: center;

    background:
        linear-gradient(
            135deg,
            #9b4dff,
            #4a00ff
        );

    box-shadow:
        0 10px 40px
        rgba(108,55,255,0.35);

    font-size: 32px;

    margin-top: 4px;
    margin-bottom: 12px;
}}

.title {{
    margin: 0;

    font-size: 28px;

    font-weight: 900;

    letter-spacing: 1px;

    text-align: center;
}}

.subtitle {{
    margin-top: 6px;

    color: #9997a7;

    font-size: 13px;

    text-align: center;
}}

.player-card {{
    width: 100%;
    max-width: 1000px;

    margin-top: 24px;

    padding: 8px;

    border-radius: 22px;

    background:
        linear-gradient(
            145deg,
            rgba(255,255,255,0.10),
            rgba(255,255,255,0.025)
        );

    border:
        1px solid
        rgba(255,255,255,0.10);

    box-shadow:
        0 25px 80px
        rgba(0,0,0,0.55);

    backdrop-filter:
        blur(18px);
}}

.video-container {{
    width: 100%;

    background: #000;

    border-radius: 16px;

    overflow: hidden;

    position: relative;
}}

video {{
    display: block;

    width: 100%;

    max-height: 75vh;

    background: #000;

    object-fit: contain;

    border-radius: 16px;
}}

.ad-screen {{
    position: fixed;

    inset: 0;

    z-index: 9999;

    display: none;

    align-items: center;
    justify-content: center;

    flex-direction: column;

    padding: 25px;

    background:
        radial-gradient(
            circle at top,
            #241438,
            #050507 65%
        );
}}

.ad-box {{
    width: 100%;
    max-width: 420px;

    padding: 30px 20px;

    border-radius: 24px;

    text-align: center;

    background:
        rgba(255,255,255,0.055);

    border:
        1px solid
        rgba(255,255,255,0.10);

    box-shadow:
        0 25px 80px
        rgba(0,0,0,0.55);
}}

.ad-icon {{
    font-size: 48px;

    margin-bottom: 15px;
}}

.ad-title {{
    font-size: 22px;

    font-weight: 800;

    margin-bottom: 8px;
}}

.ad-status {{
    color: #a9a6b4;

    font-size: 13px;

    line-height: 1.5;
}}

.status {{
    width: 100%;
    max-width: 1000px;

    margin-top: 13px;

    padding: 10px;

    color: #9693a2;

    font-size: 12px;

    text-align: center;
}}

.info-row {{
    width: 100%;
    max-width: 1000px;

    display: flex;

    justify-content: center;

    gap: 8px;

    margin-top: 7px;

    flex-wrap: wrap;
}}

.badge {{
    padding: 7px 11px;

    border-radius: 999px;

    background:
        rgba(139,44,255,0.12);

    border:
        1px solid
        rgba(139,44,255,0.18);

    color: #bba0ff;

    font-size: 11px;
}}

.brand {{
    margin-top: auto;

    padding-top: 30px;

    color: #5f5d69;

    font-size: 11px;

    letter-spacing: 0.5px;

    text-align: center;
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
                    src="{video_url}"
                    type="{mime_type}"
                >

                Your browser does not support
                HTML5 video.

            </video>

        </div>

    </div>


    <div
        id="status"
        class="status"
    >
        ⏳ Preparing video...
    </div>


    <div class="info-row">

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


    <div class="brand">
        🌙 NIGHT HUB
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
   TELEGRAM WEB APP
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

    console.log(
        "Telegram error:",
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
        "AdsGram init error:",
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
                    400
                )
        );

        adScreen.style.display =
            "none";

        return true;

    }} catch(error) {{

        console.log(
            "AdsGram error:",
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
   START VIDEO
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
            "Autoplay error:",
            error
        );

        status.textContent =
            "▶️ Tap the video to play";

    }}

}}


/* =====================================================
   USER INTERACTION
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
        content_type="text/html",
    )


# =========================================================
# RANGE PARSER
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

    start_text = (
        parts[0].strip()
    )

    end_text = (
        parts[1].strip()
    )

    try:

        # -------------------------------------------------
        # Suffix range
        # Example: bytes=-500
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
                file_size
                - 1
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

        return start, end

    except ValueError:

        return None


# =========================================================
# STREAM VIDEO
# =========================================================

async def stream_video(
    request: web.Request
):

    # -----------------------------------------------------
    # SECURITY
    # -----------------------------------------------------

    params = get_secure_params(
        request
    )

    if not params:

        return web.Response(
            text="Invalid or expired stream link.",
            status=403,
        )

    file_id = params["file_id"]
    file_size = params["size"]
    mime_type = params["mime"]
    file_name = params["name"]

    if file_size <= 0:

        return web.Response(
            text="Invalid file size.",
            status=400,
        )

    # -----------------------------------------------------
    # RANGE
    # -----------------------------------------------------

    range_header = request.headers.get(
        "Range"
    )

    requested_range = parse_range(
        range_header,
        file_size,
    )

    # -----------------------------------------------------
    # HEAD
    # -----------------------------------------------------

    if request.method == "HEAD":

        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Disposition": (
                f'inline; filename="{file_name}"'
            ),
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        }

        return web.Response(
            status=200,
            headers=headers,
        )

    # -----------------------------------------------------
    # RANGE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # RESPONSE HEADERS
    # -----------------------------------------------------

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

        headers["Content-Range"] = (
            f"bytes "
            f"{start_byte}-"
            f"{end_byte}/"
            f"{file_size}"
        )

    # -----------------------------------------------------
    # STREAM RESPONSE
    # -----------------------------------------------------

    response = web.StreamResponse(
        status=status_code,
        headers=headers,
    )

    await response.prepare(
        request
    )

    # -----------------------------------------------------
    # PYROGRAM OFFSET
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # PROTECT HUGE REQUESTS
    # -----------------------------------------------------

    max_chunks = (
        MAX_RANGE_REQUEST
        // CHUNK_SIZE
    )

    if chunks_needed > max_chunks:

        chunks_needed = max_chunks

    # -----------------------------------------------------
    # STREAM
    # -----------------------------------------------------

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
            # Remove bytes before requested start
            # ---------------------------------------------

            if chunk_number == 0:

                if inner_offset:

                    chunk = (
                        chunk[
                            inner_offset:
                        ]
                    )

            # ---------------------------------------------
            # Do not send extra bytes
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

        # Browser cancelled request,
        # usually because user seeked.
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
    # WATCH
    # -----------------------------------------------------

    app.router.add_get(
        "/watch",
        player
    )

    # -----------------------------------------------------
    # STREAM GET
    # -----------------------------------------------------

    app.router.add_route(
        "GET",
        "/stream",
        stream_video
    )

    # -----------------------------------------------------
    # STREAM HEAD
    # -----------------------------------------------------

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
        PORT,
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
        "MTProto: ENABLED"
    )

    print(
        "Large streaming: ENABLED"
    )

    print(
        "Range/Seek: ENABLED"
    )

    print(
        "ADMIN ONLY UPLOAD: ENABLED"
    )

    print(
        "ADDVIDEO REQUIRED: ENABLED"
    )

    print(
        "COVER SYSTEM: ENABLED"
    )

    print(
        "WATCH NOW: ENABLED"
    )

    print(
        "SECURE STREAM URL: ENABLED"
    )

    print(
        f"AdsGram: {ADSGRAM_BLOCK_ID}"
    )

    print(
        "=========================================="
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    # -----------------------------------------------------
    # MTProto
    # -----------------------------------------------------

    print(
        "Starting Telegram MTProto client..."
    )

    await mtproto.start()

    print(
        "Telegram MTProto started ✅"
    )

    # -----------------------------------------------------
    # WEB SERVER
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
