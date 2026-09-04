import os
import asyncio
import json
import shutil
import tempfile
import secrets
from pathlib import Path

from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from pyrogram import Client, filters
from pyrogram.types import Message as PyroMessage

import imageio_ffmpeg


# ============================================================
# NIGHT HUB
# 2 GB USER SESSION ARCHITECTURE
# ============================================================


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

API_ID = os.getenv("API_ID", "").strip()

API_HASH = os.getenv("API_HASH", "").strip()

ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()

SESSION_STRING = os.getenv("SESSION_STRING", "").strip()

WEB_URL = os.getenv("WEB_URL", "").strip()

WATCH_SECRET = os.getenv(
    "WATCH_SECRET",
    secrets.token_urlsafe(32)
).strip()

PORT = int(
    os.getenv(
        "PORT",
        "8080"
    )
)


# ============================================================
# VALIDATION
# ============================================================

required = {
    "BOT_TOKEN": BOT_TOKEN,
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "ADMIN_ID": ADMIN_ID,
    "CHANNEL_ID": CHANNEL_ID,
    "SESSION_STRING": SESSION_STRING,
}


for name, value in required.items():

    if not value:

        raise RuntimeError(
            f"Missing environment variable: {name}"
        )


try:

    API_ID = int(API_ID)

    ADMIN_ID = int(ADMIN_ID)

    CHANNEL_ID = int(CHANNEL_ID)

except ValueError:

    raise RuntimeError(
        "API_ID, ADMIN_ID and CHANNEL_ID must be numbers."
    )


# ============================================================
# WEB URL
# ============================================================

if not WEB_URL:

    railway_domain = os.getenv(
        "RAILWAY_PUBLIC_DOMAIN",
        ""
    ).strip()

    if railway_domain:

        WEB_URL = (
            f"https://{railway_domain}"
        )

    else:

        WEB_URL = (
            f"http://localhost:{PORT}"
        )


WEB_URL = WEB_URL.rstrip("/")


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(
    os.getenv(
        "DATA_DIR",
        "/tmp/night_hub"
    )
)

BASE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


LIBRARY_FILE = (
    BASE_DIR /
    "library.json"
)


# ============================================================
# VIDEO EXTENSIONS
# ============================================================

VIDEO_EXTENSIONS = {

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
    ".wmv",
}


# ============================================================
# FFMPEG
# ============================================================

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# ============================================================
# PYROGRAM USER SESSION
#
# IMPORTANT:
# NO bot_token here.
#
# This is a REAL Telegram USER SESSION.
# ============================================================

user_client = Client(
    name="night_hub_user",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    workdir=str(BASE_DIR),
)


# ============================================================
# LIBRARY
# ============================================================

def load_library():

    if not LIBRARY_FILE.exists():

        return {}

    try:

        with open(
            LIBRARY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, dict):

            return data

    except Exception as e:

        print(
            "LIBRARY LOAD ERROR:",
            repr(e)
        )

    return {}


library = load_library()


def save_library():

    temporary = (
        LIBRARY_FILE.with_suffix(".tmp")
    )

    with open(
        temporary,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            library,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temporary,
        LIBRARY_FILE
    )


# ============================================================
# PROCESSING STATE
# ============================================================

processing = False

current_video_name = ""


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(user_id):

    return (
        int(user_id) == ADMIN_ID
    )


# ============================================================
# ADMIN KEYBOARD
# ============================================================

def admin_keyboard():

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(
                    text="🎬 ADD VIDEO",
                    callback_data="add_video"
                ),

                InlineKeyboardButton(
                    text="📚 VIDEOS",
                    callback_data="videos"
                ),
            ],

            [

                InlineKeyboardButton(
                    text="📢 CHANNEL",
                    callback_data="channel"
                ),

                InlineKeyboardButton(
                    text="📊 STATUS",
                    callback_data="status"
                ),
            ],

            [

                InlineKeyboardButton(
                    text="🔄 REFRESH",
                    callback_data="refresh"
                ),

                InlineKeyboardButton(
                    text="❌ CLOSE",
                    callback_data="close"
                ),
            ]

        ]
    )


# ============================================================
# ADMIN TEXT
# ============================================================

