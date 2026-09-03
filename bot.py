import os
import asyncio
import json
import secrets
import tempfile
from pathlib import Path
from urllib.parse import quote

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, WebAppInfo, FSInputFile,
    BotCommand, BotCommandScopeChat, BotCommandScopeDefault
)
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup as PyroMarkup
from pyrogram.types import InlineKeyboardButton as PyroButton
import imageio_ffmpeg


# =========================================================
# ENVIRONMENT
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")
WEB_URL = os.getenv("WEB_URL")
WATCH_SECRET = os.getenv("WATCH_SECRET")

PORT = int(os.getenv("PORT", "8080"))
ADSGRAM_BLOCK_ID = os.getenv("ADSGRAM_BLOCK_ID", "")

required = {
    "BOT_TOKEN": BOT_TOKEN,
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "ADMIN_ID": ADMIN_ID,
    "CHANNEL_ID": CHANNEL_ID,
    "WATCH_SECRET": WATCH_SECRET,
}

for key, value in required.items():
    if not value:
        raise RuntimeError(f"{key} environment variable is missing")

try:
    API_ID = int(API_ID)
    ADMIN_ID = int(ADMIN_ID)
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError as e:
    raise RuntimeError("API_ID, ADMIN_ID and CHANNEL_ID must be numeric") from e


if not WEB_URL:
    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    WEB_URL = f"https://{domain}" if domain else f"http://localhost:{PORT}"

WEB_URL = WEB_URL.rstrip("/")


# =========================================================
# BOT / PYROGRAM
# =========================================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

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

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024

VIDEO_EXTENSIONS = (
    ".mp4", ".mkv", ".webm", ".mov", ".m4v",
    ".avi", ".mpeg", ".mpg", ".3gp", ".ts", ".flv"
)

DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp/night_hub_data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

LIBRARY_FILE = DATA_DIR / "video_library.json"

watch_tokens = {}
processing = set()


# =========================================================
# LIBRARY
# =========================================================

def load_library():
    if not LIBRARY_FILE.exists():
        return {}

    try:
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print("LIBRARY LOAD ERROR:", repr(e))
        return {}


video_library = load_library()


def save_library():
    tmp = LIBRARY_FILE.with_suffix(".tmp")

    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(video_library, f, ensure_ascii=False, indent=2)

        os.replace(tmp, LIBRARY_FILE)

    except Exception as e:
        print("LIBRARY SAVE ERROR:", repr(e))


# =========================================================
# ADMIN
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


# =========================================================
# WATCH TOKEN
# =========================================================

def make_watch_url(file_id, size, mime, name):
    token = secrets.token_urlsafe(32)

    watch_tokens[token] = {
        "file_id": file_id,
        "size": int(size or 0),
        "mime": mime or "video/mp4",
        "name": name or "video.mp4",
    }

    return f"{WEB_URL}/watch?token={quote(token, safe='')}"


def watch_keyboard(file_id, size, mime, name):
    url = make_watch_url(file_id, size, mime, name)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👉 𝐖𝐀𝐓𝐂𝐇 𝐍𝐎𝐖 👈",
                    web_app=WebAppInfo(url=url)
                )
            ]
        ]
    )


def channel_keyboard(url):
    return PyroMarkup(
        [
            [
                PyroButton(
                    "👉 𝐖𝐀𝐓𝐂𝐇 𝐍𝐎𝐖 👈",
                    url=url
                )
            ]
        ]
    )


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎬 ADD VIDEO",
                    callback_data="admin_add_video"
                ),
                InlineKeyboardButton(
                    text="📚 VIDEOS",
                    callback_data="admin_videos"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 CHANNEL",
                    callback_data="admin_channel"
                ),
                InlineKeyboardButton(
                    text="👥 USERS",
                    callback_data="admin_users"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 REFRESH",
                    callback_data="admin_refresh"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ CLOSE",
                    callback_data="admin_close"
                )
            ]
        ]
    )


def admin_text():
    return (
        "👑 <b>NIGHT HUB ADMIN PANEL</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎬 Video Management\n"
        "📢 Private Channel\n"
        "👥 User Access\n"
        "🎥 Mini App\n"
        "🖼️ Automatic Cover\n"
        "⚡ Fast Publishing\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 Select an option:"
    )


# =========================================================
# COVER
# =========================================================

