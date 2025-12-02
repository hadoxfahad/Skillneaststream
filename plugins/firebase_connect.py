import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import *
import pyrebase

# --- 1. Firebase Configuration ---
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
# {user_id: {"cat_id": "...", "batch_id": "...", "module_id": "...", "fast_mode": False, "default_type": "lec"}}
user_session = {} 

# --- Helper Functions ---

async def get_stream_link(message: Message):
    """Generates Direct Link & Cleans Filename"""
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        
        if message.video:
            file_name = message.video.file_name or f"Video {log_msg.id}.mp4"
        elif message.document:
            file_name = message.document.file_name or f"File {log_msg.id}.pdf"
        else:
            file_name = f"File {log_msg.id}"
            
        # Clean Name: Remove Extension & Underscores
        name_without_ext = os.path.splitext(file_name)[0]
        clean_name = name_without_ext.replace("_", " ")
        
        # URL Generation
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name, log_msg.id
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None, None

def get_name(data):
    if not data: return "Unnamed"
    return data.get("name") or data.get("title") or data.get("description") or "Unnamed"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    user_session[user_id] = {"state": "idle", "fast_mode": False}
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!\nSelect a Category to start:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Switch Mode", callback_data="fb_mode_menu")]
        ])
    )

# --- Navigation ---

