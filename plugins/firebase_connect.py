import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import pyrebase
from info import *  # Ensure ADMINS, LOG_CHANNEL, STREAM_URL exist here

# --- 1. Firebase Configuration ---
firebaseConfig = {
    "apiKey": "AIzaSyChwpbFb6M4HtG6zwjg0AXh7Lz9KjnrGZk", # Replace with yours
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

# Session Structure to track user navigation
user_session = {} 

# --- Helper Functions ---

def get_name(data):
    """Safely extract name from Firebase data"""
    if not data: return "Unnamed"
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or "Unnamed"
    return "Unnamed"

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
            
        name_without_ext = os.path.splitext(file_name)[0]
        # Clean filename for display
        clean_name = name_without_ext.replace("_", " ").replace(".", " ").strip()
        
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name, log_msg.id
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None, None

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    # Reset Session
    user_session[user_id] = {
        "state": "idle", 
        "fast_mode": False, 
        "is_sub_module": False, # Flag to check if we are inside a sub-module
        "sub_mod_id": None
    }
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!\nSelect a Category to start:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")]
        ])
    )

# --- Navigation System ---

# 1. List Categories
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        cats_data = db.child("categories").get().val()
        buttons = []
        
        if cats_data:
            if isinstance(cats_data, dict):
                for key, val in cats_data.items():
                    buttons.append([InlineKeyboardButton(f"📂 {get_name(val)}", callback_data=f"fb_sel_cat_{key}")])
            elif isinstance(cats_data, list):
                for i, val in enumerate(cats_data):
                    if val: buttons.append([InlineKeyboardButton(f"📂 {get_name(val)}", callback_data=f"fb_sel_cat_{i}")])
        
        await query.message.edit_text("**📂 Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error fetching categories: {e}")

