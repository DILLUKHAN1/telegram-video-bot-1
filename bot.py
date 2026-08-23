import os
import asyncio
from io import BytesIO
from urllib.parse import quote

from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    BufferedInputFile,
)

from pyrogram import Client


# =========================================================
# SETTINGS
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

PORT = int(os.getenv("PORT", "8080"))

WEB_URL = os.getenv("WEB_URL")

ADSGRAM_BLOCK_ID = os.getenv(
    "ADSGRAM_BLOCK_ID",
    "int-44048"
)


# =========================================================
# STREAM SETTINGS
# =========================================================

CHUNK_SIZE = 1024 * 1024

MAX_RANGE_REQUEST = (
    16 * 1024 * 1024
)

MAX_FILE_SIZE = (
    2 * 1024 * 1024 * 1024
)


# =========================================================
# ENVIRONMENT CHECK
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
# AIROGRAM
# =========================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# =========================================================
# PYROGRAM MTProto
# =========================================================

mtproto = Client(
    "night_videos_mtproto",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    no_updates=True,
    in_memory=True,
)


# =========================================================
# CREATE PLAY URL
# =========================================================

def make_play_url(
    file_id: str,
    size_bytes: int = 0,
    mime_type: str = "video/mp4",
    file_name: str = "video.mp4",
) -> str:

    params = (
        f"file_id={quote(file_id, safe='')}"
        f"&size={int(size_bytes)}"
        f"&mime={quote(mime_type, safe='')}"
        f"&name={quote(file_name, safe='')}"
    )

    return (
        f"{WEB_URL.rstrip('/')}"
        f"/watch?{params}"
    )


# =========================================================
# WATCH NOW BUTTON
# =========================================================

def watch_keyboard(
    file_id: str,
    size_bytes: int,
    mime_type: str,
    file_name: str,
) -> InlineKeyboardMarkup:

    play_url = make_play_url(
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
                        url=play_url
                    ),
                )
            ]
        ]
    )


# =========================================================
# GET THUMBNAIL AS PHOTO
# =========================================================

async def download_thumbnail(
    thumbnail_file_id: str,
):
    """
    Downloads only Telegram thumbnail.
    It does NOT download the full video.
    """

    try:

        telegram_file = await bot.get_file(
            thumbnail_file_id
        )

        buffer = BytesIO()

        await bot.download_file(
            telegram_file.file_path,
            buffer,
        )

        buffer.seek(0)

        return BufferedInputFile(
            buffer.read(),
            filename="cover.jpg",
        )

    except Exception as error:

        print(
            "THUMBNAIL DOWNLOAD ERROR:",
            repr(error)
        )

        return None


# =========================================================
# SEND COVER + WATCH NOW
# =========================================================

