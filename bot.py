import os
import asyncio
import secrets
import tempfile
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
from pyrogram.types import InputMediaVideo


# =========================================================
# =========================================================
#                     NIGHT HUB
#          CHANNEL + ADMIN BOT + MINI APP
# =========================================================
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
    "int-44048"
)


# =========================================================
# REQUIRED VARIABLES CHECK
# =========================================================

required_variables = {
    "BOT_TOKEN": BOT_TOKEN,
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "ADMIN_ID": ADMIN_ID,
    "CHANNEL_ID": CHANNEL_ID,
    "WATCH_SECRET": WATCH_SECRET,
}


for variable_name, variable_value in required_variables.items():

    if not variable_value:

        raise RuntimeError(
            f"{variable_name} environment variable is missing"
        )


# =========================================================
# ADMIN ID
# =========================================================

try:

    ADMIN_ID = int(ADMIN_ID)

except ValueError:

    raise RuntimeError(
        "ADMIN_ID must be a numeric Telegram User ID"
    )


# =========================================================
# CHANNEL ID
# =========================================================

try:

    CHANNEL_ID = int(CHANNEL_ID)

except ValueError:

    raise RuntimeError(
        "CHANNEL_ID must be a numeric Telegram Channel ID"
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

    api_id=int(API_ID),

    api_hash=API_HASH,

    bot_token=BOT_TOKEN,

    no_updates=True,

    in_memory=True,
)


# =========================================================
# STREAM SETTINGS
# =========================================================

CHUNK_SIZE = 1024 * 1024


# =========================================================
# ADMIN UPLOAD STATE
# =========================================================

pending_videos = {}


# =========================================================
# WATCH TOKEN STORAGE
#
# Tokens are generated for every video.
# This prevents a user from directly guessing
# the original Telegram file_id URL.
# =========================================================

watch_tokens = {}


# =========================================================
# SIMPLE VIDEO LIBRARY
#
# Channel is the permanent source of videos.
# This dictionary is only used during current runtime.
# =========================================================

video_library = {}


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id: int) -> bool:

    return user_id == ADMIN_ID


# =========================================================
# ADMIN PANEL KEYBOARD
# =========================================================

def admin_panel_keyboard():

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
                ),

            ],

            [

                InlineKeyboardButton(
                    text="📢 CHANNEL",
                    callback_data="admin_channel"
                ),

                InlineKeyboardButton(
                    text="👥 USERS",
                    callback_data="admin_users"
                ),

            ],

            [

                InlineKeyboardButton(
                    text="🔄 REFRESH",
                    callback_data="admin_refresh"
                ),

            ],

            [

                InlineKeyboardButton(
                    text="❌ CLOSE",
                    callback_data="admin_close"
                )

            ]

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
        "💰 AdsGram\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "👇 Select an option:"

    )


# =========================================================
# WATCH URL
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

        "size": int(size_bytes),

        "mime": mime_type or "video/mp4",

        "name": file_name or "video.mp4",

    }

    return (

        f"{WEB_URL}"

        f"/watch?"

        f"token="

        f"{quote(token, safe='')}"

    )


