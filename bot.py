import os
import re
import json
import time
import html
import asyncio
import shutil
import tempfile
import secrets
from pathlib import Path
from typing import Optional

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
    BotCommand,
)
from aiogram.client.default import DefaultBotProperties

from pyrogram import Client
from pyrogram.types import Message as PyroMessage
import imageio_ffmpeg


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
WEB_URL = os.getenv("WEB_URL", "").strip().rstrip("/")
WATCH_SECRET = os.getenv("WATCH_SECRET", "").strip()

PORT = int(os.getenv("PORT", "8080"))
ADSGRAM_BLOCK_ID = os.getenv("ADSGRAM_BLOCK_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")

if not API_ID:
    raise RuntimeError("API_ID environment variable is missing")

if not API_HASH:
    raise RuntimeError("API_HASH environment variable is missing")

if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID environment variable is missing")

if not CHANNEL_ID:
    raise RuntimeError("CHANNEL_ID environment variable is missing")

if not WATCH_SECRET:
    raise RuntimeError("WATCH_SECRET environment variable is missing")

try:
    API_ID = int(API_ID)
    ADMIN_ID = int(ADMIN_ID)
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError:
    raise RuntimeError(
        "API_ID, ADMIN_ID and CHANNEL_ID must contain valid numbers"
    )


# =========================================================
# PATHS / SETTINGS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMP_DIR = BASE_DIR / "temp"

DATA_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

LIBRARY_FILE = DATA_DIR / "videos.json"

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
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
}

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

PROCESS_LOCK = asyncio.Semaphore(2)

video_library = {}
library_lock = asyncio.Lock()


# =========================================================
# BOT / DISPATCHER
# =========================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ),
)

dp = Dispatcher()


# =========================================================
# PYROGRAM CLIENT
# =========================================================

pyro = Client(
    "night_hub_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir=str(DATA_DIR),
)


# =========================================================
# HELPERS
# =========================================================

def is_admin(user_id: int) -> bool:
    return int(user_id) == ADMIN_ID


def safe_filename(name: str) -> str:
    name = name or "video"
    name = re.sub(r"[^\w\s.\-()\[\]]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] or "video"


def escape(text: str) -> str:
    return html.escape(str(text))


def load_library_sync():
    global video_library

    if not LIBRARY_FILE.exists():
        video_library = {}
        return

    try:
        data = json.loads(
            LIBRARY_FILE.read_text(encoding="utf-8")
        )

        if isinstance(data, dict):
            video_library = data
        else:
            video_library = {}

    except Exception:
        video_library = {}


def save_library_sync():
    tmp = LIBRARY_FILE.with_suffix(".tmp")

    tmp.write_text(
        json.dumps(
            video_library,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    tmp.replace(LIBRARY_FILE)


async def save_library():
    async with library_lock:
        await asyncio.to_thread(save_library_sync)


async def add_library_item(item: dict):
    key = str(item["channel_message_id"])

    async with library_lock:
        video_library[key] = item
        await asyncio.to_thread(save_library_sync)


async def remove_library_item(message_id: int):
    async with library_lock:
        video_library.pop(str(message_id), None)
        await asyncio.to_thread(save_library_sync)


def get_library_items():
    items = list(video_library.values())

    items.sort(
        key=lambda x: int(x.get("created_at", 0)),
        reverse=True,
    )

    return items


def create_watch_url(message_id: int) -> str:
    if not WEB_URL:
        return ""

    token = secrets.token_urlsafe(16)

    return (
        f"{WEB_URL}/watch/"
        f"{int(message_id)}"
        f"?s={WATCH_SECRET}"
        f"&t={token}"
    )


def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Add Video",
                    callback_data="admin_add",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎬 Videos",
                    callback_data="admin_videos",
                ),
                InlineKeyboardButton(
                    text="🔄 Refresh",
                    callback_data="admin_refresh",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Statistics",
                    callback_data="admin_stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Close",
                    callback_data="admin_close",
                ),
            ],
        ]
    )


