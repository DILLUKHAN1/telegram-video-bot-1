import os
import asyncio
import secrets
import tempfile
from urllib.parse import quote
from pathlib import Path

from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
    FSInputFile,
)

from pyrogram import Client

import imageio_ffmpeg


# =========================================================
#                    NIGHT HUB
#          TELEGRAM VIDEO BOT + MINI APP
# =========================================================


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
ADMIN_ID = os.getenv("ADMIN_ID")
WEB_URL = os.getenv("WEB_URL")
CHANNEL_ID = os.getenv("CHANNEL_ID")
WATCH_SECRET = os.getenv("WATCH_SECRET")

PORT = int(os.getenv("PORT", "8080"))

ADSGRAM_BLOCK_ID = os.getenv(
    "ADSGRAM_BLOCK_ID",
    ""
)


# =========================================================
# REQUIRED VARIABLES
# =========================================================

required_variables = {
    "BOT_TOKEN": BOT_TOKEN,
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "ADMIN_ID": ADMIN_ID,
    "CHANNEL_ID": CHANNEL_ID,
    "WATCH_SECRET": WATCH_SECRET,
}

for name, value in required_variables.items():

    if not value:

        raise RuntimeError(
            f"{name} environment variable is missing"
        )


# =========================================================
# CONVERT IDs
# =========================================================

try:

    ADMIN_ID = int(ADMIN_ID)

except ValueError:

    raise RuntimeError(
        "ADMIN_ID must be a numeric Telegram User ID"
    )


try:

    CHANNEL_ID = int(CHANNEL_ID)

except ValueError:

    raise RuntimeError(
        "CHANNEL_ID must be a numeric Telegram Channel ID"
    )


try:

    API_ID = int(API_ID)

except ValueError:

    raise RuntimeError(
        "API_ID must be numeric"
    )


# =========================================================
# WEB URL
# =========================================================

if not WEB_URL:

    railway_domain = os.getenv(
        "RAILWAY_PUBLIC_DOMAIN"
    )

    if railway_domain:

        WEB_URL = (
            f"https://{railway_domain}"
        )

    else:

        WEB_URL = (
            f"http://localhost:{PORT}"
        )


WEB_URL = WEB_URL.rstrip("/")


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
    "night_hub_mtproto",

    api_id=API_ID,

    api_hash=API_HASH,

    bot_token=BOT_TOKEN,

    no_updates=True,

    in_memory=True,
)


# =========================================================
# SETTINGS
# =========================================================

CHUNK_SIZE = 1024 * 1024

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024

VIDEO_EXTENSIONS = (
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


# =========================================================
# STORAGE
# =========================================================

watch_tokens = {}

video_library = {}

processing_videos = set()


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id: int) -> bool:

    return user_id == ADMIN_ID


# =========================================================
# FFMPEG
# =========================================================

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()


# =========================================================
# MAKE WATCH URL
# =========================================================

def make_watch_url(
    file_id: str,
    size_bytes: int,
    mime_type: str,
    file_name: str,
):

    token = secrets.token_urlsafe(32)

    watch_tokens[token] = {

        "file_id": file_id,

        "size": int(size_bytes or 0),

        "mime": mime_type or "video/mp4",

        "name": file_name or "video.mp4",

    }

    return (
        f"{WEB_URL}/watch?"
        f"token={quote(token, safe='')}"
    )


# =========================================================
# WATCH KEYBOARD
# =========================================================

def watch_keyboard(
    file_id: str,
    size_bytes: int,
    mime_type: str,
    file_name: str,
):

    watch_url = make_watch_url(

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

                        url=watch_url

                    ),

                )

            ]

        ]

    )


# =========================================================
# ADMIN PANEL KEYBOARD
# =========================================================

def admin_panel_keyboard():

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="🎬 ADD VIDEO",

                    callback_data="admin_add_video",

                ),

                InlineKeyboardButton(

                    text="📚 VIDEOS",

                    callback_data="admin_videos",

                ),

            ],

            [

                InlineKeyboardButton(

                    text="📢 CHANNEL",

                    callback_data="admin_channel",

                ),

                InlineKeyboardButton(

                    text="👥 USERS",

                    callback_data="admin_users",

                ),

            ],

            [

                InlineKeyboardButton(

                    text="🔄 REFRESH",

                    callback_data="admin_refresh",

                ),

            ],

            [

                InlineKeyboardButton(

                    text="❌ CLOSE",

                    callback_data="admin_close",

                ),

            ],

        ]

    )


# =========================================================
# ADMIN PANEL TEXT
# =========================================================

