import asyncio
import os
import urllib.parse
import time
import base64
import json
import logging
import math
import mimetypes
from aiohttp import web, ClientSession
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import pyrebase
from info import *  # Ensure this file exists with API_ID, API_HASH, BOT_TOKEN, STREAM_URL, LOG_CHANNEL, ADMINS

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# ⚠️ MATCH THIS KEY WITH YOUR REACT APP (services/streamProxy.ts)
SECRET_KEY = "SKILLNEAST_SECURE_STREAM_V2" 

# --- FIREBASE CONFIGURATION ---
firebaseConfig = {
    "apiKey": "AIzaSyChwpbFb6M4HtG6zwjg0AXh7Lz9KjnrGZk",
    "authDomain": "adminneast.firebaseapp.com",
    "databaseURL": "https://adminneast-default-rtdb.firebaseio.com",
    "projectId": "adminneast",
    "storageBucket": "adminneast.firebasestorage.app",
    "messagingSenderId": "883877553418",
    "appId": "1:883877553418:web:84ce8200f4b471bfffc6f3",
    "measurementId": "G-PCH99BDF1S"
}

try:
    firebase = pyrebase.initialize_app(firebaseConfig)
    db = firebase.database()
    logger.info("✅ Firebase Connected Successfully")
except Exception as e:
    logger.error(f"❌ Firebase Error: {e}")