def video_watch_keyboard(message_id: int):
    url = create_watch_url(message_id)

    buttons = []

    if url:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="▶️ WATCH NOW",
                    web_app={"url": url},
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🎬 More Videos",
                callback_data="show_videos",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def video_list_keyboard():
    items = get_library_items()

    buttons = []

    for item in items[:50]:
        message_id = int(item["channel_message_id"])
        title = item.get("title", "Video")

        if len(title) > 35:
            title = title[:35] + "..."

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎬 {title}",
                    callback_data=f"watch:{message_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


def admin_panel_text() -> str:
    count = len(video_library)

    return (
        "👑 <b>NIGHT HUB ADMIN PANEL</b>\n\n"
        f"🎬 Videos: <b>{count}</b>\n"
        f"📢 Channel: <code>{CHANNEL_ID}</code>\n\n"
        "📤 <b>Add Video</b>\n"
        "Sirf admin video upload kar sakta hai.\n\n"
        "Video bhejo aur bot automatically:\n"
        "• Video download karega\n"
        "• Video se cover nikalega\n"
        "• Private channel me publish karega\n"
        "• WATCH NOW button lagayega\n"
        "• Video library me save karega"
    )


# =========================================================
# FFMPEG COVER EXTRACTION
# =========================================================

async def extract_cover(
    video_path: str,
    cover_path: str,
) -> bool:

    process = None

    try:
        process = await asyncio.create_subprocess_exec(
            FFMPEG_PATH,
            "-y",
            "-ss",
            "00:00:02",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-vf",
            "scale='min(1280,iw)':-2",
            "-q:v",
            "2",
            cover_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr = await process.communicate()

        if process.returncode != 0:
            print(
                "FFmpeg cover error:",
                stderr.decode(
                    "utf-8",
                    errors="ignore",
                )[-2000:],
            )

            return False

        return (
            os.path.exists(cover_path)
            and os.path.getsize(cover_path) > 0
        )

    except Exception as e:
        print("Cover extraction error:", e)
        return False

    finally:
        if process and process.returncode is None:
            try:
                process.kill()
            except Exception:
                pass


# =========================================================
# PYROGRAM DOWNLOAD
# =========================================================

async def download_pyro_video(
    message_id: int,
    destination: str,
) -> str:

    message = await pyro.get_messages(
        "me",
        message_id,
    )

    if not message:
        raise RuntimeError(
            "Temporary Telegram message not found"
        )

    downloaded = await pyro.download_media(
        message,
        file_name=destination,
    )

    if not downloaded:
        raise RuntimeError(
            "Video download failed"
        )

    return downloaded


# =========================================================
# CHANNEL PUBLISH
# =========================================================

async def publish_video(
    video_path: str,
    cover_path: Optional[str],
    title: str,
    original_size: int,
) -> PyroMessage:

    caption = (
        f"<b>{escape(title)}</b>\n\n"
        "🎬 <b>NIGHT HUB</b>\n"
        "▶️ Watch Online"
    )

    thumb = cover_path if cover_path else None

    if thumb and not os.path.exists(thumb):
        thumb = None

    sent = await pyro.send_video(
        chat_id=CHANNEL_ID,
        video=video_path,
        caption=caption,
        thumb=thumb,
        supports_streaming=True,
        parse_mode="html",
    )

    return sent


# =========================================================
# VIDEO PROCESSING
# =========================================================

async def process_video(
    message: Message,
    pyro_message_id: int,
):

    async with PROCESS_LOCK:

        work_dir = Path(
            tempfile.mkdtemp(
                prefix="night_hub_",
                dir=str(TEMP_DIR),
            )
        )

        video_path = work_dir / "video"

        cover_path = work_dir / "cover.jpg"

        try:
            await message.answer(
                "⏳ <b>VIDEO PROCESSING</b>\n\n"
                "📥 Video prepare ho rahi hai...\n"
                "🖼️ Cover video se extract kiya jayega."
            )

            tg_message = await pyro.get_messages(
                "me",
                pyro_message_id,
            )

            if not tg_message:
                raise RuntimeError(
                    "Temporary message unavailable"
                )

            media = (
                tg_message.video
                or tg_message.document
            )

            if not media:
                raise RuntimeError(
                    "Video media not found"
                )

            file_size = getattr(
                media,
                "file_size",
                0,
            ) or 0

            if file_size > MAX_FILE_SIZE:
                raise RuntimeError(
                    "Video size 2 GB se zyada hai."
                )

            await message.edit_text(
                "⏳ <b>VIDEO PROCESSING</b>\n\n"
                "📥 Video download ho rahi hai..."
            )

            downloaded = await pyro.download_media(
                tg_message,
                file_name=str(video_path),
            )

            if not downloaded:
                raise RuntimeError(
                    "Video download failed"
                )

            downloaded_path = Path(downloaded)

            await message.edit_text(
                "🖼️ <b>COVER EXTRACTING</b>\n\n"
                "Video ke andar se cover nikala ja raha hai..."
            )

            cover_ok = await extract_cover(
                str(downloaded_path),
                str(cover_path),
            )

            title = (
                message.video.file_name
                if message.video
                and message.video.file_name
                else None
            )

            if not title:
                title = (
                    message.document.file_name
                    if message.document
                    and message.document.file_name
                    else f"Video {int(time.time())}"
                )

            title = os.path.splitext(title)[0]

            await message.edit_text(
                "📢 <b>CHANNEL PUBLISHING</b>\n\n"
                "Private channel me video publish ho rahi hai..."
            )

            channel_message = await publish_video(
                str(downloaded_path),
                str(cover_path) if cover_ok else None,
                title,
                file_size,
            )

            item = {
                "channel_message_id": int(
                    channel_message.id
                ),
                "channel_id": int(CHANNEL_ID),
                "title": title,
                "size": file_size,
                "created_at": int(time.time()),
                "cover": bool(cover_ok),
            }

            await add_library_item(item)

            await message.edit_text(
                "✅ <b>VIDEO PUBLISHED SUCCESSFULLY</b>\n\n"
                f"🎬 <b>{escape(title)}</b>\n"
                f"🖼️ Cover: {'✅' if cover_ok else '❌'}\n"
                "📢 Channel: ✅\n"
                "🎥 Mini App: ✅\n\n"
                "Video library me save ho gayi hai."
            )

        except Exception as e:

            print(
                "VIDEO PROCESS ERROR:",
                repr(e),
            )

            error_text = escape(
                str(e)
            )[:2500]

            try:
                await message.edit_text(
                    "❌ <b>VIDEO PROCESS FAILED</b>\n\n"
                    f"<code>{error_text}</code>\n\n"
                    "Railway logs check karein."
                )
            except Exception:
                pass

        finally:
            shutil.rmtree(
                work_dir,
                ignore_errors=True,
            )


# =========================================================
# TEMP MESSAGE CREATION
# =========================================================

async def copy_video_to_pyrogram(
    message: Message,
) -> int:

    # Bot API message cannot always be downloaded
    # directly for large files.
    #
    # We copy the media to Saved Messages using the
    # Pyrogram bot account first.

    if message.video:
        sent = await pyro.send_cached_media(
            "me",
            message.video.file_id,
        )

        return int(sent.id)

    if message.document:
        sent = await pyro.send_cached_media(
            "me",
            message.document.file_id,
        )

        return int(sent.id)

    raise RuntimeError(
        "Video media not found"
    )


# =========================================================
# START
# =========================================================

@dp.message(Command("start"))
async def start_handler(
    message: Message,
):

    items = get_library_items()

    if not items:

        await message.answer(
            "🎬 <b>WELCOME TO NIGHT HUB</b>\n\n"
            "Abhi koi video available nahi hai.\n\n"
            "New videos upload hone ke baad "
            "yahan available hongi."
        )

        return

    await message.answer(
        "🎬 <b>WELCOME TO NIGHT HUB</b>\n\n"
        f"📚 <b>{len(items)} videos available</b>\n\n"
        "👇 Video select karein:",
        reply_markup=video_list_keyboard(),
    )


# =========================================================
# SHOW VIDEOS
# =========================================================

@dp.message(Command("videos"))
async def videos_command(
    message: Message,
):

    items = get_library_items()

    if not items:
        await message.answer(
            "❌ Abhi koi video available nahi hai."
        )
        return

    await message.answer(
        f"🎬 <b>{len(items)} VIDEOS AVAILABLE</b>\n\n"
        "👇 Video select karein:",
        reply_markup=video_list_keyboard(),
    )


# =========================================================
# ADMIN
# =========================================================

@dp.message(Command("admin"))
async def admin_handler(
    message: Message,
):

    if not message.from_user:
        return

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "🔒 <b>ACCESS DENIED</b>\n\n"
            "Aapko Admin Panel ka access nahi hai."
        )

        return

    await message.answer(
        admin_panel_text(),
        reply_markup=admin_keyboard(),
    )