def admin_panel_text():

    return (

        "👑 <b>NIGHT HUB ADMIN PANEL</b>\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"

        "🎬 Video Management\n"
        "📢 Private Channel\n"
        "👥 User Access\n"
        "🎥 Mini App\n"
        "🖼️ Auto Video Cover\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "👇 Select an option:"

    )


# =========================================================
# EXTRACT COVER
# =========================================================

async def extract_video_cover(
    video_path: str,
    output_path: str,
):

    commands = [

        [

            FFMPEG_PATH,

            "-y",

            "-ss",
            "00:00:02",

            "-i",
            video_path,

            "-frames:v",
            "1",

            "-q:v",
            "2",

            output_path,

        ],

        [

            FFMPEG_PATH,

            "-y",

            "-i",
            video_path,

            "-frames:v",
            "1",

            "-q:v",
            "2",

            output_path,

        ],

    ]

    for command in commands:

        try:

            process = (
                await asyncio.create_subprocess_exec(

                    *command,

                    stdout=asyncio.subprocess.PIPE,

                    stderr=asyncio.subprocess.PIPE,

                )
            )

            stdout, stderr = (
                await process.communicate()
            )

            if (

                process.returncode == 0

                and os.path.exists(output_path)

                and os.path.getsize(output_path) > 0

            ):

                return True

        except Exception as error:

            print(
                "FFMPEG ERROR:",
                repr(error)
            )

        try:

            if os.path.exists(output_path):

                os.remove(output_path)

        except Exception:

            pass

    return False


# =========================================================
# DOWNLOAD VIDEO USING PYROGRAM
# =========================================================

async def download_video_temp(
    message: Message,
    file_id: str,
    file_name: str,
):

    temp_dir = tempfile.mkdtemp(
        prefix="night_hub_"
    )

    safe_name = (
        Path(file_name).name
        or "video.mp4"
    )

    video_path = os.path.join(
        temp_dir,
        safe_name
    )

    try:

        print(
            "Getting Telegram message through MTProto..."
        )

        pyro_message = await mtproto.get_messages(

            chat_id=message.chat.id,

            message_ids=message.message_id,

        )

        if not pyro_message:

            raise RuntimeError(
                "Pyrogram could not find the uploaded message."
            )

        if not (
            pyro_message.video
            or pyro_message.document
        ):

            raise RuntimeError(
                "Video media was not found."
            )

        print(
            "Downloading video using Pyrogram MTProto..."
        )

        downloaded_path = (
            await mtproto.download_media(

                pyro_message,

                file_name=video_path,

            )
        )

        if not downloaded_path:

            raise RuntimeError(
                "Pyrogram download failed."
            )

        if not os.path.exists(
            downloaded_path
        ):

            raise RuntimeError(
                "Downloaded file does not exist."
            )

        downloaded_size = os.path.getsize(
            downloaded_path
        )

        print(
            "=========================================="
        )

        print(
            "VIDEO DOWNLOAD SUCCESS"
        )

        print(
            f"File: {downloaded_path}"
        )

        print(
            f"Size: "
            f"{downloaded_size / (1024 * 1024):.2f} MB"
        )

        print(
            "=========================================="
        )

        return (
            temp_dir,
            downloaded_path
        )

    except Exception as error:

        print(
            "PYROGRAM DOWNLOAD ERROR:",
            repr(error)
        )

        cleanup_temp_dir(
            temp_dir
        )

        raise


# =========================================================
# CLEANUP TEMP DIRECTORY
# =========================================================

def cleanup_temp_dir(
    temp_dir: str
):

    try:

        if not os.path.isdir(
            temp_dir
        ):

            return

        for item in os.listdir(
            temp_dir
        ):

            path = os.path.join(
                temp_dir,
                item
            )

            try:

                if os.path.isfile(path):

                    os.remove(path)

            except Exception:

                pass

        try:

            os.rmdir(temp_dir)

        except Exception:

            pass

    except Exception:

        pass


# =========================================================
# PUBLISH VIDEO TO CHANNEL
# =========================================================