# =========================================================
# DIRECT WATCH BUTTON
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

                    )

                )

            ]

        ]

    )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(message: Message):

    user_id = message.from_user.id


    # =====================================================
    # ADMIN
    # =====================================================

    if is_admin(user_id):

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            "👑 <b>ADMIN MODE</b>\n\n"

            "Aapke paas full control hai.\n\n"

            "🎬 Video upload:\n"
            "/addvideo\n\n"

            "👑 Admin Panel:\n"
            "/admin\n\n"

            "📹 Video → Cover → WATCH NOW\n"
            "📢 Video private channel mein post hogi.",

            parse_mode="HTML"

        )

        return


    # =====================================================
    # PUBLIC USER
    # =====================================================

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

        # -----------------------------------------------
        # Read latest videos from private channel
        # -----------------------------------------------

        async for channel_message in mtproto.get_chat_history(
            CHANNEL_ID,
            limit=30
        ):

            video = None

            if channel_message.video:

                video = channel_message.video

            elif channel_message.document:

                document = channel_message.document

                mime = document.mime_type or ""

                if mime.startswith("video/"):

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


        # -----------------------------------------------
        # No videos
        # -----------------------------------------------

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


        # -----------------------------------------------
        # Header
        # -----------------------------------------------

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            f"🎬 <b>{len(found_videos)} videos available</b>\n\n"

            "👇 Watch Now par click karein:",

            parse_mode="HTML"

        )


        # -----------------------------------------------
        # Send video cards
        # -----------------------------------------------

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
            "Public library error:",
            repr(error)
        )


        await message.answer(

            "⚠️ Video library temporarily "
            "unavailable.\n\n"
            "Please try again later."

        )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_cmd(message: Message):

    user_id = message.from_user.id


    if is_admin(user_id):

        await message.answer(

            "🌙 <b>NIGHT HUB ADMIN HELP</b>\n\n"

            "/start - Start\n"
            "/admin - Admin Panel\n"
            "/addvideo - Add Video\n"
            "/cancel - Cancel upload\n"
            "/help - Help",

            parse_mode="HTML"

        )

    else:

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            "🎬 Available videos ke liye "
            "/start press karein.",

            parse_mode="HTML"

        )


# =========================================================
# ADMIN COMMAND
# =========================================================

@dp.message(Command("admin"))
async def admin_cmd(message: Message):

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
# ADD VIDEO COMMAND
# =========================================================

@dp.message(Command("addvideo"))
async def add_video_cmd(message: Message):

    user_id = message.from_user.id


    if not is_admin(user_id):

        await message.answer(

            "🔒 <b>ACCESS DENIED</b>\n\n"

            "Sirf Admin video upload kar sakta hai.",

            parse_mode="HTML"

        )

        return


    pending_videos[user_id] = {

        "file_id": None,

        "file_size": 0,

        "mime_type": "video/mp4",

        "file_name": "video.mp4",

        "cover_file_id": None,

        "cover_path": None,

    }


    await message.answer(

        "👑 <b>ADMIN UPLOAD MODE</b>\n\n"

        "📹 Ab video ya forwarded video bhejo.\n\n"

        "Video ke baad bot Cover Photo maangega.\n\n"

        "❌ Cancel:\n"
        "/cancel",

        parse_mode="HTML"

    )


# =========================================================
# CANCEL
# =========================================================

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):

    user_id = message.from_user.id


    if not is_admin(user_id):

        return


    if user_id in pending_videos:

        data = pending_videos.pop(
            user_id
        )

        cover_path = data.get(
            "cover_path"
        )

        if cover_path:

            try:

                if os.path.exists(
                    cover_path
                ):

                    os.remove(
                        cover_path
                    )

            except Exception:

                pass


    await message.answer(
        "❌ Upload cancelled."
    )


# =========================================================
# VIDEO RECEIVED
# =========================================================

@dp.message(F.video)
async def video_received(message: Message):

    user_id = message.from_user.id


    # =====================================================
    # PUBLIC USER
    # =====================================================

    if not is_admin(user_id):

        await message.answer(

            "🔒 <b>UPLOAD DISABLED</b>\n\n"

            "Public users video upload nahi kar sakte.\n\n"

            "🎬 Videos dekhne ke liye /start use karein.",

            parse_mode="HTML"

        )

        return


    # =====================================================
    # REQUIRE ADD VIDEO MODE
    # =====================================================

    if user_id not in pending_videos:

        await message.answer(

            "⚠️ Pehle /addvideo command bhejo."

        )

        return


    video = message.video


    pending_videos[user_id].update({

        "file_id":
            video.file_id,

        "file_size":
            video.file_size or 0,

        "mime_type":
            video.mime_type or "video/mp4",

        "file_name":
            video.file_name or "video.mp4",

    })


    # =====================================================
    # TELEGRAM THUMBNAIL
    # =====================================================

    try:

        if video.thumbnail:

            pending_videos[user_id][
                "cover_file_id"
            ] = video.thumbnail.file_id

    except Exception as error:

        print(
            "Thumbnail error:",
            repr(error)
        )


    await message.answer(

        "✅ <b>VIDEO RECEIVED</b>\n\n"

        f"📁 {video.file_name or 'video.mp4'}\n"

        f"📦 "
        f"{(video.file_size or 0) / (1024 * 1024):.2f} MB\n\n"

        "🖼️ Ab <b>Cover Photo</b> bhejo.\n\n"

        "Agar custom cover nahi chahiye:\n"
        "/usecover",

        parse_mode="HTML"

    )