# =========================================================
# ADD VIDEO COMMAND
# =========================================================

@dp.message(Command("addvideo"))
async def addvideo_handler(
    message: Message,
):

    if not message.from_user:
        return

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "🔒 <b>UPLOAD DISABLED</b>\n\n"
            "Sirf Admin video upload kar sakta hai."
        )

        return

    await message.answer(
        "📤 <b>ADD VIDEO</b>\n\n"
        "Ab video bhejo.\n\n"
        "Bot automatically:\n"
        "🖼️ Video se cover nikalega\n"
        "📢 Private channel me publish karega\n"
        "▶️ WATCH NOW button lagayega\n"
        "📚 Library me save karega\n\n"
        "Multiple videos bhi ek ke baad ek bhej sakte ho."
    )


# =========================================================
# VIDEO HANDLER
# =========================================================

@dp.message(
    F.video
)
async def video_handler(
    message: Message,
):

    if not message.from_user:
        return

    # PUBLIC USER UPLOAD BLOCK
    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "🔒 <b>UPLOAD DISABLED</b>\n\n"
            "Public users video upload nahi kar sakte.\n\n"
            "🎬 Videos dekhne ke liye /start use karein."
        )

        return

    if message.video.file_size:
        if message.video.file_size > MAX_FILE_SIZE:

            await message.answer(
                "❌ <b>VIDEO TOO LARGE</b>\n\n"
                "Maximum allowed size: 2 GB."
            )

            return

    status = await message.answer(
        "⏳ <b>VIDEO RECEIVED</b>\n\n"
        "Video processing start ho rahi hai..."
    )

    try:

        # Pyrogram Saved Messages copy
        pyro_message_id = await copy_video_to_pyrogram(
            message
        )

        await process_video(
            status,
            pyro_message_id,
        )

    except Exception as e:

        print(
            "VIDEO HANDLER ERROR:",
            repr(e),
        )

        await status.edit_text(
            "❌ <b>VIDEO PROCESS FAILED</b>\n\n"
            f"<code>{escape(str(e))[:2500]}</code>"
        )