async def send_watch_button(
    message: Message,
    file_id: str,
    size_bytes: int = 0,
    mime_type: str = "video/mp4",
    file_name: str = "video.mp4",
    thumbnail_file_id: str | None = None,
):

    # -----------------------------------------------------
    # FILE SIZE CHECK
    # -----------------------------------------------------

    if size_bytes > MAX_FILE_SIZE:

        await message.answer(
            "❌ Ye file 2 GB se badi hai."
        )

        return


    # -----------------------------------------------------
    # KEYBOARD
    # -----------------------------------------------------

    keyboard = watch_keyboard(
        file_id=file_id,
        size_bytes=size_bytes,
        mime_type=mime_type,
        file_name=file_name,
    )


    # -----------------------------------------------------
    # COVER
    # -----------------------------------------------------

    if thumbnail_file_id:

        cover = await download_thumbnail(
            thumbnail_file_id
        )

        if cover:

            try:

                await message.answer_photo(
                    photo=cover,
                    reply_markup=keyboard,
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

    try:

        await message.reply(
            "\u2063",
            reply_markup=keyboard,
        )

    except Exception as error:

        print(
            "WATCH BUTTON ERROR:",
            repr(error)
        )

        await message.answer(
            "👉 𝐖𝐀𝐓𝐂𝐇 𝐍𝐎𝐖 👈",
            reply_markup=keyboard,
        )


# =========================================================
# START
# =========================================================

@dp.message(CommandStart())
async def start(
    message: Message
):

    await message.answer(
        "🎬 NIGHT VIDEOS\n\n"
        "Video bhejo ya forward karo.\n\n"
        "🖼️ Video ka cover milega\n"
        "👇 Uske niche WATCH NOW button hoga.\n\n"
        "👉 WATCH NOW dabao\n"
        "📺 Advertisement dekho\n"
        "▶️ Ad complete hone ke baad video automatically play hoga."
    )


# =========================================================
# HELP
# =========================================================

@dp.message(Command("help"))
async def help_cmd(
    message: Message
):

    await message.answer(
        "📌 NIGHT VIDEOS\n\n"
        "1️⃣ Video bhejo ya forward karo\n"
        "2️⃣ Cover photo ke niche WATCH NOW dabao\n"
        "3️⃣ Advertisement show hoga\n"
        "4️⃣ Advertisement complete hone ke baad video play hoga\n"
        "5️⃣ Large video ke liye MTProto streaming\n"
        "6️⃣ Range / Seek supported\n"
        "7️⃣ Maximum configured size: 2 GB"
    )


# =========================================================
# VIDEO RECEIVED
# =========================================================

@dp.message(F.video)
async def video_received(
    message: Message
):

    video = message.video

    thumbnail_file_id = None

    if video.thumbnail:

        thumbnail_file_id = (
            video.thumbnail.file_id
        )

    await send_watch_button(
        message=message,
        file_id=video.file_id,
        size_bytes=(
            video.file_size or 0
        ),
        mime_type=(
            video.mime_type
            or "video/mp4"
        ),
        file_name=(
            video.file_name
            or "video.mp4"
        ),
        thumbnail_file_id=(
            thumbnail_file_id
        ),
    )


# =========================================================
# DOCUMENT / FORWARDED VIDEO FILE
# =========================================================

@dp.message(F.document)
async def document_received(
    message: Message
):

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
        ".m2ts",
        ".mts",
    )


    is_video = (
        mime.startswith("video/")
        or filename_lower.endswith(
            video_extensions
        )
    )


    if not is_video:

        await message.answer(
            "📄 Ye video file nahi hai."
        )

        return


    thumbnail_file_id = None

    if document.thumbnail:

        thumbnail_file_id = (
            document.thumbnail.file_id
        )


    await send_watch_button(
        message=message,
        file_id=document.file_id,
        size_bytes=(
            document.file_size or 0
        ),
        mime_type=(
            mime
            or "video/mp4"
        ),
        file_name=filename,
        thumbnail_file_id=(
            thumbnail_file_id
        ),
    )


# =========================================================
# HEALTH
# =========================================================

async def health(
    request: web.Request
):

    return web.Response(
        text="NIGHT VIDEOS is running ✅"
    )


# =========================================================
# PARSE HTTP RANGE
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
            1,
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

        # ---------------------------------------------
        # SUFFIX RANGE
        # bytes=-500000
        # ---------------------------------------------

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


            # -----------------------------------------
            # OPEN ENDED RANGE
            # bytes=500000-
            # -----------------------------------------

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


        # ---------------------------------------------
        # LIMIT HTTP RESPONSE RANGE
        # ---------------------------------------------

        maximum_end = (
            start
            + MAX_RANGE_REQUEST
            - 1
        )


        if end > maximum_end:

            end = maximum_end


        return start, end


    except ValueError:

        return None


# =========================================================
# MINI APP PLAYER
# =========================================================

async def player(
    request: web.Request
):

    file_id = request.query.get(
        "file_id"
    )


    if not file_id:

        return web.Response(
            text="Missing file_id",
            status=400,
        )


    try:

        size = int(
            request.query.get(
                "size",
                "0",
            )
        )

    except ValueError:

        size = 0


    if size <= 0:

        return web.Response(
            text="Invalid file size",
            status=400,
        )


    if size > MAX_FILE_SIZE:

        return web.Response(
            text="File is larger than 2 GB",
            status=413,
        )


    mime_type = request.query.get(
        "mime",
        "video/mp4",
    )


    file_name = request.query.get(
        "name",
        "video.mp4",
    )


    # =====================================================
    # STREAM URL
    # =====================================================

    stream_url = (
        f"{request.scheme}://"
        f"{request.host}"
        f"/stream?"
        f"file_id="
        f"{quote(file_id, safe='')}"
        f"&size={size}"
        f"&mime="
        f"{quote(mime_type, safe='')}"
        f"&name="
        f"{quote(file_name, safe='')}"
    )


    # =====================================================
    # LUXURY MINI APP
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
             viewport-fit=cover"
