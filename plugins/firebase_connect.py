import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import *  # Ensure LOG_CHANNEL and STREAM_URL are in info.py
import pyrebase

# --- 1. Firebase Configuration ---
# WARNING: Apni API Keys ko hamesha Environment Variables mein rakhein.
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

# Session Storage
user_session = {}

# --- Helper Functions ---

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
            
        # Clean Name
        name_without_ext = os.path.splitext(file_name)[0]
        clean_name = name_without_ext.replace("_", " ").replace("-", " ")
        
        # Safe URL
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None

def get_name(data):
    """Safely extracts name from Firebase data"""
    if not data: return "Unnamed"
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or "Unnamed"
    return "Unnamed"

def get_breadcrumb(user_id):
    """Shows current path: Cat > Batch > Module"""
    sess = user_session.get(user_id, {})
    cat = sess.get("cat_name", "...")
    batch = sess.get("batch_name", "...")
    mod = sess.get("mod_name", "...")
    return f"📂 `{cat}`\n   └ 🎓 `{batch}`\n      └ 📺 `{mod}`"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    # Reset Session
    user_session[user_id] = {"state": "idle", "fast_mode": False}
    
    txt = (
        "**👋 Welcome to Firebase Admin Panel**\n\n"
        "Manage your content efficiently.\n"
        "Database Status: 🟢 **Connected**\n\n"
        "👇 **Select an action to begin:**"
    )
    
    buttons = [
        [InlineKeyboardButton("📂 Browse Categories", callback_data="fb_cat_list")],
        [InlineKeyboardButton("⚙️ Settings / Tools", callback_data="fb_mode_menu")]
    ]
    
    await message.reply_text(txt, reply_markup=InlineKeyboardMarkup(buttons))