# =========================================================
# DOCUMENT VIDEO
# =========================================================

@dp.message(F.document)
async def document_received(message: Message):

    user_id = message.from_user.id


    # =====================================================
    # PUBLIC USER
    # =====================================================

    if not is_admin(user_id):

        await message.answer(

            "🔒 <b>UPLOAD DISABLED</b>\n\n"

            "Public users video upload nahi kar sakte.",

            parse_mode="HTML"

        )

        return


    if user_id not in pending_videos:

        await message.answer(

            "⚠️ Pehle /addvideo command bhejo."

        )

        return


    document = message.document


    mime = document.mime_type or ""

    file_name = (
        document.file_name
        or "video.mp4"
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

        or file_name.lower().endswith(
            video_extensions
        )

    )


    if not is_video:

        await message.answer(

            "❌ Ye video file nahi lag rahi."

        )

        return


    pending_videos[user_id].update({

        "file_id":
            document.file_id,

        "file_size":
            document.file_size or 0,

        "mime_type":
            mime or "video/mp4",

        "file_name":
            file_name,

    })


    try:

        if document.thumbnail:

            pending_videos[user_id][
                "cover_file_id"
            ] = document.thumbnail.file_id

    except Exception as error:

        print(
            "Document thumbnail error:",
            repr(error)
        )


    await message.answer(

        "✅ <b>VIDEO FILE RECEIVED</b>\n\n"

        f"📁 {file_name}\n"

        f"📦 "
        f"{(document.file_size or 0) / (1024 * 1024):.2f} MB\n\n"

        "🖼️ Ab <b>Cover Photo</b> bhejo.\n\n"

        "Custom cover nahi chahiye:\n"
        "/usecover",

        parse_mode="HTML"

    )


# =========================================================
# COVER PHOTO
# =========================================================

@dp.message(F.photo)
async def cover_received(message: Message):

    user_id = message.from_user.id


    if not is_admin(user_id):

        await message.answer(

            "🔒 Sirf Admin cover upload kar sakta hai."

        )

        return


    if user_id not in pending_videos:

        await message.answer(

            "ℹ️ Pehle /addvideo se video upload karo."

        )

        return


    photo = message.photo[-1]


    pending_videos[user_id][
        "cover_file_id"
    ] = photo.file_id


    await message.answer(

        "🖼️ <b>COVER RECEIVED</b>\n\n"

        "⏳ Video channel mein publish ho rahi hai...\n\n"
        "Please wait...",

        parse_mode="HTML"

    )


    await finalize_admin_video(

        message=message,

        user_id=user_id

    )


# =========================================================
# USE COVER
# =========================================================

@dp.message(Command("usecover"))
async def use_cover_cmd(message: Message):

    user_id = message.from_user.id


    if not is_admin(user_id):

        return


    if user_id not in pending_videos:

        await message.answer(
            "❌ Pehle video bhejo."
        )

        return


    data = pending_videos[user_id]


    if not data.get("cover_file_id"):

        await message.answer(

            "⚠️ Telegram thumbnail available nahi hai.\n\n"

            "Custom cover photo bhejo."

        )

        return


    await message.answer(

        "🖼️ Telegram thumbnail use ki ja rahi hai...\n\n"
        "⏳ Publishing video..."

    )


    await finalize_admin_video(

        message=message,

        user_id=user_id

    )


