import os
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ============================================================
# NIGHT HUB
# ============================================================
# Fresh Bot API version
#
# Features:
# - /start
# - /admin
# - Add Video
# - Direct channel copy
# - WATCH NOW button
# - Mini App URL
# - Video library
# - Delete video
# - Statistics
# - Railway compatible
# - NO SESSION_STRING
# - NO Pyrogram bot session
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
# VALIDATION
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
        "Missing environment variable(s): "
        + ", ".join(missing)
    )


# ============================================================
# CONVERT VALUES
# ============================================================

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError(
        "ADMIN_ID must be a valid number."
    )


try:
    CHANNEL_ID = int(CHANNEL_ID_RAW)
except ValueError:
    raise RuntimeError(
        "CHANNEL_ID must be a valid number."
    )


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
# IN-MEMORY DATABASE
# ============================================================

videos = {}

next_video_id = 1

admin_waiting_for_video = set()


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def make_watch_url(video_id: int) -> str:
    """
    Creates Mini App/watch URL.
    """

    if not WEB_URL:
        return ""

    separator = "&" if "?" in WEB_URL else "?"

    url = (
        f"{WEB_URL}"
        f"{separator}"
        f"video={video_id}"
    )

    if WATCH_SECRET:
        url += (
            f"&secret={WATCH_SECRET}"
        )

    return url


def watch_button(video_id: int):
    """
    WATCH NOW button.
    """

    url = make_watch_url(video_id)

    if not url:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️ WATCH NOW",
                    url=url
                )
            ]
        ]
    )


def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📤 ADD VIDEO",
                    callback_data="add_video"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📚 VIDEO LIST",
                    callback_data="video_list"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🗑 DELETE VIDEO",
                    callback_data="delete_menu"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📊 STATISTICS",
                    callback_data="statistics"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📢 CHANNEL",
                    callback_data="channel_info"
                )
            ]

        ]
    )


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start_command(message: Message):

    if is_admin(
        message.from_user.id
    ):

        await message.answer(

            "🌙 <b>NIGHT HUB</b>\n\n"

            "👑 Welcome Admin.\n\n"

            f"🎬 Videos: <b>{len(videos)}</b>\n"
            "📢 Channel: ✅\n"
            "▶️ Watch Now: ✅\n\n"

            "Use /admin to open the control panel."

        )

        return


    if not videos:

        await message.answer(

            "🌙 <b>WELCOME TO NIGHT HUB</b>\n\n"

            "🎬 Abhi koi video available nahi hai."

        )

        return


    buttons = []

    for video_id, data in videos.items():

        buttons.append([

            InlineKeyboardButton(
                text=f"🎬 {data['title']}",
                callback_data=f"watch:{video_id}"
            )

        ])


    await message.answer(

        "🌙 <b>NIGHT HUB</b>\n\n"
        "🎬 Available Videos:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )

    )


# ============================================================
# ADMIN
# ============================================================

@dp.message(Command("admin"))
async def admin_command(message: Message):

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "❌ Access denied."
        )

        return


    await message.answer(

        "👑 <b>NIGHT HUB ADMIN PANEL</b>\n\n"

        "Select an option:",

        reply_markup=admin_keyboard()

    )


# ============================================================
# ADD VIDEO BUTTON
# ============================================================

@dp.callback_query(F.data == "add_video")
async def add_video_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return


    admin_waiting_for_video.add(
        callback.from_user.id
    )


    await callback.message.answer(

        "📤 <b>ADD VIDEO</b>\n\n"

        "Ab apni video bhejo.\n\n"

        "Video receive hone ke baad:\n"
        "1️⃣ Video channel mein copy hogi\n"
        "2️⃣ WATCH NOW button add hoga\n"
        "3️⃣ Mini App URL attach hoga\n\n"

        "⚠️ Bot ko channel mein administrator "
        "permission dena zaroori hai."

    )


    await callback.answer()


# ============================================================
# RECEIVE VIDEO
# ============================================================

