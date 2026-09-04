import os
import asyncio
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


# ============================================================
# NIGHT HUB
# Telegram Video Bot
# Bot API Based
# SESSION_STRING NOT REQUIRED
# ============================================================


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("NIGHT_HUB")


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()
CHANNEL_ID_RAW = os.getenv("CHANNEL_ID", "").strip()

WEB_URL = os.getenv("WEB_URL", "").strip()
WATCH_SECRET = os.getenv("WATCH_SECRET", "").strip()

PORT_RAW = os.getenv("PORT", "8080").strip()


# ============================================================
# REQUIRED VARIABLES
# ============================================================

missing = []

if not BOT_TOKEN:
    missing.append("BOT_TOKEN")

if not ADMIN_ID_RAW:
    missing.append("ADMIN_ID")

if not CHANNEL_ID_RAW:
    missing.append("CHANNEL_ID")

if missing:
    raise RuntimeError(
        "Missing environment variable(s): " + ", ".join(missing)
    )


# ============================================================
# CONVERT VALUES
# ============================================================

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError("ADMIN_ID must be a number")


try:
    CHANNEL_ID = int(CHANNEL_ID_RAW)
except ValueError:
    raise RuntimeError("CHANNEL_ID must be a number")


try:
    PORT = int(PORT_RAW)
except ValueError:
    PORT = 8080


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


# ============================================================
# MEMORY
# ============================================================

# Temporary state for admin
admin_state = {}

# Stored video messages
videos = {}

# Simple counter
video_counter = 0


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def get_start_text():
    if not videos:
        return (
            "🎬 <b>WELCOME TO NIGHT HUB</b>\n\n"
            "Abhi koi video available nahi hai.\n\n"
            "New videos upload hone ke baad yahan available hongi."
        )

    return (
        "🎬 <b>WELCOME TO NIGHT HUB</b>\n\n"
        f"📺 Available Videos: <b>{len(videos)}</b>\n\n"
        "Neeche video select karein."
    )


def video_keyboard():
    rows = []

    for vid, data in videos.items():
        title = data.get("title", f"Video {vid}")

        if len(title) > 30:
            title = title[:27] + "..."

        rows.append([
            InlineKeyboardButton(
                text=f"🎬 {title}",
                callback_data=f"watch:{vid}"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 ADD VIDEO",
                    callback_data="admin_add"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 VIDEO LIST",
                    callback_data="admin_list"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 DELETE VIDEO",
                    callback_data="admin_delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 STATISTICS",
                    callback_data="admin_stats"
                )
            ]
        ]
    )