async def publish_video_to_channel(

    file_id: str,

    file_size: int,

    mime_type: str,

    file_name: str,

    cover_path: str | None,

):

    caption = (

        "🌙 <b>NIGHT HUB</b>\n\n"

        f"🎬 <b>{file_name}</b>\n\n"

        "👉 Watch this video below."

    )

    # =====================================================
    # IMPORTANT:
    # WATCH NOW BUTTON
    # =====================================================

    keyboard = watch_keyboard(

        file_id=file_id,

        size_bytes=file_size,

        mime_type=mime_type,

        file_name=file_name,

    )

    # =====================================================
    # BOT API PUBLISH
    # =====================================================

    try:

        print(
            "Publishing video to channel using Bot API..."
        )

        if (

            cover_path

            and os.path.exists(
                cover_path
            )

        ):

            sent = await bot.send_video(

                chat_id=CHANNEL_ID,

                video=file_id,

                thumbnail=FSInputFile(
                    cover_path
                ),

                caption=caption,

                parse_mode="HTML",

                supports_streaming=True,

                protect_content=True,

                # IMPORTANT
                reply_markup=keyboard,

            )

        else:

            sent = await bot.send_video(

                chat_id=CHANNEL_ID,

                video=file_id,

                caption=caption,

                parse_mode="HTML",

                supports_streaming=True,

                protect_content=True,

                # IMPORTANT
                reply_markup=keyboard,

            )

        print(
            "Channel publish successful ✅"
        )

        return sent

    except Exception as error:

        print(
            "Bot API channel publish failed:"
        )

        print(
            repr(error)
        )

        print(
            "Trying Pyrogram fallback..."
        )

    # =====================================================
    # PYROGRAM FALLBACK
    # =====================================================

    try:

        if (

            cover_path

            and os.path.exists(
                cover_path
            )

        ):

            sent = await mtproto.send_video(

                chat_id=CHANNEL_ID,

                video=file_id,

                thumb=cover_path,

                caption=caption,

                parse_mode="HTML",

                supports_streaming=True,

                reply_markup=keyboard,

            )

        else:

            sent = await mtproto.send_video(

                chat_id=CHANNEL_ID,

                video=file_id,

                caption=caption,

                parse_mode="HTML",

                supports_streaming=True,

                reply_markup=keyboard,

            )

        print(
            "Pyrogram channel publish successful ✅"
        )

        return sent

    except Exception as error:

        print(
            "PYROGRAM CHANNEL PUBLISH ERROR:",
            repr(error)
        )

        raise RuntimeError(
            f"Channel publish failed: {error}"
        )


# =========================================================
# PROCESS ONE VIDEO
# =========================================================