# =========================================================
# DOCUMENT VIDEO HANDLER
# =========================================================

@dp.message(
    F.document
)
async def document_handler(
    message: Message,
):

    if not message.from_user:
        return

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "🔒 <b>UPLOAD DISABLED</b>\n\n"
            "Public users video upload nahi kar sakte."
        )

        return

    filename = (
        message.document.file_name
        or ""
    )

    extension = Path(
        filename
    ).suffix.lower()

    if extension not in VIDEO_EXTENSIONS:

        await message.answer(
            "❌ Ye video file nahi lag rahi.\n\n"
            "MP4, MKV, WEBM, MOV, AVI etc. supported hain."
        )

        return

    if (
        message.document.file_size
        and message.document.file_size > MAX_FILE_SIZE
    ):

        await message.answer(
            "❌ <b>VIDEO TOO LARGE</b>\n\n"
            "Maximum allowed size: 2 GB."
        )

        return

    status = await message.answer(
        "⏳ <b>VIDEO RECEIVED</b>\n\n"
        "Processing start ho rahi hai..."
    )

    try:

        pyro_message_id = await copy_video_to_pyrogram(
            message
        )

        await process_video(
            status,
            pyro_message_id,
        )

    except Exception as e:

        print(
            "DOCUMENT VIDEO ERROR:",
            repr(e),
        )

        await status.edit_text(
            "❌ <b>VIDEO PROCESS FAILED</b>\n\n"
            f"<code>{escape(str(e))[:2500]}</code>"
        )