async def extract_cover(video_path, output_path):
    commands = [
        [
            FFMPEG,
            "-y",
            "-ss",
            "00:00:02",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            output_path
        ],
        [
            FFMPEG,
            "-y",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            output_path
        ]
    ]

    for cmd in commands:
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await process.communicate()

            if (
                process.returncode == 0
                and os.path.exists(output_path)
                and os.path.getsize(output_path) > 0
            ):
                return True

        except Exception as e:
            print("FFMPEG ERROR:", repr(e))

        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception:
            pass

    return False


# =========================================================
# TEMP DOWNLOAD
# =========================================================

async def download_video(file_id, file_name):
    temp_dir = tempfile.mkdtemp(prefix="night_hub_")

    safe_name = Path(file_name).name or "video.mp4"
    path = os.path.join(temp_dir, safe_name)

    try:
        downloaded = await mtproto.download_media(
            file_id,
            file_name=path
        )

        if downloaded:
            path = downloaded

        if not os.path.exists(path):
            raise RuntimeError("Video download failed")

        return temp_dir, path

    except Exception:
        cleanup(temp_dir)
        raise


def cleanup(folder):
    try:
        if not os.path.isdir(folder):
            return

        for name in os.listdir(folder):
            path = os.path.join(folder, name)

            try:
                if os.path.isfile(path):
                    os.remove(path)
            except Exception:
                pass

        try:
            os.rmdir(folder)
        except Exception:
            pass

    except Exception:
        pass


# =========================================================
# CHANNEL UPLOAD
# =========================================================

async def publish_video(
    video_path,
    size,
    mime,
    name,
    cover_path=None,
    document=False
):
    if not os.path.exists(video_path):
        raise RuntimeError("Local video file missing")

    caption = (
        "🌙 <b>NIGHT HUB</b>\n\n"
        f"🎬 <b>{name}</b>\n\n"
        "👉 Watch this video below."
    )

    thumb = (
        cover_path
        if cover_path and os.path.exists(cover_path)
        else None
    )

    try:
        # IMPORTANT:
        # Aiogram Bot API file_id is NOT sent to Pyrogram.
        # Local downloaded file is uploaded instead.

        if document:
            sent = await mtproto.send_document(
                chat_id=CHANNEL_ID,
                document=video_path,
                thumb=thumb,
                caption=caption,
                parse_mode="html",
                protect_content=True
            )
        else:
            sent = await mtproto.send_video(
                chat_id=CHANNEL_ID,
                video=video_path,
                thumb=thumb,
                caption=caption,
                parse_mode="html",
                supports_streaming=True,
                protect_content=True
            )

        media = sent.video or sent.document

        if not media or not media.file_id:
            raise RuntimeError(
                "Pyrogram file_id was not returned"
            )

        stream_file_id = media.file_id

        watch_url = make_watch_url(
            stream_file_id,
            size,
            mime,
            name
        )

        try:
            await mtproto.edit_message_reply_markup(
                CHANNEL_ID,
                sent.id,
                reply_markup=channel_keyboard(watch_url)
            )
        except Exception as e:
            print("BUTTON ERROR:", repr(e))

        return sent, stream_file_id

    except Exception as e:
        print("CHANNEL UPLOAD ERROR:", repr(e))
        raise RuntimeError(
            f"Channel upload failed: {e}"
        ) from e


# =========================================================
# PROCESS VIDEO
# =========================================================