async def process_one_video(
    message: Message,
):

    user_id = message.from_user.id

    if not is_admin(user_id):

        return

    file_id = None

    file_size = 0

    mime_type = "video/mp4"

    file_name = "video.mp4"

    # =====================================================
    # VIDEO
    # =====================================================

    if message.video:

        video = message.video

        file_id = video.file_id

        file_size = video.file_size or 0

        mime_type = (
            video.mime_type
            or "video/mp4"
        )

        file_name = (
            video.file_name
            or "video.mp4"
        )

    # =====================================================
    # DOCUMENT
    # =====================================================

    elif message.document:

        document = message.document

        file_id = document.file_id

        file_size = document.file_size or 0

        mime_type = (
            document.mime_type
            or "application/octet-stream"
        )

        file_name = (
            document.file_name
            or "video.mp4"
        )

        is_video = (

            mime_type.startswith("video/")

            or file_name.lower().endswith(
                VIDEO_EXTENSIONS
            )

        )

        if not is_video:

            return

    else:

        return

    # =====================================================
    # SIZE CHECK
    # =====================================================

    if file_size > MAX_FILE_SIZE:

        await message.answer(

            "❌ <b>VIDEO TOO LARGE</b>\n\n"

            "Maximum supported size is 2 GB.",

            parse_mode="HTML"

        )

        return

    # =====================================================
    # DUPLICATE PROCESS CHECK
    # =====================================================

    if file_id in processing_videos:

        await message.answer(
            "⏳ Ye video already processing mein hai."
        )

        return

    processing_videos.add(file_id)

    temp_dir = None

    cover_path = None

    status_message = None

    try:

        # =================================================
        # STATUS
        # =================================================

        status_message = await message.answer(

            "🎬 <b>VIDEO RECEIVED</b>\n\n"

            f"📁 {file_name}\n"

            f"📦 "
            f"{file_size / (1024 * 1024):.2f} MB\n\n"

            "📥 MTProto se video download ho rahi hai...\n\n"

            "⏳ Please wait...",

            parse_mode="HTML"

        )

        # =================================================
        # DOWNLOAD USING PYROGRAM
        # =================================================

        temp_dir, video_path = (
            await download_video_temp(

                message=message,

                file_id=file_id,

                file_name=file_name,

            )
        )

        # =================================================
        # COVER
        # =================================================

        cover_path = os.path.join(

            temp_dir,

            "cover.jpg"

        )

        # =================================================
        # EXTRACT COVER
        # =================================================

        await status_message.edit_text(

            "🖼️ <b>CREATING COVER</b>\n\n"

            "Video se automatic cover nikali ja rahi hai...\n\n"

            "⏳ Please wait...",

            parse_mode="HTML"

        )

        cover_ok = await extract_video_cover(

            video_path=video_path,

            output_path=cover_path,

        )

        if cover_ok:

            await status_message.edit_text(

                "🖼️ <b>COVER READY ✅</b>\n\n"

                "📢 Video channel mein publish ho rahi hai...\n\n"

                "⏳ Please wait...",

                parse_mode="HTML"

            )

        else:

            cover_path = None

            await status_message.edit_text(

                "⚠️ <b>COVER EXTRACT NAHI HO SAKI</b>\n\n"

                "📢 Video channel mein publish ho rahi hai...\n\n"

                "⏳ Please wait...",

                parse_mode="HTML"

            )

        # =================================================
        # PUBLISH
        # =================================================

        channel_message = (

            await publish_video_to_channel(

                file_id=file_id,

                file_size=file_size,

                mime_type=mime_type,

                file_name=file_name,

                cover_path=cover_path,

            )

        )

        # =================================================
        # CHANNEL MESSAGE ID
        # =================================================

        channel_message_id = getattr(

            channel_message,

            "message_id",

            None

        )

        if channel_message_id is None:

            channel_message_id = getattr(

                channel_message,

                "id",

                0

            )

        # =================================================
        # SAVE LIBRARY
        # =================================================

        video_library[channel_message_id] = {

            "file_id": file_id,

            "size": file_size,

            "mime": mime_type,

            "name": file_name,

            "message_id": channel_message_id,

        }

        # =================================================
        # WATCH BUTTON
        # =================================================

        keyboard = watch_keyboard(

            file_id=file_id,

            size_bytes=file_size,

            mime_type=mime_type,

            file_name=file_name,

        )

        # =================================================
        # SUCCESS MESSAGE
        # =================================================

        if (

            cover_path

            and os.path.exists(
                cover_path
            )

        ):

            try:

                await message.answer_photo(

                    photo=FSInputFile(
                        cover_path
                    ),

                    caption=(

                        "✅ <b>VIDEO PUBLISHED</b>\n\n"

                        f"🎬 <b>{file_name}</b>\n\n"

                        "🖼️ Cover: ✅\n"

                        "📢 Channel: ✅\n"

                        "👉 WATCH NOW: ✅\n"

                        "🎥 Mini App: ✅"

                    ),

                    reply_markup=keyboard,

                    parse_mode="HTML",

                    protect_content=True,

                )

            except Exception as error:

                print(
                    "SUCCESS PHOTO ERROR:",
                    repr(error)
                )

                await message.answer(

                    "✅ <b>VIDEO PUBLISHED</b>\n\n"

                    f"🎬 <b>{file_name}</b>\n\n"

                    "🖼️ Cover: ✅\n"
                    "📢 Channel: ✅\n"
                    "👉 WATCH NOW: ✅\n"
                    "🎥 Mini App: ✅",

                    reply_markup=keyboard,

                    parse_mode="HTML",

                    protect_content=True,

                )

        else:

            await message.answer(

                "✅ <b>VIDEO PUBLISHED</b>\n\n"

                f"🎬 <b>{file_name}</b>\n\n"

                "🖼️ Cover: ⚠️\n"
                "📢 Channel: ✅\n"
                "👉 WATCH NOW: ✅\n"
                "🎥 Mini App: ✅",

                reply_markup=keyboard,

                parse_mode="HTML",

                protect_content=True,

            )

        # =================================================
        # DELETE STATUS
        # =================================================

        try:

            await status_message.delete()

        except Exception:

            pass

    except Exception as error:

        print(
            "=========================================="
        )

        print(
            "VIDEO PROCESS ERROR:"
        )

        print(
            repr(error)
        )

        print(
            "=========================================="
        )

        try:

            if status_message:

                await status_message.edit_text(

                    "❌ <b>VIDEO PROCESS FAILED</b>\n\n"

                    f"<code>{error}</code>\n\n"

                    "Check Railway logs.",

                    parse_mode="HTML"

                )

            else:

                await message.answer(

                    "❌ Video process failed."

                )

        except Exception:

            pass

    finally:

        processing_videos.discard(
            file_id
        )

        if temp_dir:

            cleanup_temp_dir(
                temp_dir
            )


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

            "Aapke paas full control hai.\n\n"

            "🎬 New video add karne ke liye:\n"
            "/addvideo\n\n"

            "👑 Admin Panel:\n"
            "/admin\n\n"

            "📹 Video → Automatic Cover → Channel\n"
            "👉 WATCH NOW → Mini App",

            parse_mode="HTML"

        )

        return

    await send_public_video_library(
        message
    )


# =========================================================
# PUBLIC VIDEO LIBRARY
# =========================================================