# =========================================================
# ADMIN CALLBACKS
# =========================================================

@dp.callback_query(
    F.data == "admin_add"
)
async def admin_add_callback(
    callback: CallbackQuery,
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "📤 <b>ADD VIDEO</b>\n\n"
        "Ab video bhejo.\n\n"
        "Multiple videos ek ke baad ek bhej sakte ho."
    )

    await callback.answer()


@dp.callback_query(
    F.data == "admin_videos"
)
async def admin_videos_callback(
    callback: CallbackQuery,
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied",
            show_alert=True,
        )
        return

    items = get_library_items()

    if not items:

        await callback.message.answer(
            "📭 Video library empty hai."
        )

        await callback.answer()
        return

    text = (
        "🎬 <b>NIGHT HUB VIDEOS</b>\n\n"
        f"Total: <b>{len(items)}</b>\n\n"
    )

    for index, item in enumerate(
        items[:30],
        start=1,
    ):

        text += (
            f"{index}. "
            f"<b>{escape(item.get('title', 'Video'))}</b>\n"
            f"   Message ID: <code>"
            f"{item['channel_message_id']}</code>\n\n"
        )

    await callback.message.answer(
        text
    )

    await callback.answer()


@dp.callback_query(
    F.data == "admin_stats"
)
async def admin_stats_callback(
    callback: CallbackQuery,
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied",
            show_alert=True,
        )
        return

    items = get_library_items()

    total_size = sum(
        int(x.get("size", 0) or 0)
        for x in items
    )

    total_gb = (
        total_size /
        (1024 ** 3)
    )

    await callback.message.answer(
        "📊 <b>NIGHT HUB STATISTICS</b>\n\n"
        f"🎬 Videos: <b>{len(items)}</b>\n"
        f"💾 Total size: <b>{total_gb:.2f} GB</b>\n"
        f"📢 Channel ID: <code>{CHANNEL_ID}</code>"
    )

    await callback.answer()


@dp.callback_query(
    F.data == "admin_refresh"
)
async def admin_refresh_callback(
    callback: CallbackQuery,
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        admin_panel_text(),
        reply_markup=admin_keyboard(),
    )

    await callback.answer(
        "🔄 Refreshed"
    )


@dp.callback_query(
    F.data == "admin_close"
)
async def admin_close_callback(
    callback: CallbackQuery,
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied",
            show_alert=True,
        )
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.answer()


# =========================================================
# SHOW VIDEOS CALLBACK
# =========================================================

@dp.callback_query(
    F.data == "show_videos"
)
async def show_videos_callback(
    callback: CallbackQuery,
):

    items = get_library_items()

    if not items:

        await callback.answer(
            "No videos available",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        f"🎬 <b>{len(items)} VIDEOS AVAILABLE</b>\n\n"
        "👇 Select a video:",
        reply_markup=video_list_keyboard(),
    )

    await callback.answer()


# =========================================================
# WATCH CALLBACK
# =========================================================

