import asyncio
import os
import urllib.parse
import time
import base64

# --- New Security Imports ---
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import * import pyrebase

# --- 1. Security Configuration (SECRET KEY) ---
# DHYAAN DEIN: Ye Key WAHI honi chahiye jo Website par decrypt ke liye use hogi.
# Issey change karke apni 32-character key dalein.
SECRET_KEY = b"12345678901234567890123456789012" 

# --- 2. Firebase Configuration ---
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

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

# Session Structure
user_session = {}

# --- Helper Functions ---

def encrypt_link(url):
    """Encrypts the link using AES-256 CBC Mode"""
    try:
        # 1. Generate random IV (16 bytes)
        iv = get_random_bytes(16)
        # 2. Setup Cipher
        cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
        # 3. Encrypt
        encrypted_bytes = cipher.encrypt(pad(url.encode('utf-8'), AES.block_size))
        # 4. Encode to Base64
        iv_base64 = base64.b64encode(iv).decode('utf-8')
        encrypted_base64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        # 5. Return combined string
        return f"{iv_base64}:{encrypted_base64}"
    except Exception as e:
        print(f"Encryption Error: {e}")
        return url # Fallback to normal if error (Safety)

async def get_stream_link(message: Message):
    """Generates Direct Link & Cleans Filename"""
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        file_name = "Unknown File"
        
        if message.video:
            file_name = message.video.file_name or f"Video {log_msg.id}.mp4"
        elif message.document:
            file_name = message.document.file_name or f"File {log_msg.id}.pdf"
        elif message.audio:
            file_name = message.audio.file_name or f"Audio {log_msg.id}.mp3"
            
        name_without_ext = os.path.splitext(file_name)[0]
        clean_name = name_without_ext.replace("_", " ").replace("-", " ")
        
        # Safe filename for URL
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None

def get_name(data):
    if not data: return "Unnamed"
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or "Unnamed"
    return "Unnamed"

def get_breadcrumb(user_id):
    sess = user_session.get(user_id, {})
    cat = sess.get("cat_name", "...")
    batch = sess.get("batch_name", "...")
    mod = sess.get("mod_name", "...")
    return f"📂 `{cat}`\n └ 🎓 `{batch}`\n   └ 📺 `{mod}`"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    user_session[user_id] = {"state": "idle", "fast_mode": False, "queue": []}
    
    txt = (
        "**🔥 Firebase Admin Panel 2.0 (SECURE)**\n\n"
        "Database Status: 🟢 **Connected**\n"
        "Encryption: 🔒 **AES-256 Enabled**\n\n"
        "👇 Select a Category to start:"
    )
    
    await message.reply_text(txt, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="fb_mode_menu")]
    ]))

# --- Navigation Handlers ---

