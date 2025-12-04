import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import *  # Ensure this file exists with API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL, STREAM_URL, ADMINS
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
# user_id: {
#   "cat_id": "...", "batch_id": "...", "module_id": "...",
#   "current_context": "module" or "sub_module",
#   "sub_module_id": "...", "sub_module_section": "lectures" or "resources",
#   "fast_mode": True/False, "default_type": "lectures"/"resources"
# }
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
            
        # Clean Name
        name_without_ext = os.path.splitext(file_name)[0]
        clean_name = name_without_ext.replace("_", " ")
        
        # Safe URL
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name, log_msg.id
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None, None

def get_name(data):
    if not data: return "Unnamed"
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or "Unnamed"
    return "Unnamed"

def get_current_path_text(user_id):
    """Returns a readable string of where files will be uploaded"""
    s = user_session.get(user_id, {})
    txt = f"📂 **Cat:** `{s.get('cat_id')}`\n🎓 **Batch:** `{s.get('batch_id')}`\n📺 **Module:** `{s.get('module_id')}`"
    
    if s.get("current_context") == "sub_module":
        txt += f"\n⤵️ **Sub-Module:** `{s.get('sub_module_name', 'Unknown')}`\n(Inside `{s.get('sub_module_section')}`)"
    return txt

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    user_session[user_id] = {"state": "idle", "fast_mode": False, "current_context": "module"}
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!\nSelect a Category to start:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")]
        ])
    )

# --- Navigation ---

# 1. Categories
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    cats_data = db.child("categories").get().val()
    buttons = []
    if cats_data and isinstance(cats_data, dict):
        for key, val in cats_data.items():
            buttons.append([InlineKeyboardButton(f"📂 {get_name(val)}", callback_data=f"fb_sel_cat_{key}")])
    
    await query.message.edit_text("**📂 Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))

# 2. Batches
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id].update({"cat_id": cat_id, "state": "idle"})
    
    batches_data = db.child("categories").child(cat_id).child("batches").get().val()
    buttons = []
    if batches_data and isinstance(batches_data, dict):
        for key, val in batches_data.items():
            if isinstance(val, dict):
                buttons.append([InlineKeyboardButton(f"🎓 {get_name(val)}", callback_data=f"fb_sel_batch_{key}")])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
    await query.message.edit_text(f"**📂 Category ID:** `{cat_id}`\nSelect Batch:", reply_markup=InlineKeyboardMarkup(buttons))

# 3. Modules
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    cat_id = user_session[user_id]["cat_id"]
    user_session[user_id]["batch_id"] = batch_id
    
    modules_data = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get().val()
    buttons = []
    if modules_data:
        # Handle dict or list
        iterable = modules_data.items() if isinstance(modules_data, dict) else enumerate(modules_data)
        for key, val in iterable:
            if val and isinstance(val, dict):
                buttons.append([InlineKeyboardButton(f"📺 {get_name(val)}", callback_data=f"fb_set_mod_{key}")])
    
    buttons.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
    await query.message.edit_text(f"**🎓 Batch ID:** `{batch_id}`\nSelect Module:", reply_markup=InlineKeyboardMarkup(buttons))