# =========================================================
# FINALIZE VIDEO
# =========================================================

async def finalize_admin_video(

    message: Message,

    user_id: int

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
            "❌ Video file missing."
        )

        return


    file_size = data.get(
        "file_size",
        0
    )


    mime_type = data.get(
        "mime_type",
        "video/mp4"
    )


    file_name = data.get(
        "file_name",
        "video.mp4"
    )


    cover_file_id = data.get(
        "cover_file_id"
    )


    # =====================================================
    # CREATE WATCH BUTTON
    # =====================================================

    keyboard = watch_keyboard(

        file_id=file_id,

        size_bytes=file_size,

        mime_type=mime_type,

        file_name=file_name

    )


    # =====================================================
    # DOWNLOAD COVER
    # =====================================================

    cover_path = None


    if cover_file_id:

        try:

            temp_dir = tempfile.gettempdir()

            cover_path = os.path.join(

                temp_dir,

                f"night_hub_cover_{user_id}.jpg"

            )


            await bot.download(

                cover_file_id,

                destination=cover_path

            )

        except Exception as error:

            print(
                "Cover download error:",
                repr(error)
            )

            cover_path = None


    # =====================================================
    # PUBLISH TO PRIVATE CHANNEL
    # =====================================================

    channel_message = None


    try:

        if cover_path and os.path.exists(
            cover_path
        ):

            # ---------------------------------------------
            # Send video with custom thumbnail
            # ---------------------------------------------

            channel_message = await mtproto.send_video(

                chat_id=CHANNEL_ID,

                video=file_id,

                thumb=cover_path,

                caption=(

                    "🌙 <b>NIGHT HUB</b>\n\n"

                    f"🎬 <b>{file_name}</b>\n\n"

                    "👉 Watch this video below."

                ),

                supports_streaming=True,

            )

        else:

            channel_message = await mtproto.send_video(

                chat_id=CHANNEL_ID,

                video=file_id,

                caption=(

                    "🌙 <b>NIGHT HUB</b>\n\n"

                    f"🎬 <b>{file_name}</b>\n\n"

                    "👉 Watch this video below."

                ),

                supports_streaming=True,

            )


    except Exception as error:

        print(
            "Channel publish error:",
            repr(error)
        )


        await message.answer(

            "❌ <b>CHANNEL PUBLISH FAILED</b>\n\n"

            f"<code>{error}</code>\n\n"

            "Check:\n"
            "• Bot is Channel Admin\n"
            "• CHANNEL_ID is correct\n"
            "• Bot has Post Messages permission",

            parse_mode="HTML"

        )

        return


    # =====================================================
    # SAVE RUNTIME LIBRARY
    # =====================================================

    if channel_message:

        video_library[channel_message.id] = {

            "file_id":
                file_id,

            "size":
                file_size,

            "mime":
                mime_type,

            "name":
                file_name,

            "message_id":
                channel_message.id,

        }


    # =====================================================
    # REMOVE PENDING
    # =====================================================

    pending_videos.pop(
        user_id,
        None
    )


    # =====================================================
    # DELETE TEMP COVER
    # =====================================================

    if cover_path:

        try:

            if os.path.exists(
                cover_path
            ):

                os.remove(
                    cover_path
                )

        except Exception:

            pass


    # =====================================================
    # SEND RESULT TO ADMIN
    # =====================================================

    try:

        await message.answer_photo(

            photo=cover_file_id,

            caption=(

                "✅ <b>VIDEO PUBLISHED</b>\n\n"

                f"🎬 <b>{file_name}</b>\n\n"

                "📢 Private Channel: ✅\n"
                "🖼️ Cover Photo: ✅\n"
                "👉 WATCH NOW: ✅\n"
                "🎥 Mini App: ✅\n\n"

                "Public users ab /start karke "
                "video dekh sakte hain."

            ),

            reply_markup=keyboard,

            parse_mode="HTML",

            protect_content=True

        )

    except Exception:

        await message.answer(

            "✅ <b>VIDEO PUBLISHED</b>\n\n"

            f"🎬 {file_name}\n\n"

            "📢 Channel: ✅\n"
            "👉 WATCH NOW: ✅",

            reply_markup=keyboard,

            parse_mode="HTML",

            protect_content=True

        )