# 2. List Batches
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["cat_id"] = cat_id
    
    try:
        batches_data = db.child("categories").child(cat_id).child("batches").get().val()
        buttons = []
        
        if batches_data:
            if isinstance(batches_data, dict):
                for key, val in batches_data.items():
                    if isinstance(val, dict):
                        buttons.append([InlineKeyboardButton(f"🎓 {get_name(val)}", callback_data=f"fb_sel_batch_{key}")])
            elif isinstance(batches_data, list):
                for i, val in enumerate(batches_data):
                    if val and isinstance(val, dict):
                        buttons.append([InlineKeyboardButton(f"🎓 {get_name(val)}", callback_data=f"fb_sel_batch_{i}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**📂 Category ID:** `{cat_id}`\n\nSelect a **Batch**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# 3. List Modules
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    cat_id = user_session[user_id].get("cat_id")
    user_session[user_id]["batch_id"] = batch_id
    
    try:
        modules_data = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get().val()
        buttons = []
        
        if modules_data:
            if isinstance(modules_data, dict):
                for key, val in modules_data.items():
                    if isinstance(val, dict):
                        # Goes to Module Menu (Submodule selection logic)
                        buttons.append([InlineKeyboardButton(f"📺 {get_name(val)}", callback_data=f"fb_mod_menu_{key}")])
            elif isinstance(modules_data, list):
                for i, val in enumerate(modules_data):
                    if val and isinstance(val, dict):
                        buttons.append([InlineKeyboardButton(f"📺 {get_name(val)}", callback_data=f"fb_mod_menu_{i}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        
        await query.message.edit_text(f"**🎓 Batch ID:** `{batch_id}`\n\nSelect a **Module**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error: {e}")

# --- 4. Sub-Module & Module Selection Logic (Crucial Part) ---

@Client.on_callback_query(filters.regex("^fb_mod_menu_"))
async def module_menu_handler(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    # Set Module ID and reset sub-module flags
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["is_sub_module"] = False
    user_session[user_id]["sub_mod_id"] = None
    
    buttons = [
        # Option A: Upload directly to this Module
        [InlineKeyboardButton("✅ Select This Module", callback_data=f"fb_set_final_main")],
        # Option B: Check Sub-modules
        [InlineKeyboardButton("📂 Show Sub-Modules", callback_data=f"fb_list_submod_{module_id}")],
        # Option C: Create Sub-module
        [InlineKeyboardButton("➕ Create Sub-Module", callback_data=f"fb_create_submod_ask")],
        
        [InlineKeyboardButton("🔙 Back to Modules", callback_data=f"fb_sel_batch_{user_session[user_id]['batch_id']}")]
    ]
    
    await query.message.edit_text(f"**📺 Module Selected:** `{module_id}`\n\nChoose Action:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_list_submod_"))
async def list_sub_modules(bot, query: CallbackQuery):
    mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    
    try:
        # Fetching subModules from Firebase
        sub_mods = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod_id).child("subModules").get().val()
        buttons = []
        
        if sub_mods and isinstance(sub_mods, dict):
            for key, val in sub_mods.items():
                # On click -> Sets this sub-module as target
                buttons.append([InlineKeyboardButton(f"📑 {get_name(val)}", callback_data=f"fb_set_submod_{key}")])
        
        if not buttons:
            buttons.append([InlineKeyboardButton("🚫 No Sub-Modules Found", callback_data="ignore")])
            
        buttons.append([InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_create_submod_ask")])
        buttons.append([InlineKeyboardButton("🔙 Back to Menu", callback_data=f"fb_mod_menu_{mod_id}")])
        
        await query.message.edit_text("**📂 Sub-Modules List**\nSelect one to upload inside it:", reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        await query.message.edit_text(f"Error loading Sub-modules: {e}")

# --- 5. Setting the Active Target (Dashboard) ---

@Client.on_callback_query(filters.regex("^fb_set_final_main"))
async def set_main_module_active(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["is_sub_module"] = False
    user_session[user_id]["sub_mod_id"] = None
    await show_dashboard(bot, query, "Main Module")

@Client.on_callback_query(filters.regex("^fb_set_submod_"))
async def set_sub_module_active(bot, query: CallbackQuery):
    sub_mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["is_sub_module"] = True
    user_session[user_id]["sub_mod_id"] = sub_mod_id
    
    await show_dashboard(bot, query, "Sub-Module")

async def show_dashboard(bot, query, type_name):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "active_firebase"
    
    mod_id = user_session[user_id]["module_id"]
    sub_id = user_session[user_id].get("sub_mod_id", "None")
    
    # Fast Mode UI
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    text = (
        f"✅ **Target Set: {type_name}**\n\n"
        f"📺 **Module:** `{mod_id}`\n"
    )
    if user_session[user_id]["is_sub_module"]:
        text += f"📑 **Sub-Module:** `{sub_id}`\n"
        
    text += f"\n⚡ **Fast Mode:** {fast_status}\n⬇️ **Send Files/Videos Now to Save:**"
    
    buttons = [
        [InlineKeyboardButton("✏️ Manage Content (Delete)", callback_data=f"fb_manage_idx")],
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🔙 Back to Module", callback_data=f"fb_mod_menu_{mod_id}")]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# --- 6. Fast Mode & Management ---

@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    current = user_session[user_id].get("fast_mode", False)
    
    if not current:
        buttons = [[InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"), InlineKeyboardButton("📄 Resources", callback_data="fb_set_fast_res")]]
        await query.message.edit_text("**⚡ Fast Mode Setup**\n\nAutomatic Upload kahan karein?", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        user_session[user_id]["fast_mode"] = False
        type_name = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
        await show_dashboard(bot, query, type_name)

@Client.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(bot, query: CallbackQuery):
    user_id = query.from_user.id
    type_ = query.data.split("_")[3]
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = type_
    
    await query.answer("⚡ Fast Mode Enabled!", show_alert=True)
    type_name = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
    await show_dashboard(bot, query, type_name)

@Client.on_callback_query(filters.regex("^fb_manage_idx"))
async def manage_content_list(bot, query: CallbackQuery):
    # This lists items to delete. Can be expanded based on need.
    await query.answer("Feature available in full version (Code omitted for brevity)", show_alert=True)

# --- 7. FILE HANDLER (Main Logic for Saving) ---
# Ye function check karta hai ki Module hai ya Sub-Module aur wahi save karta hai.

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    # Check if user is in Active state
    if user_session.get(user_id, {}).get("state") != "active_firebase":
        return

    msg = await message.reply("⚙️ processing...")
    
    # 1. Generate Link
    stream_link, clean_name, log_id = await get_stream_link(message)
    if not stream_link:
        return await msg.edit("❌ Error generating link.")

    # 2. Path Construction (The most important part)
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    # Decide Base Path (Module vs Sub-Module)
    if user_session[user_id]["is_sub_module"]:
        sub_mod = user_session[user_id]["sub_mod_id"]
        # Path: .../modules/{mod}/subModules/{subMod}
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod)
        location_text = f"Sub-Module ({sub_mod})"
    else:
        # Path: .../modules/{mod}
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
        location_text = f"Module ({mod})"

    # 3. Fast Mode Handling
    if user_session[user_id].get("fast_mode"):
        def_type = user_session[user_id]["default_type"]
        target = "lectures" if def_type == "lec" else "resources"
        ts = int(time.time() * 1000)
        
        # Auto Create Path if not exists and Push Data
        path = base_path.child(target)
        ref = path.push({"name": clean_name, "link": stream_link, "order": ts})
        
        # Add 'id' key inside the node for frontend reference
        key = ref['name']
        path.child(key).update({"id": key})
        
        await msg.edit(f"⚡ **Fast Uploaded!**\n\n📂 **To:** {location_text}\n📁 **Folder:** {target}\n📄 **Name:** {clean_name}")
        return

    # 4. Normal Mode (Ask Name & Type)
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    
    buttons = [
        [InlineKeyboardButton("✅ Add (Default Name)", callback_data="fb_name_keep")], 
        [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")], 
        [InlineKeyboardButton("❌ Cancel", callback_data=f"fb_mod_menu_{mod}")]
    ]
    await msg.edit(f"📂 **File Processed**\n\n**Name:** `{clean_name}`\n**Location:** {location_text}\n\nRename or Add?", reply_markup=InlineKeyboardMarkup(buttons))

# --- 8. Text Handler (For Renaming & Creating) ---
@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text_input(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state", "")
    
    # A. Rename File
    if state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, new_name)

    # B. Create Module
    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ref = path.push({"name": mod_name, "order": ts})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"✅ Module Created: **{mod_name}**")
        user_session[user_id]["state"] = "idle"

    # C. Create Sub-Module
    elif state == "waiting_submod_creation":
        sub_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        ts = int(time.time() * 1000)
        
        # Creating inside subModules node
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules")
        ref = path.push({"name": sub_name, "order": ts, "isSubModule": True})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"✅ Sub-Module Created: **{sub_name}**\nGo back to the list to select it.")
        user_session[user_id]["state"] = "idle"

# --- 9. Final Steps (Callbacks for Manual Upload) ---

@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_default_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def ask_for_rename_manual(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **New Name send karein:**")

async def ask_file_type(message, title):
    buttons = [[InlineKeyboardButton("🎬 Lecture", callback_data="fb_confirm_lec"), InlineKeyboardButton("📄 Resource", callback_data="fb_confirm_res")]]
    await message.reply_text(f"📌 **Type Select Karein:**\nName: `{title}`", reply_markup=InlineKeyboardMarkup(buttons))

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
    
    try:
        # Determine Path Logic (Again)
        if user_session[user_id]["is_sub_module"]:
            sub_mod = user_session[user_id]["sub_mod_id"]
            path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod).child(target)
        else:
            path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
            
        # Push automatically creates structure if missing
        ref = path.push(entry)
        key = ref['name']
        path.child(key).update({"id": key})
        
        type_name = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
        
        buttons = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data=f"fb_mod_menu_{mod}")]]
        await query.message.edit_text(f"✅ **Added Successfully!**\n\n📂 **Location:** {type_name}\n📁 **Folder:** {target}", reply_markup=InlineKeyboardMarkup(buttons))
        
        # Reset temp data
        user_session[user_id]["state"] = "active_firebase"
        
    except Exception as e:
        await query.message.edit_text(f"Error saving to Firebase: {e}")

# --- 10. Creator Callbacks ---
@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_trig(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("🆕 **Enter New Module Name:**")

@Client.on_callback_query(filters.regex("^fb_create_submod_ask"))
async def create_submod_trig(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_submod_creation"
    await query.message.edit_text(f"🆕 **Enter Sub-Module Name:**")