async def send_public_video_library(
    message: Message
):

    try:

        found_videos = []

        async for channel_message in (
            mtproto.get_chat_history(

                CHANNEL_ID,

                limit=50

            )
        ):

            video = None

            if channel_message.video:

                video = channel_message.video

            elif channel_message.document:

                document = channel_message.document

                mime = (
                    document.mime_type
                    or ""
                )

                name = (
                    document.file_name
                    or ""
                )

                if (

                    mime.startswith("video/")

                    or name.lower().endswith(
                        VIDEO_EXTENSIONS
                    )

                ):

                    video = document

            if not video:

                continue

            file_id = video.file_id

            file_size = (
                getattr(
                    video,
                    "file_size",
                    0
                )
                or 0
            )

            mime_type = (
                getattr(
                    video,
                    "mime_type",
                    None
                )
                or "video/mp4"
            )

            file_name = (
                getattr(
                    video,
                    "file_name",
                    None
                )
                or "video.mp4"
            )

            found_videos.append({

                "file_id": file_id,

                "file_size": file_size,

                "mime_type": mime_type,

                "file_name": file_name,

                "message_id":
                    channel_message.id,

            })

        if not found_videos:

            await message.answer(

                "🌙 <b>NIGHT HUB</b>\n\n"

                "🎬 Welcome!\n\n"

                "⚠️ <b>Abhi koi video available nahi hai.</b>\n\n"

                "New videos upload hone ke baad "
                "yahan दिखाई देंगी.",

                parse_mode="HTML"

            )

            return

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            f"🎬 <b>{len(found_videos)} videos available</b>\n\n"

            "👇 Video select karke WATCH NOW press karein.",

            parse_mode="HTML"

        )

        for index, item in enumerate(

            found_videos,

            start=1

        ):

            keyboard = watch_keyboard(

                file_id=item["file_id"],

                size_bytes=item["file_size"],

                mime_type=item["mime_type"],

                file_name=item["file_name"],

            )

            size_mb = (

                item["file_size"]
                / (1024 * 1024)

                if item["file_size"]

                else 0

            )

            await message.answer(

                "🎬 <b>VIDEO "
                f"{index}</b>\n\n"

                f"📁 {item['file_name']}\n"

                f"📦 {size_mb:.2f} MB\n\n"

                "👉 <b>WATCH NOW</b>",

                reply_markup=keyboard,

                parse_mode="HTML",

                protect_content=True,

            )

    except Exception as error:

        print(
            "PUBLIC LIBRARY ERROR:",
            repr(error)
        )

        await message.answer(

            "⚠️ Video library temporarily unavailable.\n\n"
            "Please try again later."

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

            "/start - Start\n"
            "/admin - Admin Panel\n"
            "/addvideo - Add Video\n"
            "/cancel - Cancel\n"
            "/help - Help",

            parse_mode="HTML"

        )

    else:

        await send_public_video_library(
            message
        )


# =========================================================
# ADMIN COMMAND
# =========================================================

@dp.message(Command("admin"))
async def admin_cmd(
    message: Message
):

    user_id = message.from_user.id

    if not is_admin(user_id):

        await message.answer(

            "🔒 <b>ACCESS DENIED</b>\n\n"

            "Aapko Admin Panel ka access nahi hai.",

            parse_mode="HTML"

        )

        return

    await message.answer(

        admin_panel_text(),

        reply_markup=admin_panel_keyboard(),

        parse_mode="HTML"

    )


# =========================================================
# ADD VIDEO
# =========================================================

@dp.message(Command("addvideo"))
async def add_video_cmd(
    message: Message
):

    user_id = message.from_user.id

    if not is_admin(user_id):

        await message.answer(

            "🔒 <b>UPLOAD DISABLED</b>\n\n"

            "Sirf Admin video upload kar sakta hai.",

            parse_mode="HTML"

        )

        return

    await message.answer(

        "👑 <b>ADMIN VIDEO UPLOAD MODE</b>\n\n"

        "📹 Ab video bhejo.\n\n"

        "🖼️ Bot video ke andar se "
        "automatic cover frame nikalega.\n\n"

        "📢 Uske baad video private channel "
        "mein publish hogi.\n\n"

        "📦 Aap multiple videos bhi bhej sakte ho.\n\n"

        "❌ Upload rokne ki zarurat nahi hai.",

        parse_mode="HTML"

    )


# =========================================================
# CANCEL
# =========================================================