# --- 1. Categories List ---
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
        
        buttons.append([InlineKeyboardButton("🔙 Main Menu", callback_data="fb_main_menu")]) # Add main menu handler if needed or redirect to command
        
        await query.message.edit_text(
            "**📂 Select a Category:**\n\nChoose where you want to add content.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await query.message.edit_text(f"❌ **Error:** {e}")

# --- 2. Batches List ---
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
        
        if not buttons:
             buttons.append([InlineKeyboardButton("🚫 No Batches Found", callback_data="ignore")])

        buttons.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="fb_cat_list")])
        
        await query.message.edit_text(
            f"📂 **Category:** `{cat_name}`\n\n👇 **Select a Batch:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        await query.message.edit_text(f"❌ Error loading batches: {e}")

# --- 3. Modules List ---
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
        
        # Grid layout for modules (2 per row)
        # buttons = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        
        buttons.append([InlineKeyboardButton("➕ Create New Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back to Batches", callback_data=f"fb_sel_cat_{cat_id}|{user_session[user_id]['cat_name']}")])
        
        await query.message.edit_text(
            f"📂 **Category:** `{user_session[user_id]['cat_name']}`\n"
            f"   └ 🎓 **Batch:** `{batch_name}`\n\n"
            f"👇 **Select a Module:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
         await query.message.edit_text(f"❌ Error: {e}")

# --- 4. Dashboard (Active State) ---
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    data_parts = query.data.split("_")[3].split("|")
    module_id = data_parts[0]
    module_name = data_parts[1] if len(data_parts) > 1 else "Unknown"
    
    user_id = query.from_user.id
    user_session[user_id].update({
        "module_id": module_id, 
        "mod_name": module_name,
        "state": "active_firebase"
    })
    
    # Fast Mode Check
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_btn_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    buttons = [
        [InlineKeyboardButton("📝 Manage Content (Edit/Delete)", callback_data=f"fb_manage_{module_id}")],
        [InlineKeyboardButton(fast_btn_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🛑 Stop / Change Path", callback_data="fb_clear_session")]
    ]

    path_text = get_breadcrumb(user_id)

    await query.message.edit_text(
        f"✅ **Target Locked!**\n\n"
        f"{path_text}\n\n"
        f"⚡ **Fast Mode:** {fast_status}\n"
        f"──────────────────\n"
        f"📤 **Send Files or URLs now to upload.**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Feature: Fast Mode ---
@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    current_status = user_session[user_id].get("fast_mode", False)
    
    if not current_status:
        buttons = [
            [InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"), 
             InlineKeyboardButton("📄 Notes/PDFs", callback_data="fb_set_fast_res")]
        ]
        await query.message.edit_text(
            "**⚡ Fast Mode Setup**\n\n"
            "Select the default type for uploads:", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        user_session[user_id]["fast_mode"] = False
        mod_id = user_session[user_id]["module_id"]
        mod_name = user_session[user_id].get("mod_name", "")
        # Return to dashboard
        query.data = f"fb_set_mod_{mod_id}|{mod_name}"
        await set_active_module(bot, query)

@Client.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(bot, query: CallbackQuery):
    user_id = query.from_user.id
    type_ = query.data.split("_")[3]
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = type_
    
    await query.answer("⚡ Fast Mode Enabled!", show_alert=True)
    
    mod_id = user_session[user_id]["module_id"]
    mod_name = user_session[user_id].get("mod_name", "")
    query.data = f"fb_set_mod_{mod_id}|{mod_name}"
    await set_active_module(bot, query)

# --- Feature: Manage Content ---
@Client.on_callback_query(filters.regex("^fb_manage_"))
async def manage_content_list(bot, query: CallbackQuery):
    module_id = query.data.split("_")[2]
    user_id = query.from_user.id
    cat, batch = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"]
    
    try:
        # Fetch lectures
        path_ref = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(module_id).child("lectures")
        lectures_data = path_ref.get().val()
        
        buttons = []
        if lectures_data:
            iterator = lectures_data.items() if isinstance(lectures_data, dict) else enumerate(lectures_data)
            for key, val in iterator:
                if val:
                    name = get_name(val)
                    buttons.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"fb_item_opt_{key}")])
        
        mod_name = user_session[user_id].get("mod_name", "")
        buttons.append([InlineKeyboardButton("🔙 Back to Upload", callback_data=f"fb_set_mod_{module_id}|{mod_name}")])
        
        await query.message.edit_text(
            f"**🗑️ Manage Content**\n\nClick an item to **Rename** or **Delete**:", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await query.message.edit_text(f"❌ Error: {e}")

@Client.on_callback_query(filters.regex("^fb_item_opt_"))
async def item_options(bot, query: CallbackQuery):
    key = query.data.split("_")[3]
    user_id = query.from_user.id
    mod_id = user_session[user_id]["module_id"]
    
    buttons = [
        [InlineKeyboardButton("✏️ Rename Item", callback_data=f"fb_edit_ask_{key}")],
        [InlineKeyboardButton("🗑️ Delete Permanently", callback_data=f"fb_del_{key}")],
        [InlineKeyboardButton("🔙 Back to List", callback_data=f"fb_manage_{mod_id}")]
    ]
    await query.message.edit_text(
        f"⚙️ **Options for ID:** `{key}`\nSelect action:", 
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^fb_del_"))
async def delete_item(bot, query: CallbackQuery):
    key = query.data.split("_")[2]
    user_id = query.from_user.id
    cat, batch, mod = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["module_id"]
    
    db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(key).remove()
    
    await query.answer("🗑️ Item Deleted Successfully!", show_alert=True)
    query.data = f"fb_manage_{mod}"
    await manage_content_list(bot, query)

@Client.on_callback_query(filters.regex("^fb_edit_ask_"))
async def edit_ask(bot, query: CallbackQuery):
    key = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["state"] = f"waiting_edit_{key}"
    
    buttons = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"fb_manage_{user_session[user_id]['module_id']}")]]
    await query.message.edit_text(
        f"✏️ **Rename Mode**\n\nSend the **New Name** for this item now:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- File Handler ---
@Client.on_message((filters.video | filters.document | filters.audio) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    
    # Check if active
    if user_session.get(user_id, {}).get("state") != "active_firebase":
        return

    msg = await message.reply("🔄 **Processing...**")
    stream_link, clean_name = await get_stream_link(message)
    
    if not stream_link: 
        return await msg.edit("❌ Error generating link.")

    # Fast Mode Logic
    if user_session[user_id].get("fast_mode"):
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        def_type = user_session[user_id]["default_type"]
        target = "lectures" if def_type == "lec" else "resources"
        
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
        ref = path.push({"name": clean_name, "link": stream_link, "order": ts})
        
        # Add ID back to node
        key = ref['name']
        path.child(key).update({"id": key})
        
        await msg.edit(f"⚡ **Fast Added:** `{clean_name}`")
        return

    # Normal Mode Logic
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    
    buttons = [
        [InlineKeyboardButton("✅ Add with this Name", callback_data="fb_name_keep")],
        [InlineKeyboardButton("✏️ Rename First", callback_data="fb_name_rename")],
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_clear_temp")] # Simply clears temp, keeps session
    ]
    await msg.edit(
        f"📂 **File Prepared!**\n\n"
        f"📜 **Name:** `{clean_name}`\n\n"
        f"How do you want to proceed?", 
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Text Handler ---
@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state", "")
    
    # Handling Rename
    if state.startswith("waiting_edit_"):
        key = state.split("_")[2]
        new_name = message.text.strip()
        cat, batch, mod = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["module_id"]
        
        db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(key).update({"name": new_name})
        
        await message.reply_text(f"✅ **Renamed Successfully!**\nNew Name: `{new_name}`")
        user_session[user_id]["state"] = "active_firebase"
        
        # Optionally show manage menu again
        # ... logic to show menu ...

    # Handling Upload Rename
    elif state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, new_name, user_session[user_id]["temp_data"]["url"])

    # Handling New Module Creation
    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ref = path.push({"name": mod_name, "order": ts})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"✅ **Module Created:** `{mod_name}`")
        user_session[user_id]["state"] = "idle"
        # Force refresh modules would be ideal here, but manual back button works

    # Handling URL Mode
    elif user_session[user_id].get("mode") == "url" and state == "active_firebase":
        await direct_url_logic(bot, message)

# --- Logic for Normal Upload ---
@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_default_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"], data["url"])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def ask_for_rename_manual(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **Enter New Name:**\n\nReply with the text you want.")

async def ask_file_type(message, title, url):
    buttons = [
        [InlineKeyboardButton("🎬 Lecture", callback_data="fb_confirm_lec"), 
         InlineKeyboardButton("📄 Resource", callback_data="fb_confirm_res")]
    ]
    if isinstance(message, Message):
        await message.reply_text(f"📌 **Categorize:** `{title}`", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.edit_text(f"📌 **Categorize:** `{title}`", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_firebase_manual(bot, query: CallbackQuery):
    action = query.data.split("_")[2]
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    
    cat, batch, mod = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["module_id"]
    target = "lectures" if action == "lec" else "resources"
    ts = int(time.time() * 1000)
    
    entry = {"name": data["title"], "link": data["url"], "order": ts}
    
    try:
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
        ref = path.push(entry)
        key = ref['name']
        path.child(key).update({"id": key})
        
        await query.message.edit_text(
            f"✅ **Successfully Added!**\n\n📌 **Key:** `{key}`", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Hide", callback_data="fb_hide_msg")]])
        )
    except Exception as e:
        await query.message.edit_text(f"❌ Error: {e}")

# --- Utilities ---

@Client.on_callback_query(filters.regex("^fb_hide_msg"))
async def hide_msg(bot, query: CallbackQuery):
    await query.message.delete()

@Client.on_callback_query(filters.regex("^fb_clear_session"))
async def clear_s(bot, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in user_session: del user_session[user_id]
    await query.message.edit_text("🛑 **Session Ended.**\n\nDatabase disconnected safely.")

@Client.on_callback_query(filters.regex("^fb_mode_menu"))
async def mode_menu(bot, query: CallbackQuery):
    buttons = [
        [InlineKeyboardButton("📂 File Mode (Default)", callback_data="fb_setmode_file")],
        [InlineKeyboardButton("🔗 Direct URL Mode", callback_data="fb_setmode_url")]
    ]
    await query.message.edit_text("⚙️ **Input Mode Selection:**", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_setmode_"))
async def set_mode(bot, query: CallbackQuery):
    mode = query.data.split("_")[2]
    user_id = query.from_user.id
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["mode"] = mode
    await query.answer(f"✅ Mode switched to: {mode.upper()}")
    await query.message.delete()

async def direct_url_logic(bot, message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if "|" in text: 
        title, url = text.split("|", 1)
    else: 
        title, url = "External Link", text
    
    user_session[user_id]["temp_data"] = {"title": title.strip(), "url": url.strip()}
    await ask_file_type(message, title.strip(), url.strip())

@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_trig(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("🆕 **Create Module**\n\nSend the Name for the new module:")