@dp.callback_query(
    F.data.startswith("watch:")
)
async def watch_callback(
    callback: CallbackQuery,
):

    try:
        message_id = int(
            callback.data.split(
                ":",
                1,
            )[1]
        )

    except Exception:

        await callback.answer(
            "Invalid video",
            show_alert=True,
        )
        return

    item = video_library.get(
        str(message_id)
    )

    if not item:

        await callback.answer(
            "Video unavailable",
            show_alert=True,
        )
        return

    title = item.get(
        "title",
        "Video",
    )

    url = create_watch_url(
        message_id
    )

    if not url:

        await callback.answer(
            "WEB_URL is not configured",
            show_alert=True,
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️ WATCH NOW",
                    web_app={
                        "url": url
                    },
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎬 More Videos",
                    callback_data="show_videos",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        f"🎬 <b>{escape(title)}</b>\n\n"
        "▶️ WATCH NOW button press karke "
        "Mini App me video play karein.",
        reply_markup=keyboard,
    )

    await callback.answer()


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_handler(
    message: Message,
):

    if message.from_user and is_admin(
        message.from_user.id
    ):

        await message.answer(
            "👑 <b>NIGHT HUB ADMIN HELP</b>\n\n"
            "/admin - Admin Panel\n"
            "/addvideo - Add Video\n"
            "/videos - Video Library\n"
            "/start - Main Menu\n"
            "/help - Help"
        )

    else:

        await message.answer(
            "🎬 <b>NIGHT HUB</b>\n\n"
            "/start - Videos\n"
            "/videos - Video Library"
        )


# =========================================================
# OTHER TEXT MESSAGES
# =========================================================

@dp.message(
    F.text
)
async def text_handler(
    message: Message,
):

    if not message.from_user:
        return

    if is_admin(
        message.from_user.id
    ):

        await message.answer(
            "👑 <b>NIGHT HUB ADMIN</b>\n\n"
            "Video upload karne ke liye video bhejo.\n\n"
            "Admin Panel ke liye /admin use karo."
        )

    else:

        await message.answer(
            "🎬 <b>NIGHT HUB</b>\n\n"
            "Videos dekhne ke liye /start press karein."
        )


# =========================================================
# MINI APP HTML
# =========================================================

MINI_APP_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta
    name="viewport"
    content="width=device-width,
             initial-scale=1.0,
             maximum-scale=1.0,
             user-scalable=no"
>
<title>NIGHT HUB</title>

<style>

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    background: #000;
    color: #fff;
    font-family: Arial, sans-serif;
}

body {
    overflow: hidden;
}

#app {
    width: 100%;
    height: 100%;
    background:
        radial-gradient(
            circle at top,
            #252525 0%,
            #080808 45%,
            #000 100%
        );
}

.header {
    height: 60px;
    display: flex;
    align-items: center;
    padding: 0 16px;
    border-bottom: 1px solid #242424;
}

.logo {
    font-size: 20px;
    font-weight: 900;
    letter-spacing: 2px;
}