# --- GLOBAL VARIABLES ---
user_session = {}
bot = Client(
    "SkillNeastBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ==============================================================================
#  1. SECURE STREAMING LOGIC (New Protection System)
# ==============================================================================

def xor_decrypt(text, key):
    """Decrypts the XOR encrypted string from frontend"""
    result = []
    for i, char in enumerate(text):
        key_char = key[i % len(key)]
        result.append(chr(ord(char) ^ ord(key_char)))
    return "".join(result)

def decode_token(token):
    """Decodes Base64 and Decrypts payload"""
    try:
        token += '=' * (-len(token) % 4) # Fix padding
        token = token.replace('-', '+').replace('_', '/')
        decoded_bytes = base64.b64decode(token)
        decoded_str = decoded_bytes.decode('utf-8')
        decrypted_json = xor_decrypt(decoded_str, SECRET_KEY)
        return json.loads(decrypted_json)
    except Exception as e:
        logger.warning(f"Token Decode Failed: {e}")
        return None

async def secure_stream_handler(request):
    """
    Route: /api/v2/stream?vid=ENCRYPTED_TOKEN
    Proxies the stream securely.
    """
    token = request.query.get('vid') or request.query.get('token')
    
    if not token:
        return web.Response(text="Access Denied: Missing Token", status=403)

    data = decode_token(token)

    if not data:
        return web.Response(text="Access Denied: Invalid Token", status=403)

    # Validate Expiry (60s window)
    if data.get('exp', 0) < int(time.time() * 1000):
        return web.Response(text="Link Expired", status=410)

    # Get Real URL (The /dl/ link stored in Firebase)
    real_url = data.get('url')

    # Proxy the content
    try:
        async with ClientSession() as session:
            headers = {}
            if request.headers.get('Range'):
                headers['Range'] = request.headers.get('Range')

            async with session.get(real_url, headers=headers) as resp:
                response = web.StreamResponse(status=resp.status, reason=resp.reason)
                
                # Forward critical headers
                for h in ['Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges']:
                    if h in resp.headers:
                        response.headers[h] = resp.headers[h]
                
                response.headers['Access-Control-Allow-Origin'] = '*'
                
                await response.prepare(request)
                
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    await response.write(chunk)
                
                return response
    except Exception as e:
        logger.error(f"Proxy Error: {e}")
        return web.Response(text="Internal Stream Error", status=500)

# ==============================================================================
#  2. STANDARD STREAM HANDLER (/dl/ Route)
# ==============================================================================

class MediaStreamer:
    """Helper to stream file from Telegram"""
    def __init__(self, client, message):
        self.client = client
        self.message = message
        self.file_id = message.video.file_id if message.video else message.document.file_id if message.document else message.audio.file_id
        self.file_size = message.video.file_size if message.video else message.document.file_size if message.document else message.audio.file_size

    async def yield_chunks(self, offset, length):
        async for chunk in self.client.stream_media(self.message, offset=offset, limit=length):
            yield chunk

async def dl_route_handler(request):
    """
    Route: /dl/{message_id}/{filename}
    Fetches from Telegram and streams to the proxy or user.
    """
    try:
        message_id = int(request.match_info['message_id'])
        message = await bot.get_messages(LOG_CHANNEL, message_id)
        
        if not message or not (message.video or message.document or message.audio):
            return web.Response(text="File not found", status=404)

        streamer = MediaStreamer(bot, message)
        file_size = streamer.file_size
        
        # Range Handling
        range_header = request.headers.get("Range")
        offset = 0
        length = file_size

        if range_header:
            parts = range_header.replace("bytes=", "").split("-")
            offset = int(parts[0])
            if parts[1]:
                length = int(parts[1]) - offset + 1
            else:
                length = file_size - offset

        # Mime Type
        mime_type = mimetypes.guess_type(request.path)[0] or "application/octet-stream"
        
        response = web.StreamResponse(
            status=206 if range_header else 200,
            reason="Partial Content" if range_header else "OK"
        )
        
        response.headers["Content-Type"] = mime_type
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Content-Range"] = f"bytes {offset}-{offset + length - 1}/{file_size}"
        response.headers["Content-Length"] = str(length)
        response.headers["Content-Disposition"] = f'attachment; filename="{os.path.basename(request.path)}"'

        await response.prepare(request)

        async for chunk in streamer.yield_chunks(offset, length):
            await response.write(chunk)
            
        return response

    except Exception as e:
        logger.error(f"DL Handler Error: {e}")
        return web.Response(text="Server Error", status=500)

async def health_check(request):
    return web.Response(text="SkillNeast Server Active 🟢")

# ==============================================================================
#  3. BOT LOGIC (Your Provided Logic)
# ==============================================================================

async def get_stream_link(message: Message):
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        file_name = "Unknown"
        if message.video: file_name = message.video.file_name or f"Video_{log_msg.id}.mp4"
        elif message.document: file_name = message.document.file_name or f"File_{log_msg.id}.pdf"
        elif message.audio: file_name = message.audio.file_name or f"Audio_{log_msg.id}.mp3"
            
        clean_name = os.path.splitext(file_name)[0].replace("_", " ").replace("-", " ")
        safe_filename = urllib.parse.quote_plus(file_name)
        
        # Link Format: https://your-app.onrender.com/dl/123/video.mp4
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        return stream_link, clean_name
    except Exception as e:
        logger.error(f"Link Gen Error: {e}")
        return None, None

def get_name(data):
    if not data or not isinstance(data, dict): return "Unnamed"
    return data.get("name") or data.get("title") or "Unnamed"

def get_breadcrumb(user_id):
    sess = user_session.get(user_id, {})
    return f"📂 `{sess.get('cat_name','...')}`\n   └ 🎓 `{sess.get('batch_name','...')}`\n      └ 📺 `{sess.get('mod_name','...')}`"

# --- Bot Handlers ---

@bot.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(client, message):
    user_id = message.from_user.id
    user_session[user_id] = {"state": "idle", "fast_mode": False, "queue": []}
    await message.reply_text(
        "**🔥 Firebase Admin Panel 2.0**\nStatus: 🟢 **Connected**\n\n👇 Select Category:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")]])
    )

@bot.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(client, query):
    try:
        cats = db.child("categories").get().val() or {}
        btns = [[InlineKeyboardButton(f"📂 {get_name(v)}", callback_data=f"fb_sel_cat_{k}|{get_name(v)}")] for k, v in (cats.items() if isinstance(cats, dict) else enumerate(cats)) if v]
        await query.message.edit_text("**📂 Select Category:**", reply_markup=InlineKeyboardMarkup(btns))
    except Exception as e: await query.message.edit_text(f"❌ Error: {e}")

@bot.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(client, query):
    cid, cname = query.data.split("_")[3].split("|")
    user_session.setdefault(query.from_user.id, {}).update({"cat_id": cid, "cat_name": cname})
    try:
        batches = db.child("categories").child(cid).child("batches").get().val() or {}
        btns = [[InlineKeyboardButton(f"🎓 {get_name(v)}", callback_data=f"fb_sel_batch_{k}|{get_name(v)}")] for k, v in batches.items() if v]
        btns.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"📂 `{cname}`\n👇 **Select Batch:**", reply_markup=InlineKeyboardMarkup(btns))
    except: await query.message.edit_text("Error fetching batches")