async def process_video(message: Message):
    if not is_admin(message.from_user.id):
        return

    file_id = None
    size = 0
    mime = "video/mp4"
    name = "video.mp4"
    document = False

    if message.video:
        video = message.video

        file_id = video.file_id
        size = video.file_size or 0
        mime = video.mime_type or "video/mp4"
        name = video.file_name or "video.mp4"

    elif message.document:
        doc = message.document

        file_id = doc.file_id
        size = doc.file_size or 0
        mime = doc.mime_type or ""
        name = doc.file_name or "video.mp4"
        document = True

        if not (
            mime.startswith("video/")
            or name.lower().endswith(VIDEO_EXTENSIONS)
        ):
            return

    else:
        return

    if size > MAX_FILE_SIZE:
        await message.answer(
            "❌ Video 2 GB se badi hai."
        )
        return

    if file_id in processing:
        return

    processing.add(file_id)

    temp_dir = None
    cover = None
    status = None

    try:
        status = await message.answer(
            "🎬 <b>VIDEO RECEIVED</b>\n\n"
            f"📁 <b>{name}</b>\n"
            f"📦 {size / 1024 / 1024:.2f} MB\n\n"
            "🖼️ Cover prepare ho rahi hai...\n\n"
            "⏳ Please wait...",
            parse_mode="HTML"
        )

        temp_dir, video_path = await download_video(
            file_id,
            name
        )

        cover = os.path.join(
            temp_dir,
            "cover.jpg"
        )

        cover_ok = await extract_cover(
            video_path,
            cover
        )

        if not cover_ok:
            cover = None

        await status.edit_text(
            "📢 <b>VIDEO PUBLISHING...</b>\n\n"
            "⚡ Please wait...",
            parse_mode="HTML"
        )

        channel_message, stream_file_id = await publish_video(
            video_path=video_path,
            size=size,
            mime=mime,
            name=name,
            cover_path=cover,
            document=document
        )

        message_id = channel_message.id

        video_library[str(message_id)] = {
            "file_id": stream_file_id,
            "size": size,
            "mime": mime,
            "name": name,
            "message_id": message_id
        }

        save_library()

        watch_url = make_watch_url(
            stream_file_id,
            size,
            mime,
            name
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👉 𝐖𝐀𝐓𝐂𝐇 𝐍𝐎𝐖 👈",
                        web_app=WebAppInfo(
                            url=watch_url
                        )
                    )
                ]
            ]
        )

        if cover and os.path.exists(cover):
            try:
                await message.answer_photo(
                    photo=FSInputFile(cover),
                    caption=(
                        "✅ <b>VIDEO PUBLISHED</b>\n\n"
                        f"🎬 <b>{name}</b>\n\n"
                        "🖼️ Cover: ✅\n"
                        "📢 Channel: ✅\n"
                        "👉 WATCH NOW: ✅\n"
                        "🎥 Mini App: ✅"
                    ),
                    reply_markup=keyboard,
                    parse_mode="HTML",
                    protect_content=True
                )
            except Exception:
                await message.answer(
                    "✅ <b>VIDEO PUBLISHED</b>\n\n"
                    f"🎬 <b>{name}</b>\n\n"
                    "🖼️ Cover: ✅\n"
                    "📢 Channel: ✅\n"
                    "👉 WATCH NOW: ✅\n"
                    "🎥 Mini App: ✅",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        else:
            await message.answer(
                "✅ <b>VIDEO PUBLISHED</b>\n\n"
                f"🎬 <b>{name}</b>\n\n"
                "🖼️ Cover: ⚠️\n"
                "📢 Channel: ✅\n"
                "👉 WATCH NOW: ✅\n"
                "🎥 Mini App: ✅",
                reply_markup=keyboard,
                parse_mode="HTML"
            )

        try:
            await status.delete()
        except Exception:
            pass

    except Exception as e:
        print("VIDEO PROCESS ERROR:", repr(e))

        try:
            text = (
                "❌ <b>VIDEO PROCESS FAILED</b>\n\n"
                f"<code>{str(e)[:3000]}</code>"
            )

            if status:
                await status.edit_text(
                    text,
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    text,
                    parse_mode="HTML"
                )

        except Exception:
            pass

    finally:
        processing.discard(file_id)

        if temp_dir:
            cleanup(temp_dir)


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):
    if is_admin(message.from_user.id):
        await message.answer(
            "🌙 <b>NIGHT HUB</b>\n\n"
            "👑 <b>ADMIN MODE</b>\n\n"
            "🎬 Add Video:\n"
            "/addvideo\n\n"
            "👑 Admin Panel:\n"
            "/admin\n\n"
            "📹 Video → Cover → Channel\n"
            "👉 WATCH NOW → Mini App",
            parse_mode="HTML"
        )
        return

    await send_public_library(message)


# =========================================================
# PUBLIC LIBRARY
# =========================================================

async def send_public_library(message: Message):
    if not video_library:
        await message.answer(
            "🎬 <b>WELCOME TO NIGHT HUB</b>\n\n"
            "Abhi koi video available nahi hai.\n\n"
            "New videos upload hone ke baad yahan available hongi.",
            parse_mode="HTML"
        )
        return

    items = sorted(
        video_library.values(),
        key=lambda x: int(x.get("message_id", 0)),
        reverse=True
    )

    await message.answer(
        "🎬 <b>NIGHT HUB</b>\n\n"
        f"Available videos: <b>{len(items)}</b>\n\n"
        "👇 Watch Now press karein.",
        parse_mode="HTML"
    )

    for i, item in enumerate(items, 1):
        size_mb = item["size"] / 1024 / 1024

        await message.answer(
            f"🎬 <b>VIDEO {i}</b>\n\n"
            f"📁 {item['name']}\n"
            f"📦 {size_mb:.2f} MB\n\n"
            "👉 <b>WATCH NOW</b>",
            reply_markup=watch_keyboard(
                item["file_id"],
                item["size"],
                item["mime"],
                item["name"]
            ),
            parse_mode="HTML",
            protect_content=True
        )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_command(message: Message):
    if is_admin(message.from_user.id):
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
        await send_public_library(message)