def delete_keyboard():
    rows = []

    for vid, data in videos.items():
        title = data.get("title", f"Video {vid}")

        if len(title) > 25:
            title = title[:22] + "..."

        rows.append([
            InlineKeyboardButton(
                text=f"❌ {title}",
                callback_data=f"delete:{vid}"
            )
        ])

    if not rows:
        rows.append([
            InlineKeyboardButton(
                text="No videos",
                callback_data="nothing"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start_handler(message: Message):

    try:
        await message.answer(
            get_start_text(),
            reply_markup=video_keyboard() if videos else None
        )

    except Exception as e:
        logger.exception("Start error: %s", e)


# ============================================================
# ADMIN COMMAND
# ============================================================

@dp.message(Command("admin"))
async def admin_handler(message: Message):

    if not is_admin(message.from_user.id):
        await message.answer(
            "❌ <b>Access Denied</b>\n\n"
            "Aap admin nahi hain."
        )
        return

    await message.answer(
        "👑 <b>NIGHT HUB ADMIN PANEL</b>\n\n"
        "Control Panel:",
        reply_markup=admin_keyboard()
    )


# ============================================================
# ADMIN PANEL CALLBACK
# ============================================================

@dp.callback_query(F.data == "admin_add")
async def admin_add_callback(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied",
            show_alert=True
        )
        return

    admin_state[callback.from_user.id] = "waiting_video"

    await callback.message.answer(
        "📤 <b>ADD VIDEO</b>\n\n"
        "Ab video bhejo.\n\n"
        "Multiple videos ek ke baad ek bhej sakte ho."
    )

    await callback.answer()


# ============================================================
# ADMIN LIST
# ============================================================

@dp.callback_query(F.data == "admin_list")
async def admin_list_callback(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied",
            show_alert=True
        )
        return

    if not videos:
        await callback.message.answer(
            "📋 <b>VIDEO LIST</b>\n\n"
            "Abhi koi video nahi hai."
        )
        await callback.answer()
        return

    text = "📋 <b>NIGHT HUB VIDEO LIST</b>\n\n"

    for vid, data in videos.items():

        title = data.get(
            "title",
            f"Video {vid}"
        )

        text += (
            f"🎬 <b>{vid}</b> — "
            f"{title}\n"
        )

    await callback.message.answer(text)
    await callback.answer()


# ============================================================
# ADMIN DELETE
# ============================================================

@dp.callback_query(F.data == "admin_delete")
async def admin_delete_callback(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied",
            show_alert=True
        )
        return

    await callback.message.answer(
        "🗑 <b>DELETE VIDEO</b>\n\n"
        "Jis video ko delete karna hai select karo:",
        reply_markup=delete_keyboard()
    )

    await callback.answer()


# ============================================================
# DELETE VIDEO
# ============================================================

@dp.callback_query(F.data.startswith("delete:"))
async def delete_video_callback(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied",
            show_alert=True
        )
        return

    try:
        vid = int(
            callback.data.split(":")[1]
        )
    except Exception:
        await callback.answer(
            "Invalid video",
            show_alert=True
        )
        return

    if vid not in videos:
        await callback.answer(
            "Video not found",
            show_alert=True
        )
        return

    title = videos[vid].get(
        "title",
        f"Video {vid}"
    )

    del videos[vid]

    await callback.message.answer(
        "✅ <b>VIDEO DELETED</b>\n\n"
        f"🎬 {title}"
    )

    await callback.answer("Deleted")


# ============================================================
# ADMIN STATISTICS
# ============================================================

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "Access denied",
            show_alert=True
        )
        return

    await callback.message.answer(
        "📊 <b>NIGHT HUB STATISTICS</b>\n\n"
        f"🎬 Total Videos: <b>{len(videos)}</b>\n"
        f"👑 Admin ID: <code>{ADMIN_ID}</code>\n"
        f"📢 Channel ID: <code>{CHANNEL_ID}</code>"
    )

    await callback.answer()


# ============================================================
# RECEIVE VIDEO
# ============================================================

@dp.message(F.video)
async def video_handler(message: Message):

    global video_counter

    if not is_admin(message.from_user.id):
        await message.answer(
            "❌ Sirf admin video upload kar sakta hai."
        )
        return

    state = admin_state.get(
        message.from_user.id
    )

    if state != "waiting_video":
        await message.answer(
            "ℹ️ Pehle /admin → ADD VIDEO select karo."
        )
        return

    video = message.video

    if not video:
        return

    video_counter += 1

    video_id = video_counter

    title = (
        message.caption.strip()
        if message.caption
        else f"Night Hub Video {video_id}"
    )

    # --------------------------------------------------------
    # SAVE TELEGRAM FILE_ID
    # --------------------------------------------------------

    videos[video_id] = {
        "title": title,
        "file_id": video.file_id,
        "message_id": message.message_id,
        "chat_id": message.chat.id,
        "duration": video.duration,
        "width": video.width,
        "height": video.height,
        "file_size": video.file_size,
    }

    # --------------------------------------------------------
    # DIRECT CHANNEL COPY
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # We use copy_message instead of downloading the file.
    #
    # This avoids:
    # USER_IS_BOT
    # SESSION_STRING
    # getFile download limitation
    #
    # Telegram keeps the original video content/thumbnail.
    # --------------------------------------------------------

    try:

        copied = await bot.copy_message(
            chat_id=CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        videos[video_id]["channel_message_id"] = (
            copied.message_id
        )

        await message.answer(
            "✅ <b>VIDEO UPLOADED</b>\n\n"
            f"🎬 <b>{title}</b>\n\n"
            "📢 Channel upload successful.\n"
            "🖼️ Telegram video thumbnail preserved.\n\n"
            f"🆔 Video ID: <code>{video_id}</code>"
        )

    except TelegramForbiddenError:

        videos.pop(video_id, None)

        await message.answer(
            "❌ <b>CHANNEL PERMISSION ERROR</b>\n\n"
            "Bot ko channel me administrator banao.\n"
            "Aur <b>Post Messages</b> permission enable karo."
        )

    except TelegramBadRequest as e:

        videos.pop(video_id, None)

        await message.answer(
            "❌ <b>VIDEO UPLOAD FAILED</b>\n\n"
            f"<code>{str(e)}</code>"
        )

    except Exception as e:

        videos.pop(video_id, None)

        logger.exception(
            "Channel upload error: %s",
            e
        )

        await message.answer(
            "❌ <b>VIDEO PROCESS FAILED</b>\n\n"
            f"<code>{str(e)}</code>"
        )


# ============================================================
# DOCUMENT VIDEO SUPPORT
# ============================================================

@dp.message(F.document)
async def document_handler(message: Message):

    if not is_admin(message.from_user.id):
        return

    document = message.document

    if not document:
        return

    filename = (
        document.file_name or ""
    ).lower()

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
        ".flv"
    )

    if not filename.endswith(video_extensions):
        return

    await message.answer(
        "⚠️ <b>VIDEO DOCUMENT DETECTED</b>\n\n"
        "Best result ke liye Telegram me video ko "
        "<b>Video</b> ke form me upload karo, "
        "Document ke form me nahi."
    )


# ============================================================
# VIDEO WATCH CALLBACK
# ============================================================

@dp.callback_query(F.data.startswith("watch:"))
async def watch_callback(callback: CallbackQuery):

    try:
        vid = int(
            callback.data.split(":")[1]
        )
    except Exception:
        await callback.answer(
            "Invalid video",
            show_alert=True
        )
        return

    if vid not in videos:
        await callback.answer(
            "Video unavailable",
            show_alert=True
        )
        return

    data = videos[vid]

    title = data.get(
        "title",
        f"Video {vid}"
    )

    # --------------------------------------------------------
    # MINI APP WATCH URL
    # --------------------------------------------------------

    if WEB_URL:

        separator = (
            "&"
            if "?" in WEB_URL
            else "?"
        )

        watch_url = (
            f"{WEB_URL}"
            f"{separator}"
            f"video={vid}"
        )

        if WATCH_SECRET:
            watch_url += (
                f"&secret={WATCH_SECRET}"
            )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="▶️ WATCH VIDEO",
                        url=watch_url
                    )
                ]
            ]
        )

        await callback.message.answer(
            "🎬 <b>NIGHT HUB</b>\n\n"
            f"📺 <b>{title}</b>\n\n"
            "👇 Video watch karne ke liye button press karo.",
            reply_markup=keyboard
        )

    else:

        # ----------------------------------------------------
        # FALLBACK
        # ----------------------------------------------------

        try:

            await bot.copy_message(
                chat_id=callback.from_user.id,
                from_chat_id=CHANNEL_ID,
                message_id=data.get(
                    "channel_message_id"
                )
            )

        except Exception as e:

            logger.exception(
                "Watch fallback error: %s",
                e
            )

            await callback.message.answer(
                "❌ Video abhi available nahi hai."
            )

    await callback.answer()