# =========================================================
# ADMIN CALLBACK: ADD VIDEO
# =========================================================

@dp.callback_query(F.data == "admin_add_video")
async def admin_add_video_callback(
    callback: CallbackQuery
):

    user_id = callback.from_user.id


    if not is_admin(user_id):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return


    pending_videos[user_id] = {

        "file_id": None,

        "file_size": 0,

        "mime_type": "video/mp4",

        "file_name": "video.mp4",

        "cover_file_id": None,

        "cover_path": None,

    }


    await callback.message.edit_text(

        "🎬 <b>ADD VIDEO</b>\n\n"

        "📹 Ab video ya forwarded video bhejo.\n\n"

        "Uske baad:\n"
        "🖼️ Cover Photo\n"
        "👉 WATCH NOW\n"
        "📢 Channel Publish",

        parse_mode="HTML"

    )


    await callback.answer()


# =========================================================
# ADMIN CALLBACK: VIDEOS
# =========================================================

@dp.callback_query(F.data == "admin_videos")
async def admin_videos_callback(
    callback: CallbackQuery
):

    user_id = callback.from_user.id


    if not is_admin(user_id):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return


    try:

        count = 0


        async for channel_message in mtproto.get_chat_history(

            CHANNEL_ID,

            limit=100

        ):

            if channel_message.video:

                count += 1

            elif (

                channel_message.document

                and
                (
                    channel_message.document.mime_type
                    or ""
                ).startswith("video/")

            ):

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

            "Private Channel ko permanent "
            "video library ke रूप में use kiya ja raha hai.\n\n"

            "Public users /start se available "
            "videos dekh sakte hain.",

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
# ADMIN CALLBACK: CHANNEL
# =========================================================

@dp.callback_query(F.data == "admin_channel")
async def admin_channel_callback(
    callback: CallbackQuery
):

    user_id = callback.from_user.id


    if not is_admin(user_id):

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
# ADMIN CALLBACK: USERS
# =========================================================

@dp.callback_query(F.data == "admin_users")
async def admin_users_callback(
    callback: CallbackQuery
):

    user_id = callback.from_user.id


    if not is_admin(user_id):

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

        "👑 Admin:\n"
        "✅ Admin Panel\n"
        "✅ Upload Video\n"
        "✅ Cover Photo\n"
        "✅ Channel Management\n\n"

        "👤 Public User:\n"
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
# ADMIN CALLBACK: REFRESH
# =========================================================

@dp.callback_query(F.data == "admin_refresh")
async def admin_refresh_callback(
    callback: CallbackQuery
):

    user_id = callback.from_user.id


    if not is_admin(user_id):

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
# ADMIN CALLBACK: BACK
# =========================================================

@dp.callback_query(F.data == "admin_back")
async def admin_back_callback(
    callback: CallbackQuery
):

    user_id = callback.from_user.id


    if not is_admin(user_id):

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
# ADMIN CALLBACK: CLOSE
# =========================================================

@dp.callback_query(F.data == "admin_close")
async def admin_close_callback(
    callback: CallbackQuery
):

    user_id = callback.from_user.id


    if not is_admin(user_id):

        await callback.answer(
            "❌ Access Denied",
            show_alert=True
        )

        return


    try:

        await callback.message.delete()

    except Exception as error:

        print(
            "Admin panel close error:",
            repr(error)
        )


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
# MINI APP
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

            text="Invalid or expired watch token",

            status=403

        )


    file_id = data["file_id"]

    file_size = data["size"]

    mime_type = data["mime"]

    file_name = data["name"]


    video_url = (

        f"{request.scheme}://"

        f"{request.host}"

        f"/stream?"

        f"token="

        f"{quote(token, safe='')}"

    )


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

    font-size: 32px;

    box-shadow:
        0 10px 40px
        rgba(108,55,255,0.35);
}}