@dp.message(F.video)
async def receive_video(
    message: Message
):

    global next_video_id

    user_id = message.from_user.id

    if not is_admin(user_id):

        await message.answer(
            "❌ Sirf admin video upload kar sakta hai."
        )

        return


    if user_id not in admin_waiting_for_video:

        await message.answer(

            "ℹ️ Pehle /admin → "
            "<b>ADD VIDEO</b> select karo."

        )

        return


    video = message.video

    if not video:

        return


    video_id = next_video_id

    next_video_id += 1


    # --------------------------------------------------------
    # VIDEO TITLE
    # --------------------------------------------------------

    if message.caption:

        title = message.caption.strip()

    else:

        title = (
            f"Night Hub Video {video_id}"
        )


    if len(title) > 80:

        title = title[:77] + "..."


    # --------------------------------------------------------
    # SAVE DATA
    # --------------------------------------------------------

    videos[video_id] = {

        "id": video_id,

        "title": title,

        "file_id": video.file_id,

        "source_message_id": (
            message.message_id
        ),

        "source_chat_id": (
            message.chat.id
        ),

        "file_size": (
            video.file_size or 0
        ),

        "duration": (
            video.duration or 0
        ),

        "width": (
            video.width or 0
        ),

        "height": (
            video.height or 0
        ),

        "channel_message_id": None,

    }


    # --------------------------------------------------------
    # WATCH BUTTON
    # --------------------------------------------------------

    keyboard = watch_button(
        video_id
    )


    try:

        await message.answer(

            "⏳ <b>UPLOADING VIDEO...</b>\n\n"
            f"🎬 {title}\n\n"
            "📢 Publishing to channel..."

        )


        # ----------------------------------------------------
        # DIRECT CHANNEL COPY
        # ----------------------------------------------------
        #
        # IMPORTANT:
        #
        # The video is copied by Telegram directly.
        # We don't use Pyrogram.
        # We don't use SESSION_STRING.
        #
        # reply_markup attaches WATCH NOW directly
        # to the channel post.
        # ----------------------------------------------------

        copied = await bot.copy_message(

            chat_id=CHANNEL_ID,

            from_chat_id=message.chat.id,

            message_id=message.message_id,

            reply_markup=keyboard

        )


        videos[video_id][
            "channel_message_id"
        ] = copied.message_id


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        await message.answer(

            "✅ <b>VIDEO UPLOADED SUCCESSFULLY</b>\n\n"

            f"🎬 <b>{title}</b>\n\n"

            "📢 Channel: ✅\n"
            "▶️ WATCH NOW button: "
            f"{'✅' if keyboard else '❌'}\n"
            "🔗 Mini App URL: "
            f"{'✅' if WEB_URL else '❌'}\n\n"

            f"🆔 Video ID: "
            f"<code>{video_id}</code>\n"

            f"📌 Channel Message ID: "
            f"<code>{copied.message_id}</code>"

        )


        logger.info(
            "Video %s uploaded to channel. "
            "Channel message ID=%s",
            video_id,
            copied.message_id
        )


    except Exception as e:

        logger.exception(
            "Channel upload failed: %s",
            e
        )


        videos.pop(
            video_id,
            None
        )


        await message.answer(

            "❌ <b>VIDEO PROCESS FAILED</b>\n\n"

            f"<code>{str(e)[:3500]}</code>\n\n"

            "Check:\n"
            "• Bot channel admin hai?\n"
            "• Post Messages permission hai?\n"
            "• CHANNEL_ID correct hai?\n"
            "• WEB_URL correct hai?"

        )


    finally:

        admin_waiting_for_video.discard(
            user_id
        )


# ============================================================
# WATCH CALLBACK
# ============================================================

@dp.callback_query(
    F.data.startswith("watch:")
)
async def watch_callback(
    callback: CallbackQuery
):

    try:

        video_id = int(
            callback.data.split(":")[1]
        )

    except Exception:

        await callback.answer(
            "Invalid video.",
            show_alert=True
        )

        return


    data = videos.get(
        video_id
    )


    if not data:

        await callback.answer(
            "Video not found.",
            show_alert=True
        )

        return


    url = make_watch_url(
        video_id
    )


    if url:

        await callback.message.answer(

            "🎬 <b>NIGHT HUB</b>\n\n"

            f"📺 <b>{data['title']}</b>\n\n"

            "👇 Watch karne ke liye button press karo.",

            reply_markup=watch_button(
                video_id
            )

        )

    else:

        await callback.message.answer(

            "⚠️ WEB_URL configured nahi hai.\n\n"
            "Railway Variables mein WEB_URL add karo."

        )


    await callback.answer()


# ============================================================
# VIDEO LIST
# ============================================================

@dp.callback_query(
    F.data == "video_list"
)
async def video_list_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return


    if not videos:

        await callback.message.answer(
            "📚 <b>VIDEO LIST</b>\n\n"
            "No videos."
        )

        await callback.answer()

        return


    text = (
        "📚 <b>NIGHT HUB VIDEO LIST</b>\n\n"
    )


    for video_id, data in videos.items():

        text += (

            f"🆔 <b>{video_id}</b>\n"
            f"🎬 {data['title']}\n"
            f"📢 Channel Message: "
            f"{data.get('channel_message_id')}\n\n"

        )


    await callback.message.answer(
        text
    )

    await callback.answer()


# ============================================================
# DELETE MENU
# ============================================================

@dp.callback_query(
    F.data == "delete_menu"
)
async def delete_menu_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return


    if not videos:

        await callback.message.answer(
            "🗑 No videos available."
        )

        await callback.answer()

        return


    rows = []


    for video_id, data in videos.items():

        rows.append([

            InlineKeyboardButton(

                text=(
                    f"❌ {data['title'][:30]}"
                ),

                callback_data=(
                    f"delete:{video_id}"
                )

            )

        ])


    await callback.message.answer(

        "🗑 <b>DELETE VIDEO</b>\n\n"
        "Video select karo:",

        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        )

    )


    await callback.answer()


# ============================================================
# DELETE VIDEO
# ============================================================