def admin_text():

    return (

        "👑 <b>NIGHT HUB ADMIN PANEL</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🎬 Video Management\n"
        "🖼️ Automatic Cover\n"
        "📢 Channel Publishing\n"
        "📦 2 GB Architecture\n"
        "🚀 User Session\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "👇 Select an option:"
    )


# ============================================================
# /START
# ============================================================

@dp.message(CommandStart())
async def start_handler(
    message: Message
):

    if is_admin(
        message.from_user.id
    ):

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            "👑 Welcome Admin.\n\n"

            "🎬 Video system: ✅\n"
            "🖼️ Automatic cover: ✅\n"
            "📢 Channel upload: ✅\n"
            "📦 2 GB architecture: ✅\n\n"

            "Use <b>/admin</b>.",

            parse_mode="HTML"
        )

        return


    await message.answer(

        "🌙 <b>WELCOME TO NIGHT HUB</b>\n\n"

        "🎬 Premium Video Library\n\n"

        "Use /videos to view available videos.",

        parse_mode="HTML"
    )


# ============================================================
# /ADMIN
# ============================================================

@dp.message(Command("admin"))
async def admin_handler(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "🔒 Access denied."
        )

        return


    await message.answer(

        admin_text(),

        reply_markup=admin_keyboard(),

        parse_mode="HTML"
    )


# ============================================================
# /ADDVIDEO
# ============================================================