.title {{
    margin: 12px 0 0;

    font-size: 28px;

    font-weight: 900;

    letter-spacing: 1px;
}}

.subtitle {{
    margin-top: 6px;

    color: #9997a7;

    font-size: 13px;
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
}}

.video-container {{
    width: 100%;

    background: #000;

    border-radius: 16px;

    overflow: hidden;
}}

video {{
    display: block;

    width: 100%;

    max-height: 75vh;

    background: #000;

    object-fit: contain;

    border-radius: 16px;
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

.badges {{
    display: flex;

    gap: 8px;

    margin-top: 7px;

    justify-content: center;

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
}}

.brand {{
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


    <div class="brand">
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
   TELEGRAM WEB APP
===================================================== */

try {{

    if (
        window.Telegram
        &&
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
        "AdsGram init error:",
        error
    );

}}


/* =====================================================
   SHOW ADSGRAM AD
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
   VIDEO START
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

        # =================================================
        # SUFFIX RANGE
        # =================================================

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


    # =====================================================
    # RANGE
    # =====================================================

    range_header = request.headers.get(
        "Range"
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
    # PYROGRAM STREAM
    # =====================================================

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

            limit=chunks_needed

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


    # =====================================================
    # HOME
    # =====================================================

    app.router.add_get(

        "/",

        health

    )


    # =====================================================
    # HEALTH
    # =====================================================

    app.router.add_get(

        "/health",

        health

    )


    # =====================================================
    # WATCH
    # =====================================================

    app.router.add_get(

        "/watch",

        player

    )


    # =====================================================
    # STREAM GET
    # =====================================================

    app.router.add_route(

        "GET",

        "/stream",

        stream_video

    )


    # =====================================================
    # STREAM HEAD
    # =====================================================

    app.router.add_route(

        "HEAD",

        "/stream",

        stream_video

    )


    # =====================================================
    # RUNNER
    # =====================================================

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
        "MTProto: ENABLED"
    )

    print(
        "CHANNEL SYSTEM: ENABLED"
    )

    print(
        "ADMIN PANEL: ENABLED"
    )

    print(
        "ADMIN UPLOAD: ENABLED"
    )

    print(
        "COVER SYSTEM: ENABLED"
    )

    print(
        "WATCH NOW: ENABLED"
    )

    print(
        "MINI APP: ENABLED"
    )

    print(
        "RANGE STREAMING: ENABLED"
    )

    print(
        f"AdsGram: {ADSGRAM_BLOCK_ID}"
    )

    print(
        "=========================================="
    )


# =========================================================
# BOT COMMAND MENUS
# =========================================================

async def setup_commands():

    # =====================================================
    # PUBLIC USERS
    # =====================================================

    await bot.set_my_commands(

        [

            BotCommand(

                command="start",

                description="Watch NIGHT HUB videos"

            ),

            BotCommand(

                command="help",

                description="Help"

            ),

        ],

        scope=BotCommandScopeDefault()

    )


    # =====================================================
    # ADMIN ONLY
    # =====================================================

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

                description="Cancel upload"

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
        "Starting Telegram MTProto client..."
    )


    await mtproto.start()


    print(
        "Telegram MTProto started ✅"
    )


    # =====================================================
    # COMMAND MENU
    # =====================================================

    await setup_commands()


    print(
        "Telegram command menus configured ✅"
    )


    # =====================================================
    # WEB SERVER
    # =====================================================

    await start_web_server()


    # =====================================================
    # BOT
    # =====================================================

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
