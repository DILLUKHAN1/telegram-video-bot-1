import os
import asyncio
import secrets
from urllib.parse import quote

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
)

from pyrogram import Client


# =========================================================
#                    NIGHT HUB
#          FAST VIDEO PUBLISH + MINI APP
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

required = {
    "BOT_TOKEN": BOT_TOKEN,
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "ADMIN_ID": ADMIN_ID,
    "CHANNEL_ID": CHANNEL_ID,
    "WATCH_SECRET": WATCH_SECRET,
}

for name, value in required.items():

    if not value:

        raise RuntimeError(
            f"{name} environment variable is missing"
        )


# =========================================================
# CONVERT IDs
# =========================================================

try:

    ADMIN_ID = int(ADMIN_ID)

    CHANNEL_ID = int(CHANNEL_ID)

    API_ID = int(API_ID)

except ValueError as error:

    raise RuntimeError(
        "ADMIN_ID, CHANNEL_ID and API_ID must be numeric"
    ) from error


# =========================================================
# WEB URL
# =========================================================

if not WEB_URL:

    domain = os.getenv(
        "RAILWAY_PUBLIC_DOMAIN"
    )

    if domain:

        WEB_URL = (
            f"https://{domain}"
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
# PYROGRAM
#
# Pyrogram is ONLY used for:
# - Reading channel history
# - Streaming Telegram files
#
# Channel publishing is done by aiogram.
#
# This avoids the previous:
# InlineKeyboardMarkup -> .write error
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

MAX_FILE_SIZE = (
    2 * 1024 * 1024 * 1024
)


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

def is_admin(
    user_id: int
) -> bool:

    return user_id == ADMIN_ID


# =========================================================
# WATCH URL
# =========================================================

def make_watch_url(

    file_id,

    size_bytes,

    mime_type,

    file_name,

):

    token = secrets.token_urlsafe(
        32
    )

    watch_tokens[token] = {

        "file_id": file_id,

        "size": int(
            size_bytes or 0
        ),

        "mime":
            mime_type
            or "video/mp4",

        "name":
            file_name
            or "video.mp4",

    }

    return (

        f"{WEB_URL}/watch?"

        f"token={quote(token, safe='')}"

    )


# =========================================================
# WATCH KEYBOARD
# =========================================================

def watch_keyboard(

    file_id,

    size_bytes,

    mime_type,

    file_name,

):

    watch_url = make_watch_url(

        file_id,

        size_bytes,

        mime_type,

        file_name,

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

                    callback_data=
                        "admin_add_video",

                ),

                InlineKeyboardButton(

                    text="📚 VIDEOS",

                    callback_data=
                        "admin_videos",

                ),

            ],

            [

                InlineKeyboardButton(

                    text="📢 CHANNEL",

                    callback_data=
                        "admin_channel",

                ),

                InlineKeyboardButton(

                    text="👥 USERS",

                    callback_data=
                        "admin_users",

                ),

            ],

            [

                InlineKeyboardButton(

                    text="🔄 REFRESH",

                    callback_data=
                        "admin_refresh",

                ),

            ],

            [

                InlineKeyboardButton(

                    text="❌ CLOSE",

                    callback_data=
                        "admin_close",

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

        "🎬 Fast Video Management\n"

        "📢 Private Channel\n"

        "👥 User Access\n"

        "🎥 Mini App\n"

        "🖼️ Telegram Auto Cover\n"

        "⚡ Fast Publish\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "👇 Select an option:"

    )


# =========================================================
# GET VIDEO INFORMATION
# =========================================================

def get_video_info(
    message: Message
):

    # -----------------------------------------------------
    # NORMAL TELEGRAM VIDEO
    # -----------------------------------------------------

    if message.video:

        video = message.video

        return {

            "file_id":
                video.file_id,

            "file_size":
                video.file_size or 0,

            "mime_type":
                video.mime_type
                or "video/mp4",

            "file_name":
                video.file_name
                or "video.mp4",

            "thumbnail_file_id":
                (
                    video.thumbnail.file_id
                    if video.thumbnail
                    else None
                ),

        }


    # -----------------------------------------------------
    # DOCUMENT VIDEO
    # -----------------------------------------------------

    if message.document:

        document = message.document

        mime = (
            document.mime_type
            or ""
        )

        name = (
            document.file_name
            or "video.mp4"
        )

        is_video = (

            mime.startswith(
                "video/"
            )

            or name.lower().endswith(
                VIDEO_EXTENSIONS
            )

        )

        if not is_video:

            return None


        return {

            "file_id":
                document.file_id,

            "file_size":
                document.file_size
                or 0,

            "mime_type":
                mime
                or "video/mp4",

            "file_name":
                name,

            "thumbnail_file_id":
                (
                    document.thumbnail.file_id
                    if document.thumbnail
                    else None
                ),

        }


    return None


# =========================================================
# PUBLISH VIDEO TO CHANNEL
#
# IMPORTANT:
# No download.
# No FFmpeg.
# No Pyrogram upload.
#
# Telegram Bot API directly sends the existing file_id.
# =========================================================

async def publish_video_to_channel(

    file_id,

    file_size,

    mime_type,

    file_name,

    thumbnail_file_id,

):

    caption = (

        "🌙 <b>NIGHT HUB</b>\n\n"

        f"🎬 <b>{file_name}</b>\n\n"

        "🎥 Watch this video online for FREE!\n"

        "👇 Tap the button below."

    )


    keyboard = watch_keyboard(

        file_id,

        file_size,

        mime_type,

        file_name,

    )


    kwargs = {

        "chat_id":
            CHANNEL_ID,

        "video":
            file_id,

        "caption":
            caption,

        "parse_mode":
            "HTML",

        "supports_streaming":
            True,

        "protect_content":
            True,

        "reply_markup":
            keyboard,

    }


    # -----------------------------------------------------
    # REUSE TELEGRAM THUMBNAIL
    # -----------------------------------------------------

    if thumbnail_file_id:

        kwargs["thumbnail"] = (
            thumbnail_file_id
        )


    return await bot.send_video(
        **kwargs
    )


# =========================================================
# PROCESS ONE VIDEO
# =========================================================

async def process_one_video(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    info = get_video_info(
        message
    )

    if not info:

        return


    file_id = info["file_id"]

    file_size = info["file_size"]

    mime_type = info["mime_type"]

    file_name = info["file_name"]

    thumbnail_file_id = (
        info["thumbnail_file_id"]
    )


    # =====================================================
    # SIZE CHECK
    # =====================================================

    if file_size > MAX_FILE_SIZE:

        await message.answer(

            "❌ Video 2 GB se badi hai."

        )

        return


    # =====================================================
    # DUPLICATE PROCESS CHECK
    # =====================================================

    if file_id in processing_videos:

        return


    processing_videos.add(
        file_id
    )


    status = None


    try:

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        status = await message.answer(

            "⚡ <b>VIDEO RECEIVED</b>\n\n"

            f"🎬 <b>{file_name}</b>\n"

            f"📦 "
            f"{file_size / (1024 * 1024):.2f} MB\n\n"

            "🚀 Fast mode active...\n"

            "🖼️ Telegram thumbnail reuse ho rahi hai.\n"

            "📢 Channel mein publish ho rahi hai...\n\n"

            "⏳ Please wait...",

            parse_mode="HTML"

        )


        # -------------------------------------------------
        # DIRECT CHANNEL PUBLISH
        # -------------------------------------------------

        sent = await publish_video_to_channel(

            file_id=

                file_id,

            file_size=

                file_size,

            mime_type=

                mime_type,

            file_name=

                file_name,

            thumbnail_file_id=

                thumbnail_file_id,

        )


        # -------------------------------------------------
        # MESSAGE ID
        # -------------------------------------------------

        message_id = getattr(

            sent,

            "message_id",

            None

        )


        if not message_id:

            message_id = getattr(

                sent,

                "id",

                0

            )


        # -------------------------------------------------
        # SAVE LIBRARY
        # -------------------------------------------------

        video_library[message_id] = {

            "file_id":
                file_id,

            "size":
                file_size,

            "mime":
                mime_type,

            "name":
                file_name,

            "message_id":
                message_id,

        }


        # -------------------------------------------------
        # WATCH BUTTON
        # -------------------------------------------------

        keyboard = watch_keyboard(

            file_id,

            file_size,

            mime_type,

            file_name,

        )


        # -------------------------------------------------
        # SUCCESS MESSAGE
        # -------------------------------------------------

        await message.answer(

            "✅ <b>VIDEO PUBLISHED</b>\n\n"

            f"🎬 <b>{file_name}</b>\n\n"

            "🖼️ Cover: "

            f"{'✅ Telegram cover' if thumbnail_file_id else '⚠️ No thumbnail'}\n"

            "📢 Channel: ✅\n"

            "🔘 WATCH NOW button: ✅\n"

            "🎥 Mini App: ✅\n"

            "⚡ Fast publish: ✅",

            reply_markup=keyboard,

            parse_mode="HTML",

            protect_content=True,

        )


        # -------------------------------------------------
        # DELETE STATUS
        # -------------------------------------------------

        try:

            await status.delete()

        except Exception:

            pass


    except Exception as error:

        print(

            "VIDEO PROCESS ERROR:",

            repr(error)

        )


        try:

            if status:

                await status.edit_text(

                    "❌ <b>VIDEO PROCESS FAILED</b>\n\n"

                    f"<code>{error}</code>\n\n"

                    "Railway logs check karein.",

                    parse_mode="HTML"

                )

            else:

                await message.answer(

                    "❌ Video process failed:\n"

                    f"<code>{error}</code>",

                    parse_mode="HTML"

                )

        except Exception:

            pass


    finally:

        processing_videos.discard(
            file_id
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

    if is_admin(
        message.from_user.id
    ):

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            "👑 <b>ADMIN MODE</b>\n\n"

            "⚡ FAST VIDEO PUBLISHING ENABLED\n\n"

            "🎬 New video add karne ke liye: "
            "/addvideo\n\n"

            "👑 Admin Panel: "
            "/admin\n\n"

            "📹 Video → Telegram Cover → Channel\n"

            "🔘 WATCH NOW → Mini App",

            parse_mode="HTML"

        )

    else:

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

        found = []


        # -------------------------------------------------
        # CHANNEL HISTORY
        # -------------------------------------------------

        async for channel_message in (

            mtproto.get_chat_history(

                CHANNEL_ID,

                limit=50

            )

        ):

            video = (
                channel_message.video
            )


            if (

                not video

                and channel_message.document

            ):

                document = (
                    channel_message.document
                )

                mime = (
                    document.mime_type
                    or ""
                )

                name = (
                    document.file_name
                    or ""
                )


                if (

                    mime.startswith(
                        "video/"
                    )

                    or name.lower().endswith(
                        VIDEO_EXTENSIONS
                    )

                ):

                    video = document


            if not video:

                continue


            found.append({

                "file_id":
                    video.file_id,

                "file_size":
                    getattr(
                        video,
                        "file_size",
                        0
                    ) or 0,

                "mime_type":
                    getattr(
                        video,
                        "mime_type",
                        None
                    ) or "video/mp4",

                "file_name":
                    getattr(
                        video,
                        "file_name",
                        None
                    ) or "video.mp4",

            })


        # -------------------------------------------------
        # NO VIDEOS
        # -------------------------------------------------

        if not found:

            await message.answer(

                "🌙 <b>NIGHT HUB</b>\n\n"

                "🎬 Welcome!\n\n"

                "⚠️ <b>Abhi koi video available nahi hai.</b>",

                parse_mode="HTML"

            )

            return


        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            f"🎬 <b>{len(found)} videos available</b>\n\n"

            "👇 Video select karke "
            "WATCH NOW press karein.",

            parse_mode="HTML"

        )


        # -------------------------------------------------
        # VIDEO CARDS
        # -------------------------------------------------

        for index, item in enumerate(
            found,
            1
        ):

            size_mb = (

                item["file_size"]
                / (1024 * 1024)

                if item["file_size"]

                else 0

            )


            await message.answer(

                f"🎬 <b>VIDEO {index}</b>\n\n"

                f"📁 {item['file_name']}\n"

                f"📦 {size_mb:.2f} MB\n\n"

                "👉 <b>WATCH NOW</b>",

                reply_markup=watch_keyboard(

                    item["file_id"],

                    item["file_size"],

                    item["mime_type"],

                    item["file_name"],

                ),

                parse_mode="HTML",

                protect_content=True,

            )


    except Exception as error:

        print(

            "PUBLIC LIBRARY ERROR:",

            repr(error)

        )


        await message.answer(

            "⚠️ Video library temporarily unavailable.\n"

            "Please try again later."

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

    if is_admin(
        message.from_user.id
    ):

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

@dp.message(
    Command("admin")
)
async def admin_cmd(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(

            "🔒 <b>ACCESS DENIED</b>\n\n"

            "Aapko Admin Panel ka access nahi hai.",

            parse_mode="HTML"

        )

        return


    await message.answer(

        admin_panel_text(),

        reply_markup=
            admin_panel_keyboard(),

        parse_mode="HTML"

    )


# =========================================================
# ADD VIDEO COMMAND
# =========================================================

@dp.message(
    Command("addvideo")
)
async def add_video_cmd(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(

            "🔒 <b>UPLOAD DISABLED</b>\n\n"

            "Sirf Admin video upload kar sakta hai.",

            parse_mode="HTML"

        )

        return


    await message.answer(

        "👑 <b>ADMIN VIDEO UPLOAD MODE</b>\n\n"

        "📹 Ab video bhejo.\n\n"

        "🖼️ Telegram ka existing thumbnail "
        "reuse kiya jayega.\n\n"

        "📢 Uske baad video private channel "
        "mein publish hogi.\n\n"

        "⚡ Fast mode enabled.",

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

    if not is_admin(
        message.from_user.id
    ):

        return


    await message.answer(

        "ℹ️ Current processing ko "
        "force cancel nahi kiya gaya.\n\n"

        "Processing complete hone dein."

    )


# =========================================================
# VIDEO HANDLER
# =========================================================

@dp.message(
    F.video
)
async def video_received(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(

            "🔒 <b>UPLOAD DISABLED</b>\n\n"

            "Public users video upload nahi kar sakte.\n\n"

            "🎬 Videos dekhne ke liye "
            "/start use karein.",

            parse_mode="HTML"

        )

        return


    await process_one_video(
        message
    )


# =========================================================
# DOCUMENT VIDEO HANDLER
# =========================================================

@dp.message(
    F.document
)
async def document_received(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

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

    name = (
        document.file_name
        or ""
    )


    is_video = (

        mime.startswith(
            "video/"
        )

        or name.lower().endswith(
            VIDEO_EXTENSIONS
        )

    )


    if not is_video:

        return


    await process_one_video(
        message
    )


# =========================================================
# ADMIN CALLBACK
# ADD VIDEO
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

        "🖼️ Telegram thumbnail reuse hogi.\n\n"

        "📦 Multiple videos bhej sakte ho.\n\n"

        "📢 Har video private channel mein publish hogi.\n\n"

        "⚡ Fast publish mode.",

        parse_mode="HTML"

    )


    await callback.answer()


# =========================================================
# ADMIN CALLBACK
# VIDEOS
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

                    channel_message
                    .document
                    .mime_type
                    or ""

                )


                if mime.startswith(
                    "video/"
                ):

                    count += 1


        keyboard = InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(

                        text="⬅️ BACK",

                        callback_data=
                            "admin_back"

                    )

                ]

            ]

        )


        await callback.message.edit_text(

            "📚 <b>VIDEO LIBRARY</b>\n\n"

            f"🎬 Channel videos: <b>{count}</b>\n\n"

            "📢 Private Channel permanent "
            "video library ke roop mein "
            "use ho raha hai.",

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
# ADMIN CALLBACK
# CHANNEL
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

                    callback_data=
                        "admin_back"

                )

            ]

        ]

    )


    await callback.message.edit_text(

        "📢 <b>PRIVATE CHANNEL</b>\n\n"

        "CHANNEL_ID:\n"

        f"<code>{CHANNEL_ID}</code>\n\n"

        "Bot Channel Admin: ✅\n"

        "Video Publishing: ✅\n"

        "Watch Button: ✅\n"

        "Channel Library: ✅",

        reply_markup=keyboard,

        parse_mode="HTML"

    )


    await callback.answer()


