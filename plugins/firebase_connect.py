import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import pyrebase
from info import *  # Ensure ADMINS, LOG_CHANNEL, STREAM_URL are defined here

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

# --- Session Management ---
user_session = {}

# --- Helper Functions ---

async def get_stream_link(message: Message):
    """Generates Direct Link & Cleans Filename via Log Channel"""
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        
        file_type = "file"
        if message.video:
            file_name = message.video.file_name or f"Video {log_msg.id}.mp4"
            file_type = "video"
        elif message.document:
            file_name = message.document.file_name or f"File {log_msg.id}.pdf"
            file_type = "pdf" # Defaulting to pdf for resources as per image, or use generic
        else:
            file_name = f"File {log_msg.id}"
            
        name_without_ext = os.path.splitext(file_name)[0]
        clean_name = name_without_ext.replace("_", " ")
        
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name, log_msg.id, file_type
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None, None, None

def get_name(data):
    if not data: return "Unnamed"
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or "Unnamed"
    return "Unnamed"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    # Initialize Session
    user_session[user_id] = {
        "state": "idle",
        "fast_mode": False,
        "is_sub_module": False,
        "sub_mod_id": None,
        "cat_id": None,
        "batch_id": None,
        "module_id": None
    }
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!\nSelect a Category:",
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
            iterator = cats_data.items() if isinstance(cats_data, dict) else enumerate(cats_data)
            for key, val in iterator:
                if val: buttons.append([InlineKeyboardButton(f"📂 {get_name(val)}", callback_data=f"fb_sel_cat_{key}")])
        
        await query.message.edit_text("**📂 Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error fetching categories: {e}")