>

<meta
    name="theme-color"
    content="#08080f"
>

<title>NIGHT HUB</title>


<script src="https://telegram.org/js/telegram-web-app.js">
</script>


<script src="https://sad.adsgram.ai/js/sad.min.js">
</script>


<style>

* {{
    box-sizing: border-box;
    -webkit-tap-highlight-color: transparent;
}}


html,
body {{
    margin: 0;
    padding: 0;

    width: 100%;
    min-height: 100%;

    background:
        radial-gradient(
            circle at 15% 0%,
            #47206d 0%,
            transparent 38%
        ),

        radial-gradient(
            circle at 90% 15%,
            #171d58 0%,
            transparent 35%
        ),

        linear-gradient(
            180deg,
            #08080f 0%,
            #030306 100%
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
        calc(20px + env(safe-area-inset-top))
        14px
        calc(30px + env(safe-area-inset-bottom));
}}


.logo {{
    width: 78px;
    height: 78px;

    margin-top: 8px;

    border-radius: 50%;

    display: flex;
    align-items: center;
    justify-content: center;

    font-size: 38px;

    background:
        linear-gradient(
            135deg,
            #a32cff,
            #4b00ff
        );

    box-shadow:
        0 0 45px
        rgba(132,45,255,.48),

        inset
        0 1px 1px
        rgba(255,255,255,.25);
}}


.title {{
    margin: 16px 0 0;

    font-size: 30px;
    line-height: 1;

    font-weight: 900;

    letter-spacing: 1px;

    text-align: center;
}}


.subtitle {{
    margin-top: 9px;

    color: #9999a9;

    font-size: 14px;

    font-weight: 600;

    text-align: center;
}}


.player-card {{
    width: 100%;
    max-width: 1000px;

    margin-top: 28px;

    padding: 8px;

    border-radius: 24px;

    background:
        linear-gradient(
            145deg,
            rgba(255,255,255,.10),
            rgba(255,255,255,.025)
        );

    border:
        1px solid
        rgba(255,255,255,.12);

    box-shadow:
        0 30px 80px
        rgba(0,0,0,.55);
}}


video {{
    display: block;

    width: 100%;

    max-height: 72vh;

    min-height: 220px;

    background: #000;

    border-radius: 18px;

    object-fit: contain;
}}


.loading-screen {{
    width: 100%;

    min-height: 220px;

    border-radius: 18px;

    display: flex;

    align-items: center;

    justify-content: center;

    flex-direction: column;

    background:
        radial-gradient(
            circle,
            #171226 0%,
            #07070b 70%
        );
}}


.loading-icon {{
    font-size: 46px;

    margin-bottom: 12px;
}}


.loading-text {{
    color: #a8a8b6;

    font-size: 14px;

    font-weight: 600;
}}


.status {{
    width: 100%;

    max-width: 900px;

    margin-top: 17px;

    text-align: center;

    color: #9d9dac;

    font-size: 13px;

    font-weight: 600;
}}


.features {{
    margin-top: 18px;

    color: #777786;

    font-size: 12px;

    text-align: center;

    letter-spacing: .2px;
}}


.brand {{
    margin-top: auto;

    padding-top: 45px;

    color: #555563;

    font-size: 12px;

    font-weight: 700;

    letter-spacing: 1px;
}}


.hidden {{
    display: none !important;
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
        🌙 Premium HD Video Streaming
    </div>


    <div class="player-card">


        <div
            id="loadingScreen"
            class="loading-screen"
        >

            <div class="loading-icon">
                🔒
            </div>

            <div class="loading-text">
                Advertisement required
            </div>

        </div>


        <video
            id="videoPlayer"
            class="hidden"
            controls
            playsinline
            webkit-playsinline
            preload="metadata"
            controlsList="nodownload"
        >

            Your browser does not support
            HTML5 video.

        </video>


    </div>


    <div
        id="status"
        class="status"
    >
        📺 Preparing advertisement...
    </div>


    <div class="features">
        📡 MTProto
        &nbsp;•&nbsp;
        Range
        &nbsp;•&nbsp;
        Seek
        &nbsp;•&nbsp;
        Large Files
        &nbsp;•&nbsp;
        HD
    </div>


    <div class="brand">
        NIGHT HUB
    </div>


</div>


<script>


// ========================================================
// CONFIG
// ========================================================

const STREAM_URL =
    "{stream_url}";


const ADSGRAM_BLOCK_ID =
    "{ADSGRAM_BLOCK_ID}";


// ========================================================
// TELEGRAM MINI APP
// ========================================================

try {{

    if (
        window.Telegram &&
        window.Telegram.WebApp
    ) {{

        Telegram.WebApp.ready();

        Telegram.WebApp.expand();


        try {{

            Telegram.WebApp.setHeaderColor(
                "#08080f"
            );

            Telegram.WebApp.setBackgroundColor(
                "#08080f"
            );

        }} catch (error) {{

            console.log(
                "Telegram color error:",
                error
            );

        }}

    }}

}} catch (error) {{

    console.log(
        "Telegram WebApp error:",
        error
    );

}}


// ========================================================
// ELEMENTS
// ========================================================

const video =
    document.getElementById(
        "videoPlayer"
    );


const status =
    document.getElementById(
        "status"
    );


const loadingScreen =
    document.getElementById(
        "loadingScreen"
    );


// ========================================================
// ADSGRAM
// ========================================================

let adController = null;


function initializeAds() {{

    try {{

        if (
            !window.Adsgram ||
            !ADSGRAM_BLOCK_ID
        ) {{

            console.log(
                "AdsGram unavailable"
            );

            return false;
        }}


        adController =
            window.Adsgram.init({{
                blockId:
                    ADSGRAM_BLOCK_ID
            }});


        return true;


    }} catch (error) {{

        console.log(
            "AdsGram init error:",
            error
        );

        return false;
    }}
}}


// ========================================================
// START VIDEO AFTER AD
// ========================================================

async function startVideo() {{

    try {{

        status.textContent =
            "▶️ Starting video...";


        // Source is intentionally added
        // only after advertisement.

        video.src =
            STREAM_URL;


        video.classList.remove(
            "hidden"
        );


        loadingScreen.classList.add(
            "hidden"
        );


        video.load();


        try {{

            await video.play();

        }} catch (playError) {{

            console.log(
                "Autoplay blocked:",
                playError
            );


            status.textContent =
                "▶️ Tap the video to play";
        }}


    }} catch (error) {{

        console.log(
            "Video start error:",
            error
        );


        status.textContent =
            "❌ Video could not be started";
    }}
}}


// ========================================================
// SHOW ADVERTISEMENT
// ========================================================

async function showAdvertisement() {{

    const adsAvailable =
        initializeAds();


    // If AdsGram isn't available,
    // don't permanently lock player.

    if (!adsAvailable) {{

        status.textContent =
            "▶️ Starting video...";


        await startVideo();

        return;
    }}


    try {{

        status.textContent =
            "📺 Loading advertisement...";


        /*
         * For a Reward block,
         * show() should resolve after
         * the required ad flow.
         */

        const result =
            await adController.show();


        console.log(
            "AdsGram result:",
            result
        );


        status.textContent =
            "✅ Advertisement finished";


        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    250
                )
        );


        // Automatic video start.

        await startVideo();


    }} catch (error) {{

        console.log(
            "AdsGram show error:",
            error
        );


        /*
         * If the ad provider fails,
         * don't leave the player broken.
         */

        status.textContent =
            "▶️ Starting video...";


        await startVideo();
    }}
}}


// ========================================================
// START AD AUTOMATICALLY
// ========================================================

window.addEventListener(
    "load",
    function() {{

        setTimeout(
            showAdvertisement,
            350
        );

    }}
);


// ========================================================
// VIDEO EVENTS
// ========================================================

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

        if (!video.ended) {{

            status.textContent =
                "⏸️ Paused";

        }}

    }}
);