@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        cats_data = db.child("categories").get().val()
        buttons = []
        if cats_data:
            iterator = cats_data.items() if isinstance(cats_data, dict) else enumerate(cats_data)
            for key, val in iterator:
                if val:
                    c_name = get_name(val)
                    buttons.append([InlineKeyboardButton(f"📂 {c_name}", callback_data=f"fb_sel_cat_{key}|{c_name}")])
        
        await query.message.edit_text("**📂 Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"❌ Error: {e}")

@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    data_parts = query.data.split("_")[3].split("|")
    cat_id = data_parts[0]
    cat_name = data_parts[1] if len(data_parts) > 1 else cat_id
    
    user_id = query.from_user.id
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id].update({"cat_id": cat_id, "cat_name": cat_name})
    
    try:
        batches_data = db.child("categories").child(cat_id).child("batches").get().val()
        buttons = []
        if batches_data:
            iterator = batches_data.items() if isinstance(batches_data, dict) else enumerate(batches_data)
            for key, val in iterator:
                if val and isinstance(val, dict):
                    b_name = get_name(val)
                    buttons.append([InlineKeyboardButton(f"🎓 {b_name}", callback_data=f"fb_sel_batch_{key}|{b_name}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"📂 **Category:** `{cat_name}`\n👇 **Select Batch:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    data_parts = query.data.split("_")[3].split("|")
    batch_id = data_parts[0]
    batch_name = data_parts[1] if len(data_parts) > 1 else batch_id
    
    user_id = query.from_user.id
    user_session[user_id].update({"batch_id": batch_id, "batch_name": batch_name})
    cat_id = user_session[user_id]["cat_id"]
    
    try:
        modules_data = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get().val()
        buttons = []
        if modules_data:
            iterator = modules_data.items() if isinstance(modules_data, dict) else enumerate(modules_data)
            for key, val in iterator:
                if val and isinstance(val, dict):
                    m_name = get_name(val)
                    buttons.append([InlineKeyboardButton(f"📺 {m_name}", callback_data=f"fb_set_mod_{key}|{m_name}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}|{user_session[user_id]['cat_name']}")])
        await query.message.edit_text(f"🎓 **Batch:** `{batch_name}`\n👇 **Select Module:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    data_parts = query.data.split("_")[3].split("|")
    module_id = data_parts[0]
    module_name = data_parts[1] if len(data_parts) > 1 else "Unknown"
    
    user_id = query.from_user.id
    # Reset queue when entering module
    user_session[user_id].update({
        "module_id": module_id,
        "mod_name": module_name,
        "state": "active_firebase",
        "queue": []
    })
    
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_btn = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    buttons = [
        [InlineKeyboardButton("📝 Manage Content", callback_data=f"fb_manage_{module_id}")],
        [InlineKeyboardButton(fast_btn, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🛑 Stop", callback_data="fb_clear_session")]
    ]
    
    path = get_breadcrumb(user_id)
    await query.message.edit_text(
        f"✅ **Ready to Upload!**\n\n{path}\n\n⚡ **Fast Mode:** {fast_status}\n🔒 **Encryption:** ON\n\n📥 **Send files now.**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- FAST MODE QUEUE LOGIC (WITH ENCRYPTION) ---

async def process_queue(bot, user_id):
    """Processes collected files in strict order"""
    await asyncio.sleep(4) 
    
    if user_id not in user_session or not user_session[user_id]["queue"]:
        user_session[user_id]["queue_running"] = False
        return

    # 1. Sort queue by Message ID
    queue = sorted(user_session[user_id]["queue"], key=lambda x: x.id)
    total_files = len(queue)
    
    # 2. Status Message
    status_msg = await bot.send_message(user_id, f"🔄 **Processing Batch...**\nFound {total_files} files.")
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    def_type = user_session[user_id]["default_type"]
    target = "lectures" if def_type == "lec" else "resources"
    
    count = 0
    uploaded_names = []
    
    # 3. Process Sorted List
    for msg in queue:
        count += 1
        try:
            if count == 1 or count % 3 == 0:
                await status_msg.edit(f"🚀 **Uploading & Encrypting...** ({count}/{total_files})\nDo not send more files yet.")
            
            stream_link, clean_name = await get_stream_link(msg)
            
            if not stream_link:
                continue

            # --- ENCRYPTION STEP ---
            encrypted_link = encrypt_link(stream_link)
            # -----------------------

            ts = int(time.time() * 1000)
            
            # Push to Firebase
            path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
            
            # Save Encrypted Link instead of Raw Link
            ref = path.push({"name": clean_name, "link": encrypted_link, "order": ts})
            
            key = ref['name']
            path.child(key).update({"id": key})
            uploaded_names.append(clean_name)
            
        except Exception as e:
            print(f"Failed to upload: {e}")

    # 4. Clear Queue and Final Status
    user_session[user_id]["queue"] = []
    user_session[user_id]["queue_running"] = False
    
    summary = "\n".join([f"✅ {n}" for n in uploaded_names[:5]])
    if len(uploaded_names) > 5:
        summary += f"\n...and {len(uploaded_names)-5} more."
        
    await status_msg.edit(
        f"🎉 **Batch Completed!**\n\n{summary}\n\nTotal Added: {total_files}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Close", callback_data="fb_hide_msg")]])
    )

# --- File Handler (Modified) ---

@Client.on_message((filters.video | filters.document | filters.audio) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    session = user_session[user_id]
    
    if session.get("state") != "active_firebase": return

    # FAST MODE: Add to Queue
    if session.get("fast_mode"):
        if "queue" not in session: session["queue"] = []
        session["queue"].append(message)
        
        if not session.get("queue_running"):
            session["queue_running"] = True
            asyncio.create_task(process_queue(bot, user_id))
        return

    # NORMAL MODE (One by one)
    msg = await message.reply("🔄 **Processing...**")
    stream_link, clean_name = await get_stream_link(message)
    
    if not stream_link: return await msg.edit("❌ Error.")
    
    # Store raw link in temp for now, we encrypt when user confirms
    session["temp_data"] = {"title": clean_name, "url": stream_link}
    
    buttons = [
        [InlineKeyboardButton("✅ Add (Default Name)", callback_data="fb_name_keep")],
        [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")],
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_clear_temp")]
    ]
    await msg.edit(f"📂 **File:** `{clean_name}`\nProceed?", reply_markup=InlineKeyboardMarkup(buttons))

# --- Other Features ---

@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    current_status = user_session[user_id].get("fast_mode", False)
    
    if not current_status:
        buttons = [[InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"), InlineKeyboardButton("📄 Resources", callback_data="fb_set_fast_res")]]
        await query.message.edit_text("**⚡ Fast Mode Setup**\nSelect content type:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        user_session[user_id]["fast_mode"] = False
        user_session[user_id]["queue"] = []
        mod_id = user_session[user_id]["module_id"]
        mod_name = user_session[user_id].get("mod_name", "")
        query.data = f"fb_set_mod_{mod_id}|{mod_name}"
        await set_active_module(bot, query)

@Client.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(bot, query: CallbackQuery):
    user_id = query.from_user.id
    type_ = query.data.split("_")[3]
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = type_
    user_session[user_id]["queue"] = []
    await query.answer("⚡ Fast Mode ON! Send multiple files now.", show_alert=True)
    
    mod_id = user_session[user_id]["module_id"]
    mod_name = user_session[user_id].get("mod_name", "")
    query.data = f"fb_set_mod_{mod_id}|{mod_name}"
    await set_active_module(bot, query)

# --- Standard Handlers (Rename, Text, Manage) ---

@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    
    state = user_session[user_id].get("state", "")
    
    if state.startswith("waiting_edit_"):
        key = state.split("_")[2]
        new_name = message.text.strip()
        cat, batch, mod = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["module_id"]
        
        # Note: We only update name here, link remains encrypted
        db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(key).update({"name": new_name})
        
        await message.reply_text(f"✅ Renamed to: `{new_name}`")
        user_session[user_id]["state"] = "active_firebase"

    elif state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, new_name, user_session[user_id]["temp_data"]["url"])

    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat, batch = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"]
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ts = int(time.time() * 1000)
        ref = path.push({"name": mod_name, "order": ts})
        key = ref['name']
        path.child(key).update({"id": key})
        await message.reply_text(f"✅ Created Module: `{mod_name}`")
        user_session[user_id]["state"] = "idle"

@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_name(bot, query):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"], data["url"])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def rename_ask(bot, query):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **Send New Name:**")

@Client.on_callback_query(filters.regex("^fb_clear_temp"))
async def clear_temp(bot, query):
    user_id = query.from_user.id
    if "temp_data" in user_session[user_id]:
        del user_session[user_id]["temp_data"]
    await query.message.edit_text("❌ Cancelled.")

async def ask_file_type(message, title, url):
    buttons = [[InlineKeyboardButton("🎬 Lecture", callback_data="fb_confirm_lec"), InlineKeyboardButton("📄 Resource", callback_data="fb_confirm_res")]]
    txt = f"📌 **Confirm Upload:**\nName: `{title}`"
    if isinstance(message, Message):
        await message.reply_text(txt, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.edit_text(txt, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_manual(bot, query):
    action = query.data.split("_")[2]
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    
    cat, batch, mod = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["module_id"]
    target = "lectures" if action == "lec" else "resources"
    
    # --- ENCRYPTION STEP ---
    encrypted_link = encrypt_link(data["url"])
    # -----------------------

    path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
    ts = int(time.time() * 1000)
    
    # Save Encrypted Link
    ref = path.push({"name": data["title"], "link": encrypted_link, "order": ts})
    
    key = ref['name']
    path.child(key).update({"id": key})
    
    await query.message.edit_text("✅ **Added & Encrypted!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Hide", callback_data="fb_hide_msg")]]))

@Client.on_callback_query(filters.regex("^fb_manage_"))
async def manage_menu(bot, query):
    mod_id = query.data.split("_")[2]
    user_id = query.from_user.id
    cat, batch = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"]
    
    try:
        data = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod_id).child("lectures").get().val()
        buttons = []
        if data:
            iterator = data.items() if isinstance(data, dict) else enumerate(data)
            for key, val in iterator:
                if val:
                    buttons.append([InlineKeyboardButton(f"📄 {get_name(val)}", callback_data=f"fb_item_opt_{key}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_set_mod_{mod_id}|")])
        await query.message.edit_text("**Manage Content:**", reply_markup=InlineKeyboardMarkup(buttons))
    except:
        await query.message.edit_text("Error fetching list.")

@Client.on_callback_query(filters.regex("^fb_item_opt_"))
async def item_opt(bot, query):
    key = query.data.split("_")[3]
    user_id = query.from_user.id
    mod_id = user_session[user_id]["module_id"]
    
    buttons = [
        [InlineKeyboardButton("Delete", callback_data=f"fb_del_{key}"), InlineKeyboardButton("Rename", callback_data=f"fb_edit_ask_{key}")],
        [InlineKeyboardButton("Back", callback_data=f"fb_manage_{mod_id}")]
    ]
    await query.message.edit_text(f"Options for: `{key}`", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_del_"))
async def del_item(bot, query):
    key = query.data.split("_")[2]
    user_id = query.from_user.id
    cat, batch, mod = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["module_id"]
    
    db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(key).remove()
    await query.answer("Deleted!")
    query.data = f"fb_manage_{mod}"
    await manage_menu(bot, query)

@Client.on_callback_query(filters.regex("^fb_edit_ask_"))
async def rename_menu(bot, query):
    key = query.data.split("_")[3]
    user_session[query.from_user.id]["state"] = f"waiting_edit_{key}"
    await query.message.edit_text("Send New Name:")

@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_ask(bot, query):
    user_session[query.from_user.id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("Send Module Name:")

@Client.on_callback_query(filters.regex("^fb_clear_session"))
async def clear_session(bot, query):
    if query.from_user.id in user_session:
        del user_session[query.from_user.id]
    await query.message.edit_text("Stopped.")

@Client.on_callback_query(filters.regex("^fb_hide_msg"))
async def hide(bot, query):
    await query.message.delete()