# ============================================================
# NOTHING CALLBACK
# ============================================================

@dp.callback_query(F.data == "nothing")
async def nothing_callback(callback: CallbackQuery):

    await callback.answer(
        "Abhi koi video nahi hai.",
        show_alert=True
    )


# ============================================================
# UNKNOWN TEXT
# ============================================================

@dp.message()
async def unknown_handler(message: Message):

    if message.text == "/start":
        return

    if message.from_user and is_admin(
        message.from_user.id
    ):

        if message.text:

            await message.answer(
                "👑 <b>NIGHT HUB ADMIN</b>\n\n"
                "Commands:\n"
                "/admin — Admin Panel"
            )

    else:

        await message.answer(
            get_start_text(),
            reply_markup=(
                video_keyboard()
                if videos
                else None
            )
        )


# ============================================================
# HEALTH CHECK SERVER
# ============================================================

async def health_handler(request):
    return web.Response(
        text="NIGHT HUB is running"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        health_handler
    )

    app.router.add_get(
        "/health",
        health_handler
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    logger.info(
        "Health server running on port %s",
        PORT
    )

    return runner


# ============================================================
# MAIN
# ============================================================

async def main():

    logger.info(
        "========================================"
    )

    logger.info(
        "       NIGHT HUB BOT STARTING"
    )

    logger.info(
        "========================================"
    )

    logger.info(
        "Admin ID: %s",
        ADMIN_ID
    )

    logger.info(
        "Channel ID: %s",
        CHANNEL_ID
    )

    logger.info(
        "Web URL: %s",
        WEB_URL or "Not configured"
    )

    logger.info(
        "SESSION_STRING: NOT USED"
    )

    # --------------------------------------------------------
    # WEB SERVER
    # --------------------------------------------------------

    runner = await start_web_server()

    # --------------------------------------------------------
    # BOT
    # --------------------------------------------------------

    try:

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        logger.info(
            "NIGHT HUB bot polling started"
        )

        await dp.start_polling(
            bot
        )

    finally:

        await runner.cleanup()

        await bot.session.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info(
            "NIGHT HUB stopped"
        )

    except Exception as e:

        logger.exception(
            "Fatal error: %s",
            e
        )