# =========================================================
# ADMIN
# =========================================================

@dp.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(
            "🔒 <b>ACCESS DENIED</b>",
            parse_mode="HTML"
        )
        return

    await message.answer(
        admin_text(),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# ADD VIDEO
# =========================================================

@dp.message(Command("addvideo"))
async def addvideo_command(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "📥 <b>ADD VIDEO</b>\n\n"
        "Ab video bhejo.\n\n"
        "🖼️ Automatic cover generate hogi.\n"
        "📢 Channel mein publish hogi.\n"
        "👉 WATCH NOW button lagega.",
        parse_mode="HTML"
    )


# =========================================================
# VIDEO HANDLERS
# =========================================================

@dp.message(F.video)
async def video_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(
            "🔒 Upload sirf Admin ke liye hai."
        )
        return

    await process_video(message)


@dp.message(F.document)
async def document_handler(message: Message):
    if not is_admin(message.from_user.id):
        return

    doc = message.document

    mime = doc.mime_type or ""
    name = doc.file_name or ""

    if not (
        mime.startswith("video/")
        or name.lower().endswith(VIDEO_EXTENSIONS)
    ):
        return

    await process_video(message)


# =========================================================
# ADMIN CALLBACKS
# =========================================================

@dp.callback_query(F.data == "admin_add_video")
async def add_video_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "🎬 <b>ADD VIDEO</b>\n\n"
        "Ab video bhejo.\n\n"
        "🖼️ Automatic cover generate hogi.\n"
        "📢 Private channel mein publish hogi.",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "admin_videos")
async def videos_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )
        return

    count = len(video_library)

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
        f"🎬 Videos: <b>{count}</b>\n\n"
        "✅ Persistent Library\n"
        "✅ Automatic Cover\n"
        "✅ Mini App\n"
        "✅ Channel Publishing",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "admin_channel")
async def channel_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
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
        f"CHANNEL_ID:\n<code>{CHANNEL_ID}</code>\n\n"
        "Bot Channel Access: ✅\n"
        "Video Publishing: ✅\n"
        "WATCH NOW: ✅\n"
        "Mini App: ✅",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "admin_users")
async def users_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
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
        "✅ Channel Management\n\n"
        "👤 PUBLIC USER\n"
        "❌ Upload\n"
        "❌ Admin Panel\n"
        "✅ Watch Videos\n"
        "✅ Mini App",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "admin_refresh")
async def refresh_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        admin_text(),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer("🔄 Refreshed")


@dp.callback_query(F.data == "admin_back")
async def back_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        admin_text(),
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "admin_close")
async def close_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.answer("Admin Panel closed.")


# =========================================================
# RANGE PARSER
# =========================================================

def parse_range(header, size):
    if not header or not header.startswith("bytes="):
        return None

    value = header[6:].split(",", 1)[0]

    parts = value.split("-", 1)

    if len(parts) != 2:
        return None

    start_text, end_text = parts

    try:
        if start_text == "":
            length = int(end_text)

            if length <= 0:
                return None

            length = min(length, size)

            return size - length, size - 1

        start = int(start_text)

        if start < 0 or start >= size:
            return None

        if end_text == "":
            end = size - 1
        else:
            end = min(int(end_text), size - 1)

        if end < start:
            return None

        return start, end

    except ValueError:
        return None


# =========================================================
# STREAM
# =========================================================