# =========================================================
# ADMIN CALLBACK
# USERS
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

                    callback_data=
                        "admin_back"

                )

            ]

        ]

    )


    await callback.message.edit_text(

        "👥 <b>USER ACCESS</b>\n\n"

        "👑 ADMIN\n"

        "✅ Admin Panel\n"

        "✅ Upload Video\n"

        "✅ Automatic Telegram Cover\n"

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

        reply_markup=
            admin_panel_keyboard(),

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

        reply_markup=
            admin_panel_keyboard(),

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


    html = f'''
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

*{{

    box-sizing:border-box

}}

html,body{{

    margin:0;

    padding:0;

    width:100%;

    min-height:100%;

    background:

        radial-gradient(

            circle at 20% 0%,

            #26183d 0%,

            #0b0911 35%,

            #030305 100%

        );

    color:white;

    font-family:

        -apple-system,

        BlinkMacSystemFont,

        "Segoe UI",

        Arial,

        sans-serif;

}}

.container{{

    min-height:100vh;

    display:flex;

    flex-direction:column;

    align-items:center;

    padding:20px 12px 30px;

}}

.logo{{

    width:70px;

    height:70px;

    border-radius:22px;

    display:flex;

    align-items:center;

    justify-content:center;

    background:

        linear-gradient(

            135deg,

            #9b4dff,

            #4a00ff

        );

    font-size:32px;

}}

.title{{

    margin:12px 0 0;

    font-size:28px;

    font-weight:900;

}}

.subtitle{{

    margin-top:5px;

    color:#9997a7;

    font-size:13px;

}}

.player-card{{

    width:100%;

    max-width:1000px;

    margin-top:22px;

    padding:8px;

    border-radius:22px;

    background:

        rgba(255,255,255,.06);

    border:

        1px solid

        rgba(255,255,255,.10);

}}

.video-container{{

    width:100%;

    background:black;

    border-radius:16px;

    overflow:hidden;

}}

video{{

    display:block;

    width:100%;

    max-height:75vh;

    background:black;

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

    background:

        rgba(139,44,255,.12);

    border:

        1px solid

        rgba(139,44,255,.18);

    color:#c2a7ff;

    font-size:11px;

}}

.ad-screen{{

    position:fixed;

    inset:0;

    z-index:9999;

    display:none;

    align-items:center;

    justify-content:center;

    flex-direction:column;

    padding:25px;

    background:

        radial-gradient(

            circle at top,

            #241438,

            #050507 65%

        );

}}

.ad-box{{

    width:100%;

    max-width:420px;

    padding:30px 20px;

    border-radius:24px;

    text-align:center;

    background:

        rgba(255,255,255,.055);

}}

.ad-icon{{

    font-size:48px;

}}

.ad-title{{

    font-size:22px;

    font-weight:800;

    margin-top:10px;

}}

.ad-status{{

    margin-top:10px;

    color:#aaa8b5;

}}

.footer{{

    margin-top:auto;

    padding-top:30px;

    color:#5f5d69;

    font-size:11px;

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

if(tg){{

    tg.ready();

    tg.expand();

    try{{

        tg.setHeaderColor(
            "#050507"
        );

        tg.setBackgroundColor(
            "#050507"
        );

    }}catch(e){{}}

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


let started=false;

let adController=null;


try{{

    if(

        window.Adsgram

        &&

        "{ADSGRAM_BLOCK_ID}"

    ){{

        adController =
            window.Adsgram.init({{

                blockId:
                    "{ADSGRAM_BLOCK_ID}"

            }});

    }}

}}catch(e){{

    console.log(
        "AdsGram error:",
        e
    );

}}


async function showAd(){{

    if(!adController)

        return true;


    try{{

        adScreen.style.display =
            "flex";

        adStatus.textContent =
            "📺 Advertisement loading...";


        await adController.show();


        adStatus.textContent =
            "✅ Advertisement finished";


        await new Promise(

            r => setTimeout(
                r,
                400
            )

        );


        adScreen.style.display =
            "none";


        return true;


    }}catch(e){{

        console.log(
            "Ad error:",
            e
        );


        adScreen.style.display =
            "none";


        return true;

    }}

}}


async function startVideo(){{

    if(started)

        return;


    started=true;


    status.textContent =
        "📺 Advertisement...";


    await showAd();


    status.textContent =
        "▶️ Starting video...";


    try{{

        await video.play();


        status.textContent =
            "▶️ NIGHT HUB";


    }}catch(e){{

        status.textContent =
            "▶️ Tap the video to play";

    }}

}}


document.addEventListener(

    "click",

    () => {{

        if(!started)

            startVideo();

    }},

    {{once:true}}

);


video.addEventListener(

    "loadedmetadata",

    () =>

        status.textContent =
            "✅ Video ready"

);


video.addEventListener(

    "playing",

    () =>

        status.textContent =
            "▶️ NIGHT HUB"

);


video.addEventListener(

    "waiting",

    () =>

        status.textContent =
            "⏳ Buffering..."

);


video.addEventListener(

    "pause",

    () =>

        status.textContent =
            "⏸️ Paused"

);


video.addEventListener(

    "ended",

    () =>

        status.textContent =
            "✅ Video finished"

);


video.addEventListener(

    "error",

    () =>

        status.textContent =
            "❌ Video could not be played"

);

</script>

</body>

</html>
'''


    return web.Response(

        text=html,

        content_type="text/html"

    )


# =========================================================
# RANGE PARSER
# =========================================================

def parse_range(
    header,
    file_size
):

    if (

        not header

        or not header.startswith(
            "bytes="
        )

    ):

        return None


    value = (

        header[6:]

        .strip()

        .split(",", 1)[0]

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
        # -------------------------------------------------

        if not start_text:

            length = min(

                int(end_text),

                file_size

            )


            if length <= 0:

                return None


            return (

                file_size - length,

                file_size - 1

            )


        # -------------------------------------------------
        # NORMAL RANGE
        # -------------------------------------------------

        start = int(
            start_text
        )


        if (

            start < 0

            or start >= file_size

        ):

            return None


        if end_text:

            end = min(

                int(end_text),

                file_size - 1

            )

        else:

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


    requested = parse_range(

        range_header,

        file_size

    )


    # =====================================================
    # HEAD
    # =====================================================

    if request.method == "HEAD":

        return web.Response(

            status=200,

            headers={

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

                "Access-Control-Allow-Origin":
                    "*",

            }

        )


    # =====================================================
    # RESPONSE RANGE
    # =====================================================

    if requested:

        start, end = requested

        length = (
            end
            - start
            + 1
        )

        status_code = 206


    else:

        start = 0

        end = (
            file_size - 1
        )

        length = file_size

        status_code = 200


    headers = {

        "Content-Type":
            mime_type,

        "Content-Length":
            str(length),

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

            f"{start}-"

            f"{end}/"

            f"{file_size}"

        )


    response = web.StreamResponse(

        status=status_code,

        headers=headers

    )


    await response.prepare(
        request
    )


    remaining = length


    try:

        # -------------------------------------------------
        # IMPORTANT
        #
        # Pyrogram stream_media offset
        # is in bytes.
        # -------------------------------------------------

        async for chunk in (

            mtproto.stream_media(

                file_id,

                offset=start,

                limit=0,

            )

        ):

            if remaining <= 0:

                break


            if len(chunk) > remaining:

                chunk = chunk[
                    :remaining
                ]


            if not chunk:

                break


            await response.write(
                chunk
            )


            remaining -= len(
                chunk
            )


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
        "⚡ FAST PUBLISH: ENABLED"
    )

    print(
        "🖼️ TELEGRAM THUMBNAIL REUSE: ENABLED"
    )

    print(
        "📥 FULL VIDEO DOWNLOAD: DISABLED"
    )

    print(
        "🎞️ FFMPEG COVER PROCESSING: DISABLED"
    )

    print(
        "🔘 CHANNEL WATCH BUTTON: ENABLED"
    )

    print(
        "🎥 MINI APP: ENABLED"
    )

    print(
        "📡 RANGE STREAMING: ENABLED"
    )

    print(
        "=========================================="
    )


# =========================================================
# COMMAND MENU
# =========================================================

async def setup_commands():

    # -----------------------------------------------------
    # PUBLIC
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

                description=
                    "Start NIGHT HUB"

            ),

            BotCommand(

                command="admin",

                description=
                    "Open Admin Panel"

            ),

            BotCommand(

                command="addvideo",

                description=
                    "Add Video"

            ),

            BotCommand(

                command="cancel",

                description=
                    "Cancel"

            ),

            BotCommand(

                command="help",

                description=
                    "Admin Help"

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