@dp.message(Command("cancel"))
async def cancel_cmd(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return

    await message.answer(

        "ℹ️ Current video processing ko "
        "force cancel nahi kiya gaya.\n\n"
        "Processing complete hone dein."

    )


# =========================================================
# VIDEO HANDLER
# =========================================================

@dp.message(F.video)
async def video_received(
    message: Message
):

    user_id = message.from_user.id

    if not is_admin(user_id):

        await message.answer(

            "🔒 <b>UPLOAD DISABLED</b>\n\n"

            "Public users video upload nahi kar sakte.\n\n"

            "🎬 Videos dekhne ke liye /start use karein.",

            parse_mode="HTML"

        )

        return

    await process_one_video(
        message
    )


# =========================================================
# DOCUMENT VIDEO HANDLER
# =========================================================

@dp.message(F.document)
async def document_received(
    message: Message
):

    user_id = message.from_user.id

    if not is_admin(user_id):

        await message.answer(

            "🔒 <b>UPLOAD DISABLED</b>\n\n"

            "Public users video upload nahi kar sakte.",

            parse_mode="HTML"

        )

        return

    document = message.document

    mime = (
        document.mime_type
        or ""
    )

    file_name = (
        document.file_name
        or ""
    )

    is_video = (

        mime.startswith("video/")

        or file_name.lower().endswith(
            VIDEO_EXTENSIONS
        )

    )

    if not is_video:

        return

    await process_one_video(
        message
    )


# =========================================================
# ADMIN ADD VIDEO CALLBACK
# =========================================================

@dp.callback_query(
    F.data == "admin_add_video"
)
async def admin_add_video_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return

    await callback.message.edit_text(

        "🎬 <b>ADD VIDEO</b>\n\n"

        "📹 Ab video bhejo.\n\n"

        "🖼️ Cover video ke andar se "
        "automatically niklegi.\n\n"

        "📦 Multiple videos bhej sakte ho.\n\n"

        "📢 Har video private channel mein publish hogi.",

        parse_mode="HTML"

    )

    await callback.answer()


# =========================================================
# ADMIN VIDEOS CALLBACK
# =========================================================

@dp.callback_query(
    F.data == "admin_videos"
)
async def admin_videos_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return

    try:

        count = 0

        async for channel_message in (
            mtproto.get_chat_history(

                CHANNEL_ID,

                limit=100

            )
        ):

            if channel_message.video:

                count += 1

            elif channel_message.document:

                mime = (
                    channel_message.document.mime_type
                    or ""
                )

                if mime.startswith("video/"):

                    count += 1

        keyboard = InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(

                        text="⬅️ BACK",

                        callback_data="admin_back"

                    )

                ]

            ]

        )

        await callback.message.edit_text(

            "📚 <b>VIDEO LIBRARY</b>\n\n"

            f"🎬 Channel videos: <b>{count}</b>\n\n"

            "📢 Private Channel permanent "
            "video library ke roop mein use ho raha hai.",

            reply_markup=keyboard,

            parse_mode="HTML"

        )

    except Exception as error:

        await callback.message.edit_text(

            "❌ Video library error.\n\n"

            f"<code>{error}</code>",

            parse_mode="HTML"

        )

    await callback.answer()


# =========================================================
# ADMIN CHANNEL CALLBACK
# =========================================================

@dp.callback_query(
    F.data == "admin_channel"
)
async def admin_channel_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="⬅️ BACK",

                    callback_data="admin_back"

                )

            ]

        ]

    )

    await callback.message.edit_text(

        "📢 <b>PRIVATE CHANNEL</b>\n\n"

        f"CHANNEL_ID:\n"
        f"<code>{CHANNEL_ID}</code>\n\n"

        "Bot Channel Admin: ✅\n"
        "Video Publishing: ✅\n"
        "Channel Library: ✅",

        reply_markup=keyboard,

        parse_mode="HTML"

    )

    await callback.answer()


# =========================================================
# ADMIN USERS CALLBACK
# =========================================================

@dp.callback_query(
    F.data == "admin_users"
)
async def admin_users_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="⬅️ BACK",

                    callback_data="admin_back"

                )

            ]

        ]

    )

    await callback.message.edit_text(

        "👥 <b>USER ACCESS</b>\n\n"

        "👑 ADMIN\n"
        "✅ Admin Panel\n"
        "✅ Upload Video\n"
        "✅ Automatic Cover\n"
        "✅ Channel Management\n\n"

        "👤 PUBLIC USER\n"
        "❌ Upload Video\n"
        "❌ Admin Panel\n"
        "❌ Channel Management\n"
        "✅ Watch Videos\n"
        "✅ Mini App",

        reply_markup=keyboard,

        parse_mode="HTML"

    )

    await callback.answer()


# =========================================================
# ADMIN REFRESH
# =========================================================