# 2. List Batches
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_session[query.from_user.id]["cat_id"] = cat_id
    
    try:
        batches_data = db.child("categories").child(cat_id).child("batches").get().val()
        buttons = []
        if batches_data:
            iterator = batches_data.items() if isinstance(batches_data, dict) else enumerate(batches_data)
            for key, val in iterator:
                if val: buttons.append([InlineKeyboardButton(f"🎓 {get_name(val)}", callback_data=f"fb_sel_batch_{key}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**📂 Cat ID:** `{cat_id}`\nSelect Batch:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# 3. List Modules
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["batch_id"] = batch_id
    cat_id = user_session[user_id]["cat_id"]
    
    try:
        modules_data = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get().val()
        buttons = []
        if modules_data:
            iterator = modules_data.items() if isinstance(modules_data, dict) else enumerate(modules_data)
            for key, val in iterator:
                if val: buttons.append([InlineKeyboardButton(f"📺 {get_name(val)}", callback_data=f"fb_mod_menu_{key}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        
        await query.message.edit_text(f"**🎓 Batch ID:** `{batch_id}`\nSelect Module:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# --- 4. Module Menu (Logic for Submodules) ---

@Client.on_callback_query(filters.regex("^fb_mod_menu_"))
async def module_menu_handler(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["module_id"] = module_id
    
    # Reset submodule selection when entering main module menu
    user_session[user_id]["is_sub_module"] = False
    user_session[user_id]["sub_mod_id"] = None

    buttons = [
        # Option A: Upload directly to this module
        [InlineKeyboardButton("✅ Upload to Main Module", callback_data=f"fb_set_final_main")],
        # Option B: Go inside submodules
        [InlineKeyboardButton("📂 Open Sub-Modules", callback_data=f"fb_list_submod_{module_id}")],
        
        [InlineKeyboardButton("➕ Create Sub-Module", callback_data=f"fb_create_submod_ask")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_batch_{user_session[user_id]['batch_id']}")]
    ]
    
    await query.message.edit_text(f"**📺 Module Selected:** `{module_id}`\n\nWhere do you want to upload content?", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_list_submod_"))
async def list_sub_modules(bot, query: CallbackQuery):
    mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]

    try:
        # Fetching SubModules
        sub_mods = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod_id).child("subModules").get().val()
        buttons = []
        
        if sub_mods and isinstance(sub_mods, dict):
            for key, val in sub_mods.items():
                buttons.append([InlineKeyboardButton(f"📑 {get_name(val)}", callback_data=f"fb_set_submod_{key}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_create_submod_ask")])
        buttons.append([InlineKeyboardButton("🔙 Back to Menu", callback_data=f"fb_mod_menu_{mod_id}")])
        
        await query.message.edit_text("**📂 Sub-Modules List**\nSelect a sub-module to upload inside:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error loading Sub-modules: {e}")

# --- 5. Set Active Target & Dashboard ---

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
    
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"

    text = f"✅ **Target Locked: {type_name}**\n\n📺 **Main Module:** `{mod_id}`\n"
    if user_session[user_id]["is_sub_module"]:
        text += f"📑 **Sub-Module:** `{sub_id}`\n"
    
    text += f"\n⚡ **Fast Mode:** {fast_status}\n⬇️ **Send Video/File now to upload!**"
    
    buttons = [
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🗑 Manage Content", callback_data="fb_manage_idx")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"fb_mod_menu_{mod_id}")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# --- Fast Mode & Management ---

@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    current = user_session[user_id].get("fast_mode", False)
    
    if not current:
        buttons = [[InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"), InlineKeyboardButton("📄 Resources", callback_data="fb_set_fast_res")]]
        await query.message.edit_text("**⚡ Fast Mode Setup**\nAll uploads will go to:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        user_session[user_id]["fast_mode"] = False
        type_name = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
        await show_dashboard(bot, query, type_name)

@Client.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(bot, query: CallbackQuery):
    user_id = query.from_user.id
    type_ = query.data.split("_")[3] # lec or res
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = type_
    
    await query.answer("⚡ Fast Mode Enabled!", show_alert=True)
    type_name = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
    await show_dashboard(bot, query, type_name)

# --- Upload Logic (The Core) ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    # 1. Check if user is in active state
    if user_session.get(user_id, {}).get("state") != "active_firebase":
        return

    # 2. Generate Link
    status_msg = await message.reply("🔄 Processing...")
    stream_link, clean_name, log_id, file_type = await get_stream_link(message)
    
    if not stream_link:
        return await status_msg.edit("❌ Error generating stream link.")

    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    # 3. Determine Base Path (Main or Sub)
    if user_session[user_id]["is_sub_module"]:
        sub_mod = user_session[user_id]["sub_mod_id"]
        # Path: categories/cat/batches/batch/modules/mod/subModules/subMod
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod)
        loc_txt = "Sub-Module"
    else:
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
        loc_txt = "Main Module"

    # 4. Helper to push data
    def push_to_firebase(target_folder, name, link):
        ts = int(time.time() * 1000)
        # Create unique ID reference (like -OfjbVG...)
        target_path = base_path.child(target_folder)
        
        data = {
            "name": name,
            "link": link,
            "order": ts
        }
        
        # If it's a resource/pdf, add type
        if target_folder == "resources":
            data["type"] = "pdf" if file_type == "pdf" else "file"

        # Push creates the random key
        ref = target_path.push(data)
        key = ref['name'] # This gets the key generated by push
        
        # Update the entry to include its own ID (as per your structure)
        target_path.child(key).update({"id": key})
        return key

    # 5. Handle Fast Mode
    if user_session[user_id].get("fast_mode"):
        def_type = user_session[user_id]["default_type"] # 'lec' or 'res'
        target_folder = "lectures" if def_type == "lec" else "resources"
        
        push_to_firebase(target_folder, clean_name, stream_link)
        await status_msg.edit(f"⚡ **Fast Uploaded to {loc_txt} ({target_folder})**\n📂 `{clean_name}`")
        return

    # 6. Normal Mode (Ask details)
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link, "ftype": file_type}
    buttons = [
        [InlineKeyboardButton("✅ Keep Name & Add", callback_data="fb_name_keep")], 
        [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")], 
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_cancel_up")]
    ]
    await status_msg.edit(f"📂 **File Ready:** `{clean_name}`\nLink: `{stream_link}`\n\nAdd to **{loc_txt}**?", reply_markup=InlineKeyboardMarkup(buttons))

# --- Text Handlers (Rename & Create) ---

@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state", "")
    
    # Rename File
    if state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, new_name)

    # Create Module
    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ref = path.push({"name": mod_name, "order": ts})
        path.child(ref['name']).update({"id": ref['name']})
        
        await message.reply_text(f"✅ Module Created: **{mod_name}**")
        user_session[user_id]["state"] = "idle"

    # Create Sub-Module
    elif state == "waiting_submod_creation":
        sub_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules")
        
        # Important: Adding isSubModule: true as per requirements
        data = {
            "name": sub_name,
            "order": ts,
            "isSubModule": True
        }
        ref = path.push(data)
        path.child(ref['name']).update({"id": ref['name']})
        
        await message.reply_text(f"✅ Sub-Module Created: **{sub_name}**\nRefresh the list to see it.")
        user_session[user_id]["state"] = "idle"

# --- Callbacks for Upload Confirmation ---

@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def rename_ask(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **Send new name:**")

@Client.on_callback_query(filters.regex("^fb_cancel_up"))
async def cancel_upload(bot, query: CallbackQuery):
    await query.message.delete()
    await query.answer("❌ Cancelled")

async def ask_file_type(message, title):
    buttons = [[InlineKeyboardButton("🎬 Lecture", callback_data="fb_confirm_lec"), InlineKeyboardButton("📄 Resource", callback_data="fb_confirm_res")]]
    if isinstance(message, Message):
        await message.reply_text(f"📌 **Final Confirm:**\nName: `{title}`\nSelect Type:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.edit_text(f"📌 **Final Confirm:**\nName: `{title}`\nSelect Type:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_firebase_manual(bot, query: CallbackQuery):
    action = query.data.split("_")[2] # lec or res
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    target_folder = "lectures" if action == "lec" else "resources"
    
    # Path Logic
    if user_session[user_id]["is_sub_module"]:
        sub_mod = user_session[user_id]["sub_mod_id"]
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod).child(target_folder)
    else:
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target_folder)
        
    ts = int(time.time() * 1000)
    entry = {"name": data["title"], "link": data["url"], "order": ts}
    
    if target_folder == "resources":
        entry["type"] = "pdf" if data.get("ftype") == "pdf" else "file"
        
    try:
        ref = path.push(entry)
        path.child(ref['name']).update({"id": ref['name']})
        await query.message.edit_text("✅ **Successfully Added!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Upload More", callback_data=f"fb_mod_menu_{mod}")]]))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# --- Creation Triggers ---

@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_trig(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("🆕 **Enter New Module Name:**")

@Client.on_callback_query(filters.regex("^fb_create_submod_ask"))
async def create_submod_trig(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_submod_creation"
    await query.message.edit_text("🆕 **Enter Sub-Module Name:**")

# --- Content Management (Delete) ---

@Client.on_callback_query(filters.regex("^fb_manage_idx"))
async def manage_content_list(bot, query: CallbackQuery):
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    if user_session[user_id]["is_sub_module"]:
        sub_mod = user_session[user_id]["sub_mod_id"]
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod)
    else:
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
        
    try:
        lectures = base_path.child("lectures").get().val()
        buttons = []
        if lectures:
            for key, val in lectures.items():
                buttons.append([InlineKeyboardButton(f"🗑 {get_name(val)}", callback_data=f"fb_del_item_{key}")])
        
        type_name = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_back_dash")])
        await query.message.edit_text(f"**🗑 Delete from {type_name}:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_del_item_"))
async def delete_item(bot, query: CallbackQuery):
    key = query.data.split("_")[3]
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    if user_session[user_id]["is_sub_module"]:
        sub_mod = user_session[user_id]["sub_mod_id"]
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod).child("lectures")
    else:
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures")
    
    path.child(key).remove()
    await query.answer("Deleted", show_alert=True)
    await manage_content_list(bot, query)

@Client.on_callback_query(filters.regex("^fb_back_dash"))
async def back_to_dash(bot, query: CallbackQuery):
    type_name = "Sub-Module" if user_session[query.from_user.id]["is_sub_module"] else "Main Module"
    await show_dashboard(bot, query, type_name)