@dp.callback_query(
    F.data.startswith("delete:")
)
async def delete_video_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return


    try:

        video_id = int(
            callback.data.split(":")[1]
        )

    except Exception:

        await callback.answer(
            "Invalid ID.",
            show_alert=True
        )

        return


    data = videos.get(
        video_id
    )


    if not data:

        await callback.answer(
            "Video not found.",
            show_alert=True
        )

        return


    title = data["title"]


    # --------------------------------------------------------
    # DELETE CHANNEL MESSAGE
    # --------------------------------------------------------

    channel_message_id = data.get(
        "channel_message_id"
    )


    if channel_message_id:

        try:

            await bot.delete_message(

                chat_id=CHANNEL_ID,

                message_id=channel_message_id

            )

        except Exception as e:

            logger.warning(
                "Could not delete channel message: %s",
                e
            )


    # --------------------------------------------------------
    # DELETE DATABASE ENTRY
    # --------------------------------------------------------

    del videos[
        video_id
    ]


    await callback.message.answer(

        "✅ <b>VIDEO DELETED</b>\n\n"

        f"🎬 {title}"

    )


    await callback.answer(
        "Deleted."
    )


# ============================================================
# STATISTICS
# ============================================================

@dp.callback_query(
    F.data == "statistics"
)
async def statistics_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return


    await callback.message.answer(

        "📊 <b>NIGHT HUB STATISTICS</b>\n\n"

        f"🎬 Total Videos: "
        f"<b>{len(videos)}</b>\n\n"

        f"👑 Admin ID: "
        f"<code>{ADMIN_ID}</code>\n"

        f"📢 Channel ID: "
        f"<code>{CHANNEL_ID}</code>\n\n"

        f"▶️ Watch URL: "
        f"{'✅ Configured' if WEB_URL else '❌ Missing'}"

    )


    await callback.answer()


# ============================================================
# CHANNEL INFO
# ============================================================

@dp.callback_query(
    F.data == "channel_info"
)
async def channel_info_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Access denied.",
            show_alert=True
        )

        return


    await callback.message.answer(

        "📢 <b>CHANNEL SETTINGS</b>\n\n"

        f"Channel ID:\n"
        f"<code>{CHANNEL_ID}</code>\n\n"

        "Bot must be administrator:\n"
        "✅ Post Messages\n"
        "✅ Edit Messages\n"
        "✅ Delete Messages\n\n"

        f"WEB_URL:\n"
        f"<code>{WEB_URL or 'NOT SET'}</code>"

    )


    await callback.answer()


# ============================================================
# WEB SERVER
# ============================================================

async def health_handler(
    request
):

    return web.json_response({

        "status": "online",

        "name": "NIGHT HUB",

        "videos": len(videos),

        "watch_now": bool(
            WEB_URL
        ),

        "session_string": False,

    })


async def home_handler(
    request
):

    html = """

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
    background: #050505;
    color: white;
    font-family: Arial, sans-serif;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.box {
    background: #111;
    border: 1px solid #292929;
    border-radius: 24px;
    padding: 35px;
    text-align: center;
}

.logo {
    font-size: 60px;
}

h1 {
    margin: 10px 0;
}

p {
    color: #888;
}

</style>

</head>

<body>

<div class="box">

<div class="logo">
🌙
</div>

<h1>NIGHT HUB</h1>

<p>Online Video Platform</p>

</div>

</body>

</html>

"""


    return web.Response(
        text=html,
        content_type="text/html"
    )


async def start_web_server():

    app = web.Application()


    app.router.add_get(
        "/",
        home_handler
    )


    app.router.add_get(
        "/health",
        health_handler
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


    logger.info(
        "Web server started on port %s",
        PORT
    )


    return runner


# ============================================================
# MAIN
# ============================================================

async def main():

    logger.info(
        "======================================"
    )

    logger.info(
        "       NIGHT HUB STARTING"
    )

    logger.info(
        "======================================"
    )


    # --------------------------------------------------------
    # TEST BOT
    # --------------------------------------------------------

    me = await bot.get_me()


    logger.info(
        "Bot connected: @%s",
        me.username
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
        "Watch URL: %s",
        WEB_URL or "NOT SET"
    )


    logger.info(
        "SESSION_STRING: NOT USED"
    )


    # --------------------------------------------------------
    # TEST CHANNEL ACCESS
    # --------------------------------------------------------

    try:

        chat = await bot.get_chat(
            CHANNEL_ID
        )

        logger.info(
            "Channel connected: %s",
            chat.title
        )

    except Exception as e:

        logger.error(
            "CHANNEL ACCESS ERROR: %s",
            e
        )


    # --------------------------------------------------------
    # WEB SERVER
    # --------------------------------------------------------

    runner = await start_web_server()


    # --------------------------------------------------------
    # POLLING
    # --------------------------------------------------------

    try:

        await bot.delete_webhook(
            drop_pending_updates=True
        )


        logger.info(
            "NIGHT HUB polling started."
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

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "NIGHT HUB stopped."
        )

    except Exception as e:

        logger.exception(
            "FATAL ERROR: %s",
            e
        )