# 4. Module Dashboard (The Hub)
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    # Reset to Module Context
    user_session[user_id].update({
        "module_id": module_id,
        "current_context": "module",
        "state": "active_firebase",
        "sub_module_id": None
    })
    
    # UI Logic
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    buttons = [
        [InlineKeyboardButton("📂 Show/Select Sub-Modules", callback_data=f"fb_list_subs_{module_id}")],
        [InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_ask_sub_create")],
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🔙 Back to Modules", callback_data=f"fb_sel_batch_{user_session[user_id]['batch_id']}")]
    ]

    await query.message.edit_text(
        f"✅ **Module Selected!**\n\n{get_current_path_text(user_id)}\n\n"
        f"⚡ **Fast Mode:** {fast_status}\n"
        f"⬇️ **Send Files to add to Module Root** or select a Sub-Module.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Sub-Module Logic ---

@Client.on_callback_query(filters.regex("^fb_list_subs_"))
async def list_sub_modules(bot, query: CallbackQuery):
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    buttons = []
    
    # Fetch from Lectures and Resources to find submodules
    base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
    lecs = base_path.child("lectures").get().val() or {}
    ress = base_path.child("resources").get().val() or {}
    
    # Helper to parse
    def add_subs(data, section):
        if isinstance(data, dict):
            for key, val in data.items():
                if val.get("isSubModule") == True:
                    name = get_name(val)
                    buttons.append([InlineKeyboardButton(f"📂 {name} ({section})", callback_data=f"fb_enter_sub_{section}_{key}")])

    add_subs(lecs, "lectures")
    add_subs(ress, "resources")
    
    if not buttons:
        buttons.append([InlineKeyboardButton("🚫 No Sub-modules found", callback_data="ignore")])
    
    buttons.append([InlineKeyboardButton("🔙 Back to Module", callback_data=f"fb_set_mod_{mod}")])
    await query.message.edit_text("**📂 Select a Sub-Module to Open:**", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_enter_sub_"))
async def enter_sub_module(bot, query: CallbackQuery):
    _, _, section, key = query.data.split("_")
    user_id = query.from_user.id
    
    # Fetch name for UI
    cat, batch, mod = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["module_id"]
    data = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(section).child(key).get().val()
    name = get_name(data)
    
    user_session[user_id].update({
        "current_context": "sub_module",
        "sub_module_id": key,
        "sub_module_section": section,
        "sub_module_name": name,
        "state": "active_firebase"
    })
    
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    buttons = [
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🔙 Back to Module Root", callback_data=f"fb_set_mod_{mod}")]
    ]
    
    await query.message.edit_text(
        f"✅ **Inside Sub-Module: {name}**\n\n"
        f"📂 Section: `{section}`\n"
        f"⚡ **Fast Mode:** {fast_status}\n\n"
        f"⬇️ **Send Files now to add INSIDE this Sub-Module.**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Creation Logic (Module & Sub-module) ---

@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def ask_mod_name(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_mod_name"
    await query.message.edit_text("🆕 **Enter Name for New Module:**")

@Client.on_callback_query(filters.regex("^fb_ask_sub_create"))
async def ask_sub_mod_name(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_sub_name"
    await query.message.edit_text("🆕 **Enter Name for New Sub-Module:**")

# --- Fast Mode Toggle ---
@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast(bot, query: CallbackQuery):
    user_id = query.from_user.id
    curr = user_session[user_id].get("fast_mode", False)
    
    if not curr:
        # Ask for default type (Lecture/Resource)
        buttons = [[InlineKeyboardButton("🎬 As Lecture", callback_data="fb_setfast_lectures"), InlineKeyboardButton("📄 As Resource", callback_data="fb_setfast_resources")]]
        await query.message.edit_text("**⚡ Setup Fast Mode**\n\nDefault upload type?", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        user_session[user_id]["fast_mode"] = False
        await refresh_dashboard(bot, query)

@Client.on_callback_query(filters.regex("^fb_setfast_"))
async def set_fast_type(bot, query: CallbackQuery):
    t = query.data.split("_")[2]
    user_id = query.from_user.id
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = t
    await query.answer("⚡ Fast Mode ON!")
    await refresh_dashboard(bot, query)

async def refresh_dashboard(bot, query):
    # Determine where to go back based on context
    uid = query.from_user.id
    if user_session[uid].get("current_context") == "sub_module":
        sec = user_session[uid]["sub_module_section"]
        key = user_session[uid]["sub_module_id"]
        query.data = f"fb_enter_sub_{sec}_{key}"
        await enter_sub_module(bot, query)
    else:
        mod = user_session[uid]["module_id"]
        query.data = f"fb_set_mod_{mod}"
        await set_active_module(bot, query)

# --- File Handler (The Core Logic) ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session or user_session[user_id].get("state") != "active_firebase":
        return
    
    stream_link, clean_name, _ = await get_stream_link(message)
    if not stream_link: return await message.reply("Failed to process file.")
    
    # Prepare Data
    ts = int(time.time() * 1000)
    file_data = {"name": clean_name, "link": stream_link, "order": ts}
    
    # Fast Mode Check
    if user_session[user_id].get("fast_mode"):
        await push_to_firebase(bot, message, user_id, file_data, user_session[user_id]["default_type"])
    else:
        # Ask User
        user_session[user_id]["temp_file"] = file_data
        buttons = [
            [InlineKeyboardButton("🎬 Add as Lecture", callback_data="fb_confirm_upload_lectures")],
            [InlineKeyboardButton("📄 Add as Resource", callback_data="fb_confirm_upload_resources")],
            [InlineKeyboardButton("✏️ Rename", callback_data="fb_ask_rename")]
        ]
        await message.reply_text(f"📂 **File:** `{clean_name}`\n\nWhere to add this?", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_confirm_upload_"))
async def manual_upload_confirm(bot, query: CallbackQuery):
    type_ = query.data.split("_")[3]
    user_id = query.from_user.id
    data = user_session[user_id]["temp_file"]
    await push_to_firebase(bot, query.message, user_id, data, type_)
    await query.message.delete()

async def push_to_firebase(bot, message, user_id, data, type_str):
    """Handles logic for Module vs Sub-Module pathing"""
    s = user_session[user_id]
    cat, batch, mod = s["cat_id"], s["batch_id"], s["module_id"]
    
    # Define Path
    if s.get("current_context") == "sub_module":
        # Path: modules/{mod}/{sub_section}/{sub_id}/content (or create a 'list' inside)
        # Based on user req: "lecture resource usme hi add ho"
        sub_sec = s["sub_module_section"]
        sub_id = s["sub_module_id"]
        
        # We create a nested structure for content inside the sub-module
        # NOTE: Screenshot structure implies Sub-module is an item. We add children to it.
        # Let's call the children node 'content' or reuse 'lectures'/'resources' if you want deep nesting.
        # To keep it simple and working: we add to a 'content' node inside the sub-module.
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(sub_sec).child(sub_id).child("content")
    else:
        # Normal Module Path
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(type_str)

    try:
        ref = path.push(data)
        key = ref['name']
        path.child(key).update({"id": key})
        
        loc = "Sub-Module" if s.get("current_context") == "sub_module" else "Module"
        await message.reply_text(f"✅ **Added to {loc}!**\n📄 `{data['name']}`")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# --- Text Handler (Renaming & Creating) ---

@Client.on_message(filters.text & filters.user(ADMINS))
async def text_handler(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    
    state = user_session[user_id].get("state")
    text = message.text.strip()
    ts = int(time.time() * 1000)
    
    if state == "waiting_mod_name":
        # Create Module
        cat, batch = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"]
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ref = path.push({"name": text, "order": ts})
        path.child(ref['name']).update({"id": ref['name']})
        await message.reply_text(f"✅ Module **{text}** Created!")
        user_session[user_id]["state"] = "idle" # Force user to refresh list
    
    elif state == "waiting_sub_name":
        # Step 1 of Sub-mod creation: Got Name, Ask Section
        user_session[user_id]["temp_sub_name"] = text
        buttons = [
            [InlineKeyboardButton("🎬 In Lectures", callback_data="fb_save_sub_lectures")],
            [InlineKeyboardButton("📄 In Resources", callback_data="fb_save_sub_resources")]
        ]
        await message.reply_text(f"📝 Name: `{text}`\nWhere should this Sub-Module be created?", reply_markup=InlineKeyboardMarkup(buttons))
        user_session[user_id]["state"] = "waiting_sub_section"

    elif state == "waiting_rename":
        user_session[user_id]["temp_file"]["name"] = text
        user_session[user_id]["state"] = "active_firebase"
        # Go back to ask type
        buttons = [
            [InlineKeyboardButton("🎬 Add as Lecture", callback_data="fb_confirm_upload_lectures")],
            [InlineKeyboardButton("📄 Add as Resource", callback_data="fb_confirm_upload_resources")]
        ]
        await message.reply_text(f"✏️ Renamed to: `{text}`\nConfirm type:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_save_sub_"))
async def save_sub_module(bot, query: CallbackQuery):
    section = query.data.split("_")[3]
    user_id = query.from_user.id
    name = user_session[user_id]["temp_sub_name"]
    cat, batch, mod = user_session[user_id]["cat_id"], user_session[user_id]["batch_id"], user_session[user_id]["module_id"]
    ts = int(time.time() * 1000)
    
    data = {
        "name": name,
        "isSubModule": True,
        "order": ts
    }
    
    path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(section)
    ref = path.push(data)
    path.child(ref['name']).update({"id": ref['name']})
    
    user_session[user_id]["state"] = "active_firebase"
    # Return to dashboard
    query.data = f"fb_set_mod_{mod}"
    await set_active_module(bot, query)
    await query.message.reply_text(f"✅ Sub-Module **{name}** created in {section}!")

@Client.on_callback_query(filters.regex("^fb_ask_rename"))
async def ask_rename(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_rename"
    await query.message.edit_text("✏️ **Send New Name:**")