@dp.message(Command("addvideo"))
async def add_video_handler(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    await message.answer(

        "🎬 <b>ADD VIDEO</b>\n\n"

        "2 GB video ke liye:\n\n"

        "1️⃣ Apne authorized Telegram USER "
        "account ko video bhejo.\n\n"

        "2️⃣ User session automatically video "
        "process karega.\n\n"

        "3️⃣ FFmpeg cover banayega.\n\n"

        "4️⃣ Video directly channel mein upload hoga.",

        parse_mode="HTML"
    )


# ============================================================
# ADMIN CALLBACKS
# ============================================================

@dp.callback_query(
    F.data == "add_video"
)
async def add_video_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied",
            show_alert=True
        )

        return


    await callback.message.edit_text(

        "🎬 <b>ADD VIDEO</b>\n\n"

        "Apne authorized Telegram USER "
        "account ko video bhejo.\n\n"

        "Maximum architecture: 2 GB\n"
        "Automatic cover: ON\n"
        "Channel upload: ON",

        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(
    F.data == "videos"
)
async def videos_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        return


    count = len(
        library
    )


    await callback.message.edit_text(

        "📚 <b>VIDEO LIBRARY</b>\n\n"

        f"🎬 Total videos: <b>{count}</b>\n\n"

        "🖼️ Covers: Automatic\n"
        "📢 Channel upload: Enabled\n"
        "📦 2 GB architecture: Enabled",

        reply_markup=InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(
                        text="⬅️ BACK",
                        callback_data="back"
                    )

                ]

            ]

        ),

        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(
    F.data == "channel"
)
async def channel_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        return


    await callback.message.edit_text(

        "📢 <b>CHANNEL</b>\n\n"

        f"CHANNEL_ID:\n"
        f"<code>{CHANNEL_ID}</code>\n\n"

        "Upload system: ✅\n"
        "User session: ✅",

        reply_markup=InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(
                        text="⬅️ BACK",
                        callback_data="back"
                    )

                ]

            ]

        ),

        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(
    F.data == "status"
)
async def status_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        return


    user_status = (
        "🟢 Connected"
        if user_client.is_connected
        else
        "🔴 Disconnected"
    )


    state = (
        "🔄 Processing"
        if processing
        else
        "🟢 Idle"
    )


    await callback.message.edit_text(

        "📊 <b>NIGHT HUB STATUS</b>\n\n"

        f"🤖 Bot API: 🟢 Connected\n"
        f"👤 User Session: {user_status}\n"
        f"🎬 Processor: {state}\n"
        f"📚 Library: {len(library)} videos\n"
        f"📢 Channel: <code>{CHANNEL_ID}</code>",

        reply_markup=InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(
                        text="⬅️ BACK",
                        callback_data="back"
                    )

                ]

            ]

        ),

        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(
    F.data == "refresh"
)
async def refresh_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        return


    await callback.message.edit_text(

        admin_text(),

        reply_markup=admin_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer(
        "🔄 Refreshed"
    )


@dp.callback_query(
    F.data == "back"
)
async def back_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        return


    await callback.message.edit_text(

        admin_text(),

        reply_markup=admin_keyboard(),

        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(
    F.data == "close"
)
async def close_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        return


    try:

        await callback.message.delete()

    except Exception:

        pass

    await callback.answer()


# ============================================================
# COVER EXTRACTION
# ============================================================

async def create_cover(
    video_path,
    cover_path
):

    commands = [

        [

            FFMPEG,

            "-y",

            "-ss",
            "00:00:02",

            "-i",
            str(video_path),

            "-frames:v",
            "1",

            "-q:v",
            "2",

            str(cover_path),

        ],

        [

            FFMPEG,

            "-y",

            "-i",
            str(video_path),

            "-frames:v",
            "1",

            "-q:v",
            "2",

            str(cover_path),

        ]

    ]


    for command in commands:

        try:

            process = (
                await asyncio
                .create_subprocess_exec(
                    *command,
                    stdout=(
                        asyncio.subprocess.PIPE
                    ),
                    stderr=(
                        asyncio.subprocess.PIPE
                    ),
                )
            )


            stdout, stderr = (
                await process.communicate()
            )


            if (

                process.returncode == 0

                and cover_path.exists()

                and cover_path.stat().st_size > 0

            ):

                return True


        except Exception as e:

            print(
                "COVER ERROR:",
                repr(e)
            )


        try:

            if cover_path.exists():

                cover_path.unlink()

        except Exception:

            pass


    return False


# ============================================================
# PROGRESS CALLBACK
# ============================================================

async def progress_callback(
    current,
    total,
    status_message,
    operation
):

    try:

        now = asyncio.get_running_loop().time()

        last = getattr(
            progress_callback,
            "_last",
            0
        )


        if now - last < 4:

            return


        progress_callback._last = now


        percent = (
            current / total * 100
            if total
            else 0
        )


        current_mb = (
            current /
            1024 /
            1024
        )

        total_mb = (
            total /
            1024 /
            1024
        )


        await status_message.edit_text(

            "🌙 <b>NIGHT HUB</b>\n\n"

            f"🎬 <b>{current_video_name}</b>\n\n"

            f"{operation}\n\n"

            f"📦 {current_mb:.1f} / "
            f"{total_mb:.1f} MB\n"

            f"📊 {percent:.1f}%",

            parse_mode="HTML"
        )


    except Exception:

        pass


# ============================================================
# DOWNLOAD USER MESSAGE
# ============================================================

async def download_user_video(
    message,
    output_path,
    status_message
):

    await message.download(
        file_name=str(output_path),

        progress=progress_callback,

        progress_args=(
            status_message,
            "⬇️ Downloading video..."
        )
    )


# ============================================================
# PUBLISH VIDEO TO CHANNEL
# ============================================================

async def publish_to_channel(
    video_path,
    cover_path,
    file_name,
    status_message
):

    caption = (

        "🌙 <b>NIGHT HUB</b>\n\n"

        f"🎬 <b>{file_name}</b>\n\n"

        "🖼️ Automatic Cover: "
        f"{'✅' if cover_path else '⚠️'}\n"

        "📺 Online Player: ✅\n\n"

        "━━━━━━━━━━━━━━━━━━━━"
    )


    await status_message.edit_text(

        "📢 <b>UPLOADING TO CHANNEL...</b>\n\n"

        f"🎬 {file_name}\n\n"

        "⏳ Please wait...",

        parse_mode="HTML"
    )


    sent = await user_client.send_video(

        chat_id=CHANNEL_ID,

        video=str(video_path),

        thumb=(
            str(cover_path)
            if cover_path
            else None
        ),

        caption=caption,

        parse_mode="html",

        supports_streaming=True,

        progress=progress_callback,

        progress_args=(
            status_message,
            "📤 Uploading to channel..."
        )
    )


    return sent


# ============================================================
# PROCESS VIDEO
# ============================================================

async def process_user_video(
    message: PyroMessage
):

    global processing

    global current_video_name


    if processing:

        try:

            await message.reply_text(
                "⏳ NIGHT HUB is already processing another video."
            )

        except Exception:

            pass

        return


    if message.from_user:

        if (
            message.from_user.id
            != ADMIN_ID
        ):

            return


    media = (
        message.video
        or message.document
    )


    if not media:

        return


    file_name = (
        getattr(
            media,
            "file_name",
            None
        )
        or
        "video.mp4"
    )


    if not Path(
        file_name
    ).suffix.lower() in VIDEO_EXTENSIONS:

        if not message.video:

            return


    processing = True

    current_video_name = file_name


    temporary_directory = Path(
        tempfile.mkdtemp(
            prefix="night_hub_"
        )
    )


    video_path = (
        temporary_directory /
        Path(file_name).name
    )


    cover_path = (
        temporary_directory /
        "cover.jpg"
    )


    status_message = None


    try:

        status_message = await message.reply_text(

            "🌙 <b>NIGHT HUB</b>\n\n"

            f"🎬 <b>{file_name}</b>\n\n"

            "📦 Video received.\n"
            "⬇️ Starting download...",

            parse_mode="html"
        )


        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        await download_user_video(

            message,

            video_path,

            status_message
        )


        if not video_path.exists():

            raise RuntimeError(
                "Video download failed."
            )


        # ----------------------------------------------------
        # COVER
        # ----------------------------------------------------

        await status_message.edit_text(

            "🖼️ <b>CREATING VIDEO COVER...</b>\n\n"

            f"🎬 {file_name}\n\n"

            "⏳ FFmpeg processing...",

            parse_mode="HTML"
        )


        cover_created = (
            await create_cover(
                video_path,
                cover_path
            )
        )


        # ----------------------------------------------------
        # CHANNEL UPLOAD
        # ----------------------------------------------------

        sent = await publish_to_channel(

            video_path=video_path,

            cover_path=(
                cover_path
                if cover_created
                else None
            ),

            file_name=file_name,

            status_message=status_message
        )


        # ----------------------------------------------------
        # SAVE LIBRARY
        # ----------------------------------------------------

        message_id = (
            sent.id
        )


        media_type = "video"


        library[str(message_id)] = {

            "message_id":
                message_id,

            "channel_id":
                CHANNEL_ID,

            "name":
                file_name,

            "size":
                int(
                    getattr(
                        media,
                        "file_size",
                        0
                    )
                    or
                    0
                ),

            "cover":
                bool(
                    cover_created
                ),

            "created":
                int(
                    asyncio
                    .get_running_loop()
                    .time()
                ),

            "media_type":
                media_type,
        }


        save_library()


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        await status_message.edit_text(

            "✅ <b>VIDEO PUBLISHED SUCCESSFULLY</b>\n\n"

            f"🎬 <b>{file_name}</b>\n\n"

            f"🖼️ Cover: "
            f"{'✅' if cover_created else '⚠️'}\n"

            "📢 Channel Upload: ✅\n"

            "📦 2 GB Architecture: ✅\n"

            "👤 User Session: ✅\n\n"

            f"🆔 Message ID: "
            f"<code>{message_id}</code>",

            parse_mode="HTML"
        )


        print(
            "VIDEO PUBLISHED:",
            file_name,
            message_id
        )


    except Exception as error:

        print(
            "VIDEO PROCESS ERROR:",
            repr(error)
        )


        error_text = str(
            error
        ).replace(
            "<",
            "&lt;"
        ).replace(
            ">",
            "&gt;"
        )


        if status_message:

            try:

                await status_message.edit_text(

                    "❌ <b>VIDEO PROCESS FAILED</b>\n\n"

                    f"<code>{error_text[:3500]}</code>\n\n"

                    "⚠️ Check Railway logs.",

                    parse_mode="HTML"
                )

            except Exception:

                pass


    finally:

        processing = False

        current_video_name = ""


        shutil.rmtree(
            temporary_directory,
            ignore_errors=True
        )


# ============================================================
# PYROGRAM USER MESSAGE HANDLER
#
# THIS IS WHERE 2 GB VIDEO ENTERS THE SYSTEM.
#
# The video must be sent to the authorized USER account.
# ============================================================

@user_client.on_message(
    filters.private
    & filters.user(ADMIN_ID)
    & (
        filters.video
        | filters.document
    )
)
async def user_video_handler(
    client,
    message
):

    await process_user_video(
        message
    )


# ============================================================
# PYROGRAM STARTUP
# ============================================================

async def start_user_client():

    print(
        "Starting Telegram USER session..."
    )


    await user_client.start()


    me = await user_client.get_me()


    print(
        "=========================================="
    )

    print(
        "NIGHT HUB USER SESSION CONNECTED"
    )

    print(
        f"User ID: {me.id}"
    )

    print(
        f"Username: @{me.username}"
    )

    print(
        "2 GB USER SESSION: ENABLED"
    )

    print(
        "=========================================="
    )


# ============================================================
# WEB SERVER
# ============================================================

async def health(
    request
):

    return web.json_response({

        "status":
            "online",

        "bot":
            "NIGHT HUB",

        "user_session":
            user_client.is_connected,

        "processing":
            processing,

        "videos":
            len(library),

    })


async def home(
    request
):

    html_page = """

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>NIGHT HUB</title>

<style>

body {
    margin: 0;
    background: #050507;
    color: white;
    font-family: Arial, sans-serif;
    text-align: center;
}

.container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.card {
    padding: 30px;
    border-radius: 24px;
    background: #111116;
    border: 1px solid #292930;
}

.logo {
    font-size: 55px;
}

.title {
    font-size: 30px;
    font-weight: 900;
}

.sub {
    margin-top: 10px;
    color: #888;
}

</style>

</head>

<body>

<div class="container">

<div class="card">

<div class="logo">
🌙
</div>

<div class="title">
NIGHT HUB
</div>

<div class="sub">
Online Video Platform
</div>

</div>

</div>

</body>

</html>

"""


    return web.Response(
        text=html_page,
        content_type="text/html"
    )


async def start_web_server():

    app = web.Application()


    app.router.add_get(
        "/",
        home
    )


    app.router.add_get(
        "/health",
        health
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
        "NIGHT HUB WEB SERVER STARTED"
    )

    print(
        f"PORT: {PORT}"
    )

    print(
        f"WEB URL: {WEB_URL}"
    )

    print(
        "=========================================="
    )


# ============================================================
# BOT COMMANDS
# ============================================================

async def setup_commands():

    try:

        from aiogram.types import (
            BotCommand,
            BotCommandScopeDefault,
            BotCommandScopeChat,
        )


        await bot.set_my_commands(

            [

                BotCommand(
                    command="start",
                    description="Start NIGHT HUB"
                ),

                BotCommand(
                    command="admin",
                    description="Admin Panel"
                ),

                BotCommand(
                    command="addvideo",
                    description="Add Video"
                ),

            ],

            scope=BotCommandScopeDefault()
        )


        await bot.set_my_commands(

            [

                BotCommand(
                    command="start",
                    description="Start NIGHT HUB"
                ),

                BotCommand(
                    command="admin",
                    description="Admin Panel"
                ),

                BotCommand(
                    command="addvideo",
                    description="Add Video"
                ),

            ],

            scope=BotCommandScopeChat(
                chat_id=ADMIN_ID
            )
        )


    except Exception as error:

        print(
            "COMMAND SETUP ERROR:",
            repr(error)
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    print()
    print(
        "=========================================="
    )
    print(
        "        🌙 NIGHT HUB STARTING"
    )
    print(
        "=========================================="
    )


    # --------------------------------------------------------
    # BOT API TEST
    # --------------------------------------------------------

    bot_info = await bot.get_me()


    print(
        f"Bot: @{bot_info.username}"
    )


    # --------------------------------------------------------
    # USER SESSION
    # --------------------------------------------------------

    await start_user_client()


    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    await setup_commands()


    # --------------------------------------------------------
    # WEB SERVER
    # --------------------------------------------------------

    await start_web_server()


    # --------------------------------------------------------
    # START BOT API POLLING
    # --------------------------------------------------------

    print(
        "Bot API polling started..."
    )


    try:

        await dp.start_polling(
            bot
        )

    finally:

        try:

            await user_client.stop()

        except Exception:

            pass


        try:

            await bot.session.close()

        except Exception:

            pass


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "NIGHT HUB stopped."
        )

    except Exception as error:

        print(
            "FATAL ERROR:",
            repr(error)
        )