# 1. Categories
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        cats = db.child("categories").get()
        buttons = []
        if cats.each():
            for cat in cats.each():
                c_name = get_name(cat.val())
                buttons.append([InlineKeyboardButton(f"📂 {c_name}", callback_data=f"fb_sel_cat_{cat.key()}")])
        
        await query.message.edit_text("**📂 Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# 2. Batches
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["cat_id"] = cat_id
    
    try:
        batches = db.child("categories").child(cat_id).child("batches").get()
        buttons = []
        if batches.each():
            for batch in batches.each():
                b_name = get_name(batch.val())
                buttons.append([InlineKeyboardButton(f"🎓 {b_name}", callback_data=f"fb_sel_batch_{batch.key()}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**📂 Category ID:** `{cat_id}`\n\nSelect a **Batch**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# 3. Modules
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    cat_id = user_session[user_id].get("cat_id")
    user_session[user_id]["batch_id"] = batch_id
    
    try:
        modules_ref = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get()
        buttons = []
        if modules_ref.each():
            for mod in modules_ref.each():
                m_name = get_name(mod.val())
                buttons.append([InlineKeyboardButton(f"📺 {m_name}", callback_data=f"fb_set_mod_{mod.key()}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        
        await query.message.edit_text(f"**🎓 Batch ID:** `{batch_id}`\n\nSelect a **Module**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error: {e}")

# 4. Set Module (Dashboard)
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["state"] = "active_firebase"
    
    # Check if Fast Mode is ON
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    buttons = [
        [InlineKeyboardButton("✏️ Manage Content (Edit/Del)", callback_data=f"fb_manage_{module_id}")],
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("❌ Stop / Cancel", callback_data="fb_clear_session")]
    ]

    await query.message.edit_text(
        f"✅ **Target Set!**\n\n"
        f"📂 **Category:** `{user_session[user_id]['cat_id']}`\n"
        f"🎓 **Batch:** `{user_session[user_id]['batch_id']}`\n"
        f"📺 **Module:** `{module_id}`\n\n"
        f"⚡ **Fast Mode:** {fast_status}\n\n"
        f"⬇️ **Send Files Now:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- FEATURE: Fast Mode Toggle ---
@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    
    # Toggle state
    current_status = user_session[user_id].get("fast_mode", False)
    
    if not current_status:
        # Enable karne se pehle Default Type pucho
        buttons = [
            [InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"),
             InlineKeyboardButton("📄 Resources", callback_data="fb_set_fast_res")]
        ]
        await query.message.edit_text("**⚡ Fast Mode Setup**\n\nJo files aap bhejenge wo by default kya hongi?", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        # Disable
        user_session[user_id]["fast_mode"] = False
        await set_active_module(bot, query) # Refresh Dashboard

@Client.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(bot, query: CallbackQuery):
    user_id = query.from_user.id
    type_ = query.data.split("_")[3] # lec or res
    
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = type_
    
    await query.answer("⚡ Fast Mode Enabled!", show_alert=True)
    
    # Fake a query to refresh dashboard using stored module ID
    # Note: query.data format reuse for refresh
    mod_id = user_session[user_id]["module_id"]
    query.data = f"fb_set_mod_{mod_id}"
    await set_active_module(bot, query)

# --- FEATURE: Manage Content (List/Delete/Edit) ---
@Client.on_callback_query(filters.regex("^fb_manage_"))
async def manage_content_list(bot, query: CallbackQuery):
    module_id = query.data.split("_")[2]
    user_id = query.from_user.id
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    
    try:
        # Fetch lectures
        lectures = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(module_id).child("lectures").get()
        
        buttons = []
        if lectures.each():
            for l in lectures.each():
                name = get_name(l.val())
                key = l.key()
                # Button format: Name -> leads to options
                buttons.append([InlineKeyboardButton(f"📝 {name}", callback_data=f"fb_item_opt_{key}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back to Upload", callback_data=f"fb_set_mod_{module_id}")])
        
        await query.message.edit_text(f"**🗑 Manage Content**\n\nClick on any item to **Edit** or **Delete**:", reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_item_opt_"))
async def item_options(bot, query: CallbackQuery):
    key = query.data.split("_")[3]
    user_id = query.from_user.id
    mod_id = user_session[user_id]["module_id"]
    
    buttons = [
        [InlineKeyboardButton("🗑 Delete Permanently", callback_data=f"fb_del_{key}")],
        [InlineKeyboardButton("✏️ Rename (Edit)", callback_data=f"fb_edit_ask_{key}")],
        [InlineKeyboardButton("🔙 Back to List", callback_data=f"fb_manage_{mod_id}")]
    ]
    
    await query.message.edit_text(f"**⚙️ Options for Item ID:** `{key}`\nSelect Action:", reply_markup=InlineKeyboardMarkup(buttons))

# -- Delete Logic --
@Client.on_callback_query(filters.regex("^fb_del_"))
async def delete_item(bot, query: CallbackQuery):
    key = query.data.split("_")[2]
    user_id = query.from_user.id
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(key).remove()
    
    await query.answer("🗑 Deleted!", show_alert=True)
    # Return to list
    query.data = f"fb_manage_{mod}"
    await manage_content_list(bot, query)

# -- Edit Logic --
@Client.on_callback_query(filters.regex("^fb_edit_ask_"))
async def edit_ask(bot, query: CallbackQuery):
    key = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["state"] = f"waiting_edit_{key}"
    await query.message.edit_text(f"✏️ **Send New Name** for this item:")

# --- FILE HANDLER (Enhanced for Fast Mode) ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    # Normal Link Gen
    stream_link, clean_name, log_id = await get_stream_link(message)
    if not stream_link: return await message.reply("Error.")

    # Check Firebase State
    is_active = user_session.get(user_id, {}).get("state") == "active_firebase"
    
    # 1. Normal Mode (No Firebase)
    if not is_active:
        text = f"✅ **Link Generated!**\n📄 `{clean_name}`\n🔗 `{stream_link}`"
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔥 Add to Firebase", callback_data="fb_cat_list")]]), disable_web_page_preview=True)
        return

    # 2. Firebase - FAST MODE
    if user_session[user_id].get("fast_mode"):
        # Auto Upload Logic
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        def_type = user_session[user_id]["default_type"] # lec or res
        
        target_node = "lectures" if def_type == "lec" else "resources"
        timestamp = int(time.time() * 1000)
        
        entry = {"name": clean_name, "link": stream_link, "order": timestamp}
        
        # Non-blocking Upload (Fast)
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target_node)
        push_ref = path.push(entry)
        key = push_ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"⚡ **Added:** `{clean_name}` to {target_node.upper()}")
        return

    # 3. Firebase - NORMAL MODE (Manual Confirm)
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    
    buttons = [
        [InlineKeyboardButton("✅ Add (Keep Name)", callback_data="fb_name_keep")],
        [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")],
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_clear_session")]
    ]
    await message.reply_text(f"📂 **Ready to Add:** `{clean_name}`\nRename or Keep?", reply_markup=InlineKeyboardMarkup(buttons))

# --- TEXT HANDLER (Edit, Rename, Create) ---
@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state", "")
    
    # 1. Edit Existing Item Name
    if state.startswith("waiting_edit_"):
        key = state.split("_")[2]
        new_name = message.text.strip()
        
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        
        db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(key).update({"name": new_name})
        
        await message.reply_text(f"✅ **Renamed Successfully!**")
        user_session[user_id]["state"] = "active_firebase"
        
        # Show list again
        # Note: Can't easily trigger callback, giving text prompt
        await message.reply_text("Click Manage Content again to see changes.")

    # 2. Rename New Upload
    elif state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, new_name, user_session[user_id]["temp_data"]["url"], user_session[user_id])

    # 3. Create Module
    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ref = path.push({"name": mod_name, "order": ts})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"✅ Created: {mod_name}")
        user_session[user_id]["state"] = "idle"

    # 4. URL Mode
    elif user_session[user_id].get("mode") == "url" and "module_id" in user_session[user_id]:
        await direct_url_logic(bot, message)

# --- STANDARD CALLBACKS (Same as before) ---
@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_default_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"], data["url"], user_session[user_id])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def ask_for_rename_manual(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **New Name:**")

async def ask_file_type(message, title, url, session):
    buttons = [[InlineKeyboardButton("🎬 Lecture", callback_data="fb_confirm_lec"), InlineKeyboardButton("📄 Resource", callback_data="fb_confirm_res")]]
    await message.reply_text(f"📌 **Confirm:**\nName: `{title}`", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_firebase_manual(bot, query: CallbackQuery):
    action = query.data.split("_")[2]
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    target = "lectures" if action == "lec" else "resources"
    ts = int(time.time() * 1000)
    
    entry = {"name": data["title"], "link": data["url"], "order": ts}
    
    path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
    ref = path.push(entry)
    key = ref['name']
    path.child(key).update({"id": key})
    
    await query.message.edit_text(f"✅ **Added!**\nKey: `{key}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Next", callback_data="fb_clear_session")]]))

@Client.on_callback_query(filters.regex("^fb_clear_session"))
async def clear_s(bot, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in user_session: del user_session[user_id]
    await query.message.edit_text("✅ Stopped.")

# --- URL Mode Logic ---
@Client.on_callback_query(filters.regex("^fb_mode_menu"))
async def mode_menu(bot, query: CallbackQuery):
    await query.message.edit_text("Select Mode:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📂 File", callback_data="fb_setmode_file"), InlineKeyboardButton("🔗 URL", callback_data="fb_setmode_url")]]))

@Client.on_callback_query(filters.regex("^fb_setmode_"))
async def set_mode(bot, query: CallbackQuery):
    mode = query.data.split("_")[2]
    user_id = query.from_user.id
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["mode"] = mode
    await query.answer(f"Mode: {mode}")

async def direct_url_logic(bot, message):
    # Same simplified logic as before for URL inputs
    user_id = message.from_user.id
    text = message.text.strip()
    if "|" in text: title, url = text.split("|", 1)
    else: title, url = "External", text
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    ts = int(time.time() * 1000)
    
    path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures")
    ref = path.push({"name": title.strip(), "link": url.strip(), "order": ts})
    key = ref['name']
    path.child(key).update({"id": key})
    await message.reply_text(f"✅ URL Added: {title}")

# Create Module Handler (Initial trigger)
@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_trig(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("🆕 **Enter Name:**")