.player-area {
    width: 100%;
    height: calc(100% - 60px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 10px;
}

video {
    width: 100%;
    max-height: 100%;
    border-radius: 12px;
    background: #000;
    box-shadow:
        0 10px 40px rgba(0,0,0,.7);
}

.loading {
    text-align: center;
    opacity: .8;
}

.error {
    text-align: center;
    color: #ff6666;
    padding: 25px;
}

</style>
</head>

<body>

<div id="app">

    <div class="header">
        <div class="logo">
            NIGHT HUB
        </div>
    </div>

    <div class="player-area">

        <div id="loading"
             class="loading">
            Loading video...
        </div>

        <div id="error"
             class="error"
             style="display:none">
        </div>

        <video
            id="player"
            controls
            playsinline
            preload="metadata"
            style="display:none">
        </video>

    </div>

</div>

<script>

const player =
    document.getElementById("player");

const loading =
    document.getElementById("loading");

const errorBox =
    document.getElementById("error");

const path =
    window.location.pathname;

const parts =
    path.split("/");

const messageId =
    parts[parts.length - 1];

if (!messageId ||
    isNaN(Number(messageId))) {

    loading.style.display = "none";

    errorBox.style.display = "block";

    errorBox.innerText =
        "Invalid video.";

} else {

    const streamUrl =
        "/stream/" +
        encodeURIComponent(messageId) +
        window.location.search;

    player.src = streamUrl;

    player.style.display = "block";

    loading.style.display = "none";

    player.addEventListener(
        "error",
        function() {

            errorBox.style.display =
                "block";

            errorBox.innerText =
                "Video load failed.";
        }
    );
}

</script>

</body>
</html>
"""


# =========================================================
# WEB SERVER
# =========================================================

async def mini_app_handler(
    request: web.Request,
):

    return web.Response(
        text=MINI_APP_HTML,
        content_type="text/html",
    )


async def stream_handler(
    request: web.Request,
):

    message_id_text = request.match_info.get(
        "message_id"
    )

    secret = request.query.get(
        "s",
        "",
    )

    if secret != WATCH_SECRET:

        return web.Response(
            status=403,
            text="Forbidden",
        )

    try:
        message_id = int(
            message_id_text
        )

    except Exception:

        return web.Response(
            status=400,
            text="Invalid message ID",
        )

    item = video_library.get(
        str(message_id)
    )

    if not item:

        return web.Response(
            status=404,
            text="Video not found",
        )

    try:

        channel_message = await pyro.get_messages(
            CHANNEL_ID,
            message_id,
        )

    except Exception as e:

        print(
            "Channel message error:",
            repr(e),
        )

        return web.Response(
            status=500,
            text="Telegram message unavailable",
        )

    if not channel_message:

        return web.Response(
            status=404,
            text="Telegram message not found",
        )

    media = (
        channel_message.video
        or channel_message.document
    )

    if not media:

        return web.Response(
            status=404,
            text="Video media not found",
        )

    file_size = int(
        getattr(
            media,
            "file_size",
            0,
        )
        or 0
    )

    mime_type = (
        getattr(
            media,
            "mime_type",
            None,
        )
        or "video/mp4"
    )

    range_header = request.headers.get(
        "Range"
    )

    start = 0
    end = file_size - 1

    if range_header:

        match = re.match(
            r"bytes=(\d*)-(\d*)",
            range_header,
        )

        if match:

            if match.group(1):
                start = int(
                    match.group(1)
                )

            if match.group(2):
                end = int(
                    match.group(2)
                )

            if not match.group(2):
                end = file_size - 1

            if start >= file_size:

                return web.Response(
                    status=416,
                    headers={
                        "Content-Range":
                            f"bytes */{file_size}"
                    },
                )

            end = min(
                end,
                file_size - 1,
            )

    content_length = (
        end - start + 1
    )

    response = web.StreamResponse(
        status=206
        if range_header
        else 200,
        headers={
            "Content-Type": mime_type,
            "Accept-Ranges": "bytes",
            "Content-Length": str(
                content_length
            ),
            "Cache-Control":
                "public, max-age=3600",
        },
    )

    if range_header:

        response.headers[
            "Content-Range"
        ] = (
            f"bytes {start}-{end}/{file_size}"
        )

    await response.prepare(
        request
    )

    # Telegram media streaming works in chunks.
    # We use approximately 1 MB chunks.

    chunk_size = 1024 * 1024

    first_chunk = start // chunk_size

    skip_inside_chunk = (
        start % chunk_size
    )

    remaining = content_length

    try:

        async for chunk in pyro.stream_media(
            channel_message,
            offset=first_chunk,
        ):

            if not chunk:
                continue

            if skip_inside_chunk:

                if len(chunk) <= skip_inside_chunk:

                    skip_inside_chunk -= len(chunk)

                    continue

                chunk = chunk[
                    skip_inside_chunk:
                ]

                skip_inside_chunk = 0

            if len(chunk) > remaining:

                chunk = chunk[
                    :remaining
                ]

            await response.write(
                chunk
            )

            remaining -= len(chunk)

            if remaining <= 0:
                break

    except asyncio.CancelledError:

        raise

    except Exception as e:

        print(
            "STREAM ERROR:",
            repr(e),
        )

    finally:

        try:
            await response.write_eof()
        except Exception:
            pass

    return response


async def health_handler(
    request: web.Request,
):

    return web.json_response(
        {
            "status": "ok",
            "service": "NIGHT HUB",
            "videos": len(video_library),
        }
    )


# =========================================================
# WEB APP
# =========================================================

web_app = web.Application()

web_app.router.add_get(
    "/",
    health_handler,
)

web_app.router.add_get(
    "/health",
    health_handler,
)

web_app.router.add_get(
    "/watch/{message_id}",
    mini_app_handler,
)

web_app.router.add_get(
    "/stream/{message_id}",
    stream_handler,
)


# =========================================================
# WEB RUNNER
# =========================================================

web_runner = None


async def start_web_server():

    global web_runner

    web_runner = web.AppRunner(
        web_app
    )

    await web_runner.setup()

    site = web.TCPSite(
        web_runner,
        "0.0.0.0",
        PORT,
    )

    await site.start()

    print(
        f"Web server running on port {PORT}"
    )


async def stop_web_server():

    global web_runner

    if web_runner:

        await web_runner.cleanup()

        web_runner = None


# =========================================================
# BOT COMMANDS
# =========================================================

async def setup_commands():

    commands = [
        BotCommand(
            command="start",
            description="Open NIGHT HUB",
        ),
        BotCommand(
            command="videos",
            description="View videos",
        ),
        BotCommand(
            command="help",
            description="Help",
        ),
    ]

    # Admin command also visible to admin.
    # Telegram command visibility is not per-user
    # through BotCommand, so /admin remains available
    # by typing for admin.

    await bot.set_my_commands(
        commands
    )


# =========================================================
# CHANNEL LIBRARY RESTORE
# =========================================================

async def restore_channel_library():

    """
    Persistent JSON library is loaded first.

    Then recent channel messages are scanned so that
    videos can be restored after a Railway restart.
    """

    try:

        async for msg in pyro.get_chat_history(
            CHANNEL_ID,
            limit=100,
        ):

            if not msg:
                continue

            media = (
                msg.video
                or (
                    msg.document
                    if msg.document
                    and (
                        msg.document.mime_type
                        or ""
                    ).startswith("video/")
                    else None
                )
            )

            if not media:
                continue

            message_id = int(
                msg.id
            )

            if str(message_id) in video_library:
                continue

            title = "Video"

            if msg.video:

                title = (
                    msg.video.file_name
                    or f"Video {message_id}"
                )

            elif msg.document:

                title = (
                    msg.document.file_name
                    or f"Video {message_id}"
                )

            title = os.path.splitext(
                title
            )[0]

            video_library[
                str(message_id)
            ] = {
                "channel_message_id":
                    message_id,

                "channel_id":
                    int(CHANNEL_ID),

                "title":
                    title,

                "size":
                    int(
                        getattr(
                            media,
                            "file_size",
                            0,
                        )
                        or 0
                    ),

                "created_at":
                    int(
                        msg.date.timestamp()
                    )
                    if msg.date
                    else int(time.time()),

                "cover":
                    bool(
                        msg.video
                        and msg.video.thumbs
                    ),
            }

        await save_library()

        print(
            "Channel library restored:",
            len(video_library),
        )

    except Exception as e:

        print(
            "CHANNEL RESTORE ERROR:",
            repr(e),
        )


# =========================================================
# STARTUP
# =========================================================

async def startup():

    print(
        "======================================"
    )

    print(
        "        NIGHT HUB STARTING"
    )

    print(
        "======================================"
    )

    load_library_sync()

    print(
        "Local library:",
        len(video_library),
    )

    await pyro.start()

    print(
        "Pyrogram started"
    )

    await restore_channel_library()

    await setup_commands()

    await start_web_server()

    print(
        "NIGHT HUB is READY"
    )


# =========================================================
# SHUTDOWN
# =========================================================

async def shutdown():

    print(
        "NIGHT HUB shutting down..."
    )

    await stop_web_server()

    try:
        await pyro.stop()
    except Exception:
        pass

    try:
        await bot.session.close()
    except Exception:
        pass


# =========================================================
# MAIN
# =========================================================

async def main():

    await startup()

    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )

    finally:

        await shutdown()


if __name__ == "__main__":

    try:
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "Stopped by user"
        )