async def stream_video(request: web.Request):
    token = request.query.get("token")

    if not token:
        return web.Response(
            text="Missing token",
            status=400
        )

    data = watch_tokens.get(token)

    if not data:
        return web.Response(
            text="Invalid token",
            status=403
        )

    file_id = data["file_id"]
    size = data["size"]
    mime = data["mime"]
    name = data["name"]

    if size <= 0:
        return web.Response(
            text="Invalid file size",
            status=400
        )

    requested = parse_range(
        request.headers.get("Range"),
        size
    )

    if requested:
        start, end = requested
        length = end - start + 1
        status = 206
    else:
        start = 0
        end = size - 1
        length = size
        status = 200

    headers = {
        "Content-Type": mime,
        "Content-Length": str(length),
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{name}"',
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Range",
        "Access-Control-Expose-Headers":
            "Content-Length, Content-Range, Accept-Ranges",
    }

    if status == 206:
        headers["Content-Range"] = (
            f"bytes {start}-{end}/{size}"
        )

    if request.method == "HEAD":
        return web.Response(
            status=status,
            headers=headers
        )

    response = web.StreamResponse(
        status=status,
        headers=headers
    )

    await response.prepare(request)

    first_chunk = start // CHUNK_SIZE
    inner_offset = start % CHUNK_SIZE

    chunks_needed = (
        inner_offset + length + CHUNK_SIZE - 1
    ) // CHUNK_SIZE

    remaining = length

    try:
        number = 0

        async for chunk in mtproto.stream_media(
            file_id,
            offset=first_chunk,
            limit=max(1, chunks_needed)
        ):
            if remaining <= 0:
                break

            if number == 0 and inner_offset:
                chunk = chunk[inner_offset:]

            if len(chunk) > remaining:
                chunk = chunk[:remaining]

            if not chunk:
                break

            await response.write(chunk)

            remaining -= len(chunk)
            number += 1

            if remaining <= 0:
                break

        await response.write_eof()

    except asyncio.CancelledError:
        raise

    except Exception as e:
        print("STREAM ERROR:", repr(e))

        try:
            await response.write_eof()
        except Exception:
            pass

    return response


# =========================================================
# PLAYER
# =========================================================