@bot.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(client, query):
    bid, bname = query.data.split("_")[3].split("|")
    uid = query.from_user.id
    user_session[uid].update({"batch_id": bid, "batch_name": bname})
    cid = user_session[uid]["cat_id"]
    try:
        mods = db.child("categories").child(cid).child("batches").child(bid).child("modules").get().val() or {}
        btns = [[InlineKeyboardButton(f"📺 {get_name(v)}", callback_data=f"fb_set_mod_{k}|{get_name(v)}")] for k, v in mods.items() if v]
        btns.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
        btns.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cid}|{user_session[uid]['cat_name']}")])
        await query.message.edit_text(f"🎓 `{bname}`\n👇 **Select Module:**", reply_markup=InlineKeyboardMarkup(btns))
    except: await query.message.edit_text("Error fetching modules")

@bot.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(client, query):
    mid, mname = query.data.split("_")[3].split("|")
    uid = query.from_user.id
    user_session[uid].update({"module_id": mid, "mod_name": mname, "state": "active_firebase", "queue": []})
    
    is_fast = user_session[uid].get("fast_mode", False)
    fast_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    btns = [
        [InlineKeyboardButton("📝 Manage Content", callback_data=f"fb_manage_{mid}")],
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🛑 Stop", callback_data="fb_clear_session")]
    ]
    await query.message.edit_text(f"✅ **Ready!**\n{get_breadcrumb(uid)}\n\n📤 **Send Files Now**", reply_markup=InlineKeyboardMarkup(btns))

@bot.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast(client, query):
    uid = query.from_user.id
    if not user_session[uid].get("fast_mode"):
        btns = [[InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"), InlineKeyboardButton("📄 Resources", callback_data="fb_set_fast_res")]]
        await query.message.edit_text("**⚡ Fast Mode Type:**", reply_markup=InlineKeyboardMarkup(btns))
    else:
        user_session[uid]["fast_mode"] = False
        mid, mname = user_session[uid]["module_id"], user_session[uid]["mod_name"]
        query.data = f"fb_set_mod_{mid}|{mname}"
        await set_active_module(client, query)

@bot.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(client, query):
    uid = query.from_user.id
    t = query.data.split("_")[3]
    user_session[uid].update({"fast_mode": True, "default_type": t, "queue": []})
    await query.answer("⚡ Fast Mode ON!", show_alert=True)
    mid, mname = user_session[uid]["module_id"], user_session[uid]["mod_name"]
    query.data = f"fb_set_mod_{mid}|{mname}"
    await set_active_module(client, query)

async def process_queue(client, uid):
    await asyncio.sleep(4)
    if uid not in user_session or not user_session[uid]["queue"]:
        user_session[uid]["queue_running"] = False
        return

    queue = sorted(user_session[uid]["queue"], key=lambda x: x.id)
    msg = await client.send_message(uid, f"🔄 **Processing {len(queue)} files...**")
    
    cat, batch, mod = user_session[uid]["cat_id"], user_session[uid]["batch_id"], user_session[uid]["module_id"]
    target = "lectures" if user_session[uid]["default_type"] == "lec" else "resources"
    
    count = 0
    for m in queue:
        count += 1
        if count % 3 == 0: await msg.edit(f"🚀 Uploading... ({count}/{len(queue)})")
        link, name = await get_stream_link(m)
        if link:
            ts = int(time.time() * 1000)
            path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
            ref = path.push({"name": name, "link": link, "order": ts})
            path.child(ref['name']).update({"id": ref['name']})

    user_session[uid]["queue"] = []
    user_session[uid]["queue_running"] = False
    await msg.edit("🎉 **Batch Done!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="fb_hide_msg")]]))

@bot.on_message((filters.video | filters.document | filters.audio) & filters.user(ADMINS))
async def handle_file(client, message):
    uid = message.from_user.id
    if uid not in user_session or user_session[uid].get("state") != "active_firebase": return

    if user_session[uid].get("fast_mode"):
        user_session[uid].setdefault("queue", []).append(message)
        if not user_session[uid].get("queue_running"):
            user_session[uid]["queue_running"] = True
            asyncio.create_task(process_queue(client, uid))
    else:
        msg = await message.reply("🔄 Processing...")
        link, name = await get_stream_link(message)
        if link:
            user_session[uid]["temp_data"] = {"title": name, "url": link}
            await msg.edit(f"📂 `{name}`", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Add", callback_data="fb_name_keep"), InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")]
            ]))