@dp.callback_query(
    F.data == "admin_refresh"
)
async def admin_refresh_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return

    await callback.message.edit_text(

        admin_panel_text(),

        reply_markup=admin_panel_keyboard(),

        parse_mode="HTML"

    )

    await callback.answer(
        "🔄 Refreshed"
    )


# =========================================================
# ADMIN BACK
# =========================================================

@dp.callback_query(
    F.data == "admin_back"
)
async def admin_back_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return

    await callback.message.edit_text(

        admin_panel_text(),

        reply_markup=admin_panel_keyboard(),

        parse_mode="HTML"

    )

    await callback.answer()


# =========================================================
# ADMIN CLOSE
# =========================================================

@dp.callback_query(
    F.data == "admin_close"
)
async def admin_close_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return

    try:

        await callback.message.delete()

    except Exception:

        pass

    await callback.answer(
        "Admin Panel closed."
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
# PLAYER
# =========================================================

async def player(
    request: web.Request
):

    token = request.query.get(
        "token"
    )

    if not token:

        return web.Response(

            text="Missing watch token",

            status=400

        )

    data = watch_tokens.get(
        token
    )

    if not data:

        return web.Response(

            text="Invalid watch token",

            status=403

        )

    file_name = data["name"]

    mime_type = data["mime"]

    video_url = (

        f"{WEB_URL}/stream?"

        f"token={quote(token, safe='')}"

    )

    html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,
initial-scale=1.0,
maximum-scale=1.0">

<meta name="theme-color"
content="#050507">

<title>NIGHT HUB</title>

<script src="https://telegram.org/js/telegram-web-app.js"></script>

<script src="https://sad.adsgram.ai/js/sad.min.js"></script>

<style>

* {{
    box-sizing: border-box;
}}

html, body {{
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

.container {{
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px 12px 30px;
}}

.logo {{
    width: 70px;
    height: 70px;
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
    font-size: 32px;
}}

.title {{
    margin: 12px 0 0;
    font-size: 28px;
    font-weight: 900;
}}

.subtitle {{
    margin-top: 5px;
    color: #9997a7;
    font-size: 13px;
}}

.player-card {{
    width: 100%;
    max-width: 1000px;
    margin-top: 22px;
    padding: 8px;
    border-radius: 22px;
    background:
        rgba(255,255,255,0.06);
    border:
        1px solid
        rgba(255,255,255,0.10);
}}

.video-container {{
    width: 100%;
    background: black;
    border-radius: 16px;
    overflow: hidden;
}}

video {{
    display: block;
    width: 100%;
    max-height: 75vh;
    background: black;
    object-fit: contain;
}}

.status {{
    margin-top: 14px;
    color: #aaa8b5;
    font-size: 13px;
    text-align: center;
}}

.badges {{
    display: flex;
    gap: 8px;
    margin-top: 10px;
    justify-content: center;
    flex-wrap: wrap;
}}

.badge {{
    padding: 7px 12px;
    border-radius: 999px;
    background:
        rgba(139,44,255,0.12);
    border:
        1px solid
        rgba(139,44,255,0.18);
    color: #c2a7ff;
    font-size: 11px;
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
}}

.ad-icon {{
    font-size: 48px;
}}

.ad-title {{
    font-size: 22px;
    font-weight: 800;
    margin-top: 10px;
}}

.ad-status {{
    margin-top: 10px;
    color: #aaa8b5;
}}

.footer {{
    margin-top: auto;
    padding-top: 30px;
    color: #5f5d69;
    font-size: 11px;
}}

</style>

</head>

<body>

<div class="container">

<div class="logo">
🎬
</div>

<h1 class="title">
NIGHT HUB
</h1>

<div class="subtitle">
Premium Online Video
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

Your browser does not support HTML5 video.

</video>

</div>

</div>

<div id="status"
class="status">

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
ONLINE
</div>

</div>

<div class="footer">
NIGHT HUB
</div>

</div>


<div id="adScreen"
class="ad-screen">

<div class="ad-box">

<div class="ad-icon">
📺
</div>

<div class="ad-title">
Advertisement
</div>

<div id="adStatus"
class="ad-status">
Advertisement loading...
</div>

</div>

</div>


<script>

const tg =
window.Telegram?.WebApp;

if (tg) {{

    tg.ready();

    tg.expand();

    try {{

        tg.setHeaderColor("#050507");

        tg.setBackgroundColor("#050507");

    }} catch(e) {{}}

}}


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


let started = false;

let adController = null;


try {{

    if (
        window.Adsgram
        &&
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
            "Ad error:",
            error
        );

        adScreen.style.display =
            "none";

        return true;

    }}

}}


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

        status.textContent =
            "▶️ Tap the video to play";

    }}

}}