async def player(request: web.Request):
    token = request.query.get("token")

    if not token:
        return web.Response(
            text="Missing watch token",
            status=400
        )

    data = watch_tokens.get(token)

    if not data:
        return web.Response(
            text="Invalid watch token",
            status=403
        )

    mime = data["mime"]
    name = data["name"]

    stream_url = (
        f"{WEB_URL}/stream?"
        f"token={quote(token, safe='')}"
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport"
content="width=device-width,initial-scale=1.0">
<meta name="theme-color" content="#050507">
<title>NIGHT HUB</title>

<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script src="https://sad.adsgram.ai/js/sad.min.js"></script>

<style>
*{{box-sizing:border-box}}

html,body{{
margin:0;
padding:0;
min-height:100%;
background:
radial-gradient(
circle at 20% 0%,
#26183d 0%,
#0b0911 35%,
#030305 100%
);
color:white;
font-family:-apple-system,BlinkMacSystemFont,
"Segoe UI",Arial,sans-serif;
}}

.container{{
min-height:100vh;
padding:20px 12px 30px;
display:flex;
flex-direction:column;
align-items:center;
}}

.logo{{
width:70px;
height:70px;
border-radius:22px;
display:flex;
align-items:center;
justify-content:center;
background:linear-gradient(
135deg,#9b4dff,#4a00ff);
font-size:32px;
}}

.title{{
font-size:28px;
font-weight:900;
margin:12px 0 0;
}}

.subtitle{{
color:#9997a7;
font-size:13px;
margin-top:5px;
}}

.player{{
width:100%;
max-width:1000px;
margin-top:22px;
padding:8px;
border-radius:22px;
background:rgba(255,255,255,.06);
border:1px solid rgba(255,255,255,.1);
}}

.video-box{{
width:100%;
background:#000;
border-radius:16px;
overflow:hidden;
}}

video{{
display:block;
width:100%;
max-height:75vh;
background:#000;
object-fit:contain;
}}

.status{{
margin-top:14px;
color:#aaa8b5;
font-size:13px;
text-align:center;
}}

.badges{{
display:flex;
gap:8px;
margin-top:10px;
justify-content:center;
flex-wrap:wrap;
}}

.badge{{
padding:7px 12px;
border-radius:999px;
background:rgba(139,44,255,.12);
border:1px solid rgba(139,44,255,.18);
color:#c2a7ff;
font-size:11px;
}}

.ad{{
position:fixed;
inset:0;
z-index:9999;
display:none;
align-items:center;
justify-content:center;
background:
radial-gradient(
circle at top,#241438,#050507 65%);
}}

.ad-box{{
width:90%;
max-width:420px;
padding:30px 20px;
border-radius:24px;
text-align:center;
background:rgba(255,255,255,.055);
}}

.ad-icon{{font-size:48px}}

.ad-title{{
font-size:22px;
font-weight:800;
margin-top:10px;
}}

.ad-status{{
margin-top:10px;
color:#aaa8b5;
}}
</style>
</head>

<body>

<div class="container">

<div class="logo">🎬</div>

<h1 class="title">NIGHT HUB</h1>

<div class="subtitle">
Premium Online Video
</div>

<div class="player">

<div class="video-box">

<video
id="video"
controls
playsinline
webkit-playsinline
preload="metadata"
controlsList="nodownload">

<source
src="{stream_url}"
type="{mime}">

Your browser does not support HTML5 video.

</video>

</div>

</div>

<div id="status" class="status">
⏳ Preparing video...
</div>

<div class="badges">
<div class="badge">HD+</div>
<div class="badge">SEEK</div>
<div class="badge">RANGE</div>
<div class="badge">ONLINE</div>
</div>

</div>

<div id="ad" class="ad">

<div class="ad-box">

<div class="ad-icon">📺</div>

<div class="ad-title">
Advertisement
</div>

<div id="adStatus" class="ad-status">
Advertisement loading...
</div>

</div>

</div>

<script>

const tg=window.Telegram?.WebApp;

if(tg){{
tg.ready();
tg.expand();

try{{
tg.setHeaderColor("#050507");
tg.setBackgroundColor("#050507");
}}catch(e){{}}
}}

const video=document.getElementById("video");
const status=document.getElementById("status");
const ad=document.getElementById("ad");
const adStatus=document.getElementById("adStatus");

let started=false;
let controller=null;

try{{

if(window.Adsgram && "{ADSGRAM_BLOCK_ID}"){{

controller=window.Adsgram.init({{
blockId:"{ADSGRAM_BLOCK_ID}"
}});

}}

}}catch(e){{
console.log("AdsGram error",e);
}}

async function showAd(){{

if(!controller)
return true;

try{{

ad.style.display="flex";

adStatus.textContent=
"📺 Advertisement loading...";

await controller.show();

adStatus.textContent=
"✅ Advertisement finished";

await new Promise(
r=>setTimeout(r,400)
);

ad.style.display="none";

return true;

}}catch(e){{

console.log("Ad error",e);

ad.style.display="none";

return true;

}}

}}

async function startVideo(){{

if(started)
return;

started=true;

status.textContent=
"📺 Advertisement...";

await showAd();

status.textContent=
"▶️ Starting video...";

try{{

await video.play();

status.textContent=
"▶️ NIGHT HUB";

}}catch(e){{

status.textContent=
"▶️ Tap video to play";

}}

}}

document.addEventListener(
"click",
function(){{
if(!started)
startVideo();
}},
{{once:true}}
);

video.addEventListener(
"loadedmetadata",
function(){{
status.textContent="✅ Video ready";
}}
);

video.addEventListener(
"playing",
function(){{
status.textContent="▶️ NIGHT HUB";
}}
);

video.addEventListener(
"waiting",
function(){{
status.textContent="⏳ Buffering...";
}}
);

video.addEventListener(
"pause",
function(){{
status.textContent="⏸️ Paused";
}}
);

video.addEventListener(
"ended",
function(){{
status.textContent="✅ Video finished";
}}
);

video.addEventListener(
"error",
function(){{
status.textContent=
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
# WEB SERVER
# =========================================================

async def health(request):
    return web.Response(
        text="NIGHT HUB is running ✅"
    )


async def start_web_server():
    app = web.Application(
        client_max_size=2 * 1024 * 1024 * 1024
    )

    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/watch", player)

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

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    print("====================================")
    print("🌙 NIGHT HUB WEB SERVER STARTED")
    print("PORT:", PORT)
    print("WEB_URL:", WEB_URL)
    print("CHANNEL_ID:", CHANNEL_ID)
    print("ADMIN_ID:", ADMIN_ID)
    print("FFMPEG: ENABLED")
    print("AUTO COVER: ENABLED")
    print("MINI APP: ENABLED")
    print("RANGE STREAMING: ENABLED")
    print("====================================")


# =========================================================
# COMMANDS
# =========================================================

async def setup_commands():

    await bot.set_my_commands(
        [],
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
                description="Open Admin Panel"
            ),
            BotCommand(
                command="addvideo",
                description="Add Video"
            ),
            BotCommand(
                command="help",
                description="Help"
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

    print("Starting Pyrogram...")

    await mtproto.start()

    print("Pyrogram started ✅")

    await setup_commands()

    print("Commands configured ✅")

    await start_web_server()

    print("Starting NIGHT HUB bot...")

    try:

        await dp.start_polling(bot)

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
        asyncio.run(main())

    except KeyboardInterrupt:
        print("NIGHT HUB stopped.")