video.addEventListener(
    "seeking",
    function() {{

        status.textContent =
            "🔄 Seeking...";

    }}
);


video.addEventListener(
    "seeked",
    function() {{

        status.textContent =
            "▶️ NIGHT HUB";

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
            "HTML5 video error:",
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
# VIDEO STREAM
# =========================================================

async def stream_video(
    request: web.Request
):

    file_id = request.query.get(
        "file_id"
    )


    if not file_id:

        return web.Response(
            text="Missing file_id",
            status=400,
        )


    # =====================================================
    # FILE SIZE
    # =====================================================

    try:

        file_size = int(
            request.query.get(
                "size",
                "0"
            )
        )

    except ValueError:

        file_size = 0


    if file_size <= 0:

        return web.Response(
            text="Invalid file size",
            status=400,
        )


    if file_size > MAX_FILE_SIZE:

        return web.Response(
            text="File is larger than 2 GB",
            status=413,
        )


    mime_type = request.query.get(
        "mime",
        "video/mp4"
    )


    file_name = request.query.get(
        "name",
        "video.mp4"
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
        file_size,
    )


    if (
        range_header
        and not requested_range
    ):

        return web.Response(
            status=416,
            headers={
                "Content-Range":
                    f"bytes */{file_size}",

                "Accept-Ranges":
                    "bytes",
            },
        )


    # =====================================================
    # HEAD REQUEST
    # =====================================================

    if request.method == "HEAD":

        if requested_range:

            start_byte, end_byte = (
                requested_range
            )


            content_length = (
                end_byte
                - start_byte
                + 1
            )


            headers = {

                "Content-Type":
                    mime_type,

                "Content-Length":
                    str(content_length),

                "Accept-Ranges":
                    "bytes",

                "Content-Range":
                    (
                        f"bytes "
                        f"{start_byte}-"
                        f"{end_byte}/"
                        f"{file_size}"
                    ),

                "Cache-Control":
                    "no-cache",
            }


            return web.Response(
                status=206,
                headers=headers,
            )


        headers = {

            "Content-Type":
                mime_type,

            "Content-Length":
                str(file_size),

            "Accept-Ranges":
                "bytes",

            "Cache-Control":
                "no-cache",
        }


        return web.Response(
            status=200,
            headers=headers,
        )


    # =====================================================
    # DETERMINE RANGE
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
    # RESPONSE HEADERS
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
                "inline; "
                "filename*=UTF-8''"
                f"{quote(file_name)}"
            ),

        "Cache-Control":
            "no-cache, no-store, must-revalidate",

        "Pragma":
            "no-cache",

        "X-Content-Type-Options":
            "nosniff",

        "Access-Control-Allow-Origin":
            "*",
    }


    if status_code == 206:

        headers["Content-Range"] = (
            f"bytes "
            f"{start_byte}-"
            f"{end_byte}/"
            f"{file_size}"
        )


    # =====================================================
    # STREAM RESPONSE
    # =====================================================

    response = web.StreamResponse(
        status=status_code,
        headers=headers,
    )


    await response.prepare(
        request
    )


    # =====================================================
    # PYROGRAM CHUNKS
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


    # =====================================================
    # STREAM TELEGRAM FILE
    # =====================================================

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


            # -----------------------------------------
            # REMOVE BYTES BEFORE RANGE
            # -----------------------------------------

            if chunk_number == 0:

                if inner_offset:

                    chunk = chunk[
                        inner_offset:
                    ]


            # -----------------------------------------
            # LIMIT CHUNK TO REQUESTED DATA
            # -----------------------------------------

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

        print(
            "Stream cancelled by browser."
        )

        raise


    except Exception as error:

        print(
            "======================================"
        )

        print(
            "MTProto STREAMING ERROR"
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
            1024
            * 1024
            * 1024
            * 10
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


    # MINI APP

    app.router.add_get(
        "/watch",
        player
    )


    # VIDEO STREAM

    app.router.add_route(
        "GET",
        "/stream",
        stream_video
    )


    # HEAD

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
        "======================================"
    )

    print(
        "        NIGHT HUB SERVER"
    )

    print(
        "======================================"
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
        "90MB+: ENABLED"
    )

    print(
        "2GB: ENABLED"
    )

    print(
        "RANGE: ENABLED"
    )

    print(
        "SEEK: ENABLED"
    )

    print(
        f"AdsGram: {ADSGRAM_BLOCK_ID}"
    )

    print(
        "COVER PHOTO: ENABLED"
    )

    print(
        "WATCH NOW: ENABLED"
    )

    print(
        "======================================"
    )


# =========================================================
# MAIN
# =========================================================

async def main():

    # =====================================================
    # START MTProto
    # =====================================================

    print(
        "Starting Telegram MTProto..."
    )


    await mtproto.start()


    print(
        "Telegram MTProto started ✅"
    )


    # =====================================================
    # START WEB SERVER
    # =====================================================

    await start_web_server()


    # =====================================================
    # START BOT
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