document.addEventListener(

    "click",

    function() {{

        if (!started) {{

            startVideo();

        }}

    }},

    {{ once: true }}

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

    value = range_header.replace(
        "bytes=",
        "",
        1
    ).strip()

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

                end = file_size - 1

            else:

                end = int(
                    end_text
                )

                if end >= file_size:

                    end = file_size - 1

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

    token = request.query.get(
        "token"
    )

    if not token:

        return web.Response(
            text="Missing token",
            status=400
        )

    data = watch_tokens.get(
        token
    )

    if not data:

        return web.Response(
            text="Invalid watch token",
            status=403
        )

    file_id = data["file_id"]

    file_size = data["size"]

    mime_type = data["mime"]

    file_name = data["name"]

    if file_size <= 0:

        return web.Response(
            text="Invalid file size",
            status=400
        )

    range_header = request.headers.get(
        "Range"
    )

    requested_range = parse_range(

        range_header,

        file_size

    )

    if request.method == "HEAD":

        headers = {

            "Content-Type":
                mime_type,

            "Content-Length":
                str(file_size),

            "Accept-Ranges":
                "bytes",

            "Content-Disposition":
                f'inline; filename="{file_name}"',

            "Cache-Control":
                "no-cache",

        }

        return web.Response(

            status=200,

            headers=headers

        )

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

    headers = {

        "Content-Type":
            mime_type,

        "Content-Length":
            str(content_length),

        "Accept-Ranges":
            "bytes",

        "Content-Disposition":
            f'inline; filename="{file_name}"',

        "Cache-Control":
            "no-cache",

        "Access-Control-Allow-Origin":
            "*",

        "Access-Control-Allow-Headers":
            "Range",

        "Access-Control-Expose-Headers":
            "Content-Length, Content-Range, Accept-Ranges",

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

    first_chunk = (
        start_byte // CHUNK_SIZE
    )

    inner_offset = (
        start_byte % CHUNK_SIZE
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

    try:

        chunk_number = 0

        async for chunk in mtproto.stream_media(

            file_id,

            offset=first_chunk,

            limit=chunks_needed,

        ):

            if bytes_remaining <= 0:

                break

            if chunk_number == 0:

                if inner_offset:

                    chunk = chunk[
                        inner_offset:
                    ]

            if len(chunk) > bytes_remaining:

                chunk = chunk[
                    :bytes_remaining
                ]

            if not chunk:

                break

            await response.write(
                chunk
            )

            bytes_remaining -= len(
                chunk
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

        raise

    except Exception as error:

        print(
            "STREAM ERROR:",
            repr(error)
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
            2 * 1024 * 1024 * 1024

    )

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
        f"CHANNEL_ID: {CHANNEL_ID}"
    )

    print(
        f"ADMIN_ID: {ADMIN_ID}"
    )

    print(
        "FFMPEG: ENABLED"
    )

    print(
        "AUTO VIDEO COVER: ENABLED"
    )

    print(
        "PYROGRAM MTProto DOWNLOAD: ENABLED"
    )

    print(
        "CHANNEL WATCH BUTTON: ENABLED"
    )

    print(
        "ADMIN PANEL: ENABLED"
    )

    print(
        "MINI APP: ENABLED"
    )

    print(
        "RANGE STREAMING: ENABLED"
    )

    print(
        "=========================================="
    )


# =========================================================
# COMMAND MENU
# =========================================================

async def setup_commands():

    # -----------------------------------------------------
    # PUBLIC USERS
    # -----------------------------------------------------

    await bot.set_my_commands(

        [],

        scope=BotCommandScopeDefault()

    )

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    await bot.set_my_commands(

        [

            BotCommand(

                command="start",

                description="Start NIGHT HUB"

            ),

            BotCommand(

                command="admin",

                description="Open Admin Panel"

            ),

            BotCommand(

                command="addvideo",

                description="Add Video"

            ),

            BotCommand(

                command="cancel",

                description="Cancel"

            ),

            BotCommand(

                command="help",

                description="Admin Help"

            ),

        ],

        scope=BotCommandScopeChat(

            chat_id=ADMIN_ID

        )

    )


# =========================================================
# MAIN
# =========================================================

async def main():

    print(
        "=========================================="
    )

    print(
        "Starting Telegram MTProto..."
    )

    await mtproto.start()

    print(
        "Telegram MTProto started ✅"
    )

    await setup_commands()

    print(
        "Command menus configured ✅"
    )

    await start_web_server()

    print(
        "Starting NIGHT HUB bot..."
    )

    print(
        "=========================================="
    )

    try:

        await dp.start_polling(
            bot
        )

    finally:

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