# --- Other Standard Handlers (Rename, Create, Delete etc.) ---
@bot.on_message(filters.text & filters.user(ADMINS))
async def handle_text(client, message):
    uid = message.from_user.id
    if uid not in user_session: return
    state = user_session[uid].get("state", "")

    if state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[uid]["temp_data"]["title"] = new_name
        user_session[uid]["state"] = "active_firebase"
        await ask_file_type(message, new_name)
    
    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat, batch = user_session[uid]["cat_id"], user_session[uid]["batch_id"]
        ts = int(time.time() * 1000)
        ref = db.child("categories").child(cat).child("batches").child(batch).child("modules").push({"name": mod_name, "order": ts})
        db.child("categories").child(cat).child("batches").child(batch).child("modules").child(ref['name']).update({"id": ref['name']})
        await message.reply_text(f"✅ Module `{mod_name}` created.")
        user_session[uid]["state"] = "idle"

async def ask_file_type(message, name):
    btns = [[InlineKeyboardButton("🎬 Lecture", callback_data="fb_confirm_lec"), InlineKeyboardButton("📄 Resource", callback_data="fb_confirm_res")]]
    txt = f"📌 Confirm: `{name}`"
    if isinstance(message, Message): await message.reply(txt, reply_markup=InlineKeyboardMarkup(btns))
    else: await message.edit_text(txt, reply_markup=InlineKeyboardMarkup(btns))

@bot.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_name(client, query):
    await ask_file_type(query.message, user_session[query.from_user.id]["temp_data"]["title"])

@bot.on_callback_query(filters.regex("^fb_name_rename"))
async def rename_ask(client, query):
    user_session[query.from_user.id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ Send new name:")

@bot.on_callback_query(filters.regex("^fb_confirm_"))
async def push_single(client, query):
    action = query.data.split("_")[2]
    uid = query.from_user.id
    data = user_session[uid]["temp_data"]
    cat, batch, mod = user_session[uid]["cat_id"], user_session[uid]["batch_id"], user_session[uid]["module_id"]
    target = "lectures" if action == "lec" else "resources"
    ts = int(time.time() * 1000)
    ref = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target).push({"name": data["title"], "link": data["url"], "order": ts})
    db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target).child(ref['name']).update({"id": ref['name']})
    await query.message.edit_text("✅ Added!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Hide", callback_data="fb_hide_msg")]]))

@bot.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_req(client, query):
    user_session[query.from_user.id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("Send Module Name:")

@bot.on_callback_query(filters.regex("^fb_clear_session"))
async def clear_s(client, query):
    user_session.pop(query.from_user.id, None)
    await query.message.edit_text("Stopped.")

@bot.on_callback_query(filters.regex("^fb_hide_msg"))
async def hide_m(client, query): await query.message.delete()

@bot.on_callback_query(filters.regex("^fb_manage_"))
async def manage_menu(bot, query):
    # Simplified manage menu placeholder
    await query.answer("Feature in development", show_alert=True)

# ==============================================================================
#  4. MAIN RUNNER (Run Bot + Server)
# ==============================================================================

if __name__ == "__main__":
    app = web.Application()
    
    # Routes
    app.router.add_get("/", health_check)
    app.router.add_get("/api/v2/stream", secure_stream_handler)
    app.router.add_get(r"/dl/{message_id:\d+}/{file_name:.*}", dl_route_handler)

    port = int(os.environ.get("PORT", 8080))

    async def start_services():
        logger.info("🤖 Starting Bot...")
        await bot.start()
        
        logger.info(f"🌍 Starting Web Server on Port {port}...")
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        
        logger.info("✅ All Systems Operational!")
        await idle()
        await bot.stop()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
