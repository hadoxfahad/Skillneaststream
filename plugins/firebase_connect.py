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
            
        name_without_ext = os.path.splitext(file_name)[0]
        clean_name = name_without_ext.replace("_", " ")
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name, log_msg.id
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None, None

def get_name(data):
    if not data: return "Unnamed"
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or data.get("description") or "Unnamed"
    return "Unnamed"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    # Reset Session
    user_session[user_id] = {"state": "idle", "fast_mode": False}
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!\nSelect a Category to start:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Switch Mode", callback_data="fb_mode_menu")]
        ])
    )

# --- Navigation Flow ---

# 1. Categories
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
        await query.message.edit_text(f"Error: {e}")

# 2. Batches
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
        await query.message.edit_text(f"**📂 Category:** `{cat_id}`\nSelect Batch:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# 3. Modules
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    cat_id = user_session[user_id].get("cat_id")
    user_session[user_id]["batch_id"] = batch_id
    
    # Reset sub-module info when entering module list
    if "sub_module_id" in user_session[user_id]:
        del user_session[user_id]["sub_module_id"]
    
    try:
        modules_data = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get().val()
        buttons = []
        if modules_data:
            if isinstance(modules_data, dict):
                for key, val in modules_data.items():
                    if isinstance(val, dict):
                        buttons.append([InlineKeyboardButton(f"📺 {get_name(val)}", callback_data=f"fb_set_mod_{key}")])
            elif isinstance(modules_data, list):
                for i, val in enumerate(modules_data):
                    if val and isinstance(val, dict):
                        buttons.append([InlineKeyboardButton(f"📺 {get_name(val)}", callback_data=f"fb_set_mod_{i}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        
        await query.message.edit_text(f"**🎓 Batch:** `{batch_id}`\nSelect Module:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error: {e}")

# 4. Module Dashboard (Set Active Module)
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["module_id"] = module_id
    # Clear sub-module if we are back at Main Module
    if "sub_module_id" in user_session[user_id]:
        del user_session[user_id]["sub_module_id"]

    user_session[user_id]["state"] = "active_firebase"
    
    # Fast Mode Status
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    buttons = [
        [InlineKeyboardButton("📂 Open Sub-Modules", callback_data=f"fb_sub_list_{module_id}")],
        [InlineKeyboardButton("✏️ Manage Content", callback_data=f"fb_manage_{module_id}")],
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_batch_{user_session[user_id]['batch_id']}")]
    ]

    await query.message.edit_text(
        f"✅ **Main Module Selected!**\n\n"
        f"📺 **Module:** `{module_id}`\n"
        f"⚡ **Fast Mode:** {fast_status}\n\n"
        f"⬇️ **Send Files Now** (uploads to Module root)\n"
        f"OR Click **Open Sub-Modules** to go deeper.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- 5. Sub-Module Logic (NEW) ---

@Client.on_callback_query(filters.regex("^fb_sub_list_"))
async def list_sub_modules(bot, query: CallbackQuery):
    mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]

    try:
        # Path: .../modules/{mod_id}/sub_modules
        sub_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod_id).child("sub_modules").get().val()
        
        buttons = []
        if sub_path:
            if isinstance(sub_path, dict):
                for key, val in sub_path.items():
                    if isinstance(val, dict):
                        buttons.append([InlineKeyboardButton(f"🔹 {get_name(val)}", callback_data=f"fb_set_sub_{key}")])
            elif isinstance(sub_path, list):
                for i, val in enumerate(sub_path):
                    if val: buttons.append([InlineKeyboardButton(f"🔹 {get_name(val)}", callback_data=f"fb_set_sub_{i}")])

        buttons.append([InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_create_sub")])
        buttons.append([InlineKeyboardButton("🔙 Back to Module", callback_data=f"fb_set_mod_{mod_id}")])

        await query.message.edit_text(f"**📂 Sub-Modules inside:** `{mod_id}`\nSelect one to upload inside it:", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        await query.message.edit_text(f"Error fetching sub-modules: {e}")

@Client.on_callback_query(filters.regex("^fb_set_sub_"))
async def set_active_sub_module(bot, query: CallbackQuery):
    sub_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["sub_module_id"] = sub_id
    user_session[user_id]["state"] = "active_firebase"
    mod_id = user_session[user_id]["module_id"]

    # Fast Mode Logic
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_text = "⚡ Disable Fast" if is_fast else "⚡ Enable Fast"

    buttons = [
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🔙 Back to Sub-List", callback_data=f"fb_sub_list_{mod_id}")]
    ]

    await query.message.edit_text(
        f"✅ **Sub-Module Selected!**\n\n"
        f"📺 **Parent Module:** `{mod_id}`\n"
        f"🔹 **Sub-Module:** `{sub_id}`\n"
        f"⚡ **Fast Mode:** {fast_status}\n\n"
        f"⬇️ **Send Files Now** (will add to this Sub-Module)",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^fb_create_sub"))
async def create_sub_prompt(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_sub_creation"
    await query.message.edit_text("🆕 **Enter Name for New Sub-Module:**\n\nSend text now...")

# --- Feature: Fast Mode Toggle ---
@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    current = user_session[user_id].get("fast_mode", False)
    
    if not current:
        buttons = [[InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"), InlineKeyboardButton("📄 Resources", callback_data="fb_set_fast_res")]]
        await query.message.edit_text("**⚡ Setup Fast Mode**\nDefault upload type?", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        user_session[user_id]["fast_mode"] = False
        await refresh_dashboard(bot, query)

@Client.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(bot, query: CallbackQuery):
    user_id = query.from_user.id
    type_ = query.data.split("_")[3]
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = type_
    await query.answer("⚡ Fast Mode ON!", show_alert=True)
    await refresh_dashboard(bot, query)

async def refresh_dashboard(bot, query):
    user_id = query.from_user.id
    # Refresh based on where the user is (Module or Sub-Module)
    if "sub_module_id" in user_session[user_id]:
        query.data = f"fb_set_sub_{user_session[user_id]['sub_module_id']}"
        await set_active_sub_module(bot, query)
    else:
        query.data = f"fb_set_mod_{user_session[user_id]['module_id']}"
        await set_active_module(bot, query)

# --- File Handler (Smart Path Selection) ---
@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    if user_session.get(user_id, {}).get("state") != "active_firebase":
        return 
        
    stream_link, clean_name, log_id = await get_stream_link(message)
    if not stream_link: return await message.reply("Link Error.")

    # Determine Path (Module vs Sub-Module)
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
    
    # Check if inside a Sub-Module
    if "sub_module_id" in user_session[user_id]:
        sub_id = user_session[user_id]["sub_module_id"]
        # Path becomes: modules/{mod}/sub_modules/{sub}/
        target_path_root = base_path.child("sub_modules").child(sub_id)
        location_name = "Sub-Module"
    else:
        target_path_root = base_path
        location_name = "Module"

    # Fast Mode Execution
    if user_session[user_id].get("fast_mode"):
        def_type = user_session[user_id]["default_type"]
        target_folder = "lectures" if def_type == "lec" else "resources"
        ts = int(time.time() * 1000)
        
        final_path = target_path_root.child(target_folder)
        ref = final_path.push({"name": clean_name, "link": stream_link, "order": ts})
        key = ref['name']
        final_path.child(key).update({"id": key})
        
        await message.reply_text(f"⚡ **Added to {location_name}:** `{clean_name}`")
        return

    # Normal Mode (Ask Rename)
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link, "path_root": target_path_root}
    buttons = [
        [InlineKeyboardButton("✅ Add (Keep Name)", callback_data="fb_name_keep")], 
        [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")],
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_cancel_up")]
    ]
    await message.reply_text(f"📂 **Add to {location_name}**\nFile: `{clean_name}`", reply_markup=InlineKeyboardMarkup(buttons))

# --- Text Handler (Creation Logic) ---
@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state", "")

    # 1. Create Sub-Module
    if state == "waiting_sub_creation":
        name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("sub_modules")
        ref = path.push({"name": name, "order": ts, "isSubModule": True})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"✅ Sub-Module Created: **{name}**")
        user_session[user_id]["state"] = "active_firebase"
        
        # Show list again
        fake_query = type('obj', (object,), {'data': f"fb_sub_list_{mod}", 'message': message, 'from_user': message.from_user})
        await list_sub_modules(bot, fake_query)

    # 2. Create Module
    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ref = path.push({"name": mod_name, "order": ts})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"✅ Module Created: {mod_name}")
        user_session[user_id]["state"] = "idle"

    # 3. Rename File
    elif state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, new_name)

# --- Common Callbacks ---
@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def rename_ask(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **Send New Name:**")

async def ask_file_type(message, title):
    buttons = [[InlineKeyboardButton("🎬 Lecture", callback_data="fb_confirm_lec"), InlineKeyboardButton("📄 Resource", callback_data="fb_confirm_res")]]
    await message.reply_text(f"📌 **Confirm:**\nName: `{title}`", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_to_db(bot, query: CallbackQuery):
    type_ = query.data.split("_")[2] # lec or res
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    
    target = "lectures" if type_ == "lec" else "resources"
    ts = int(time.time() * 1000)
    
    # Use the path determined in file handler
    path = data["path_root"].child(target)
    
    try:
        ref = path.push({"name": data["title"], "link": data["url"], "order": ts})
        key = ref['name']
        path.child(key).update({"id": key})
        
        # Determine where to go back
        back_cb = "fb_cancel_up" # Just clears message
        await query.message.edit_text(f"✅ **Uploaded Successfully!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Done", callback_data=back_cb)]]))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_cancel_up"))
async def cancel_upload(bot, query: CallbackQuery):
    await query.message.delete()
    # Refresh dashboard logic if needed
    
@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_trig(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("🆕 **Enter Name for New Module:**")

@Client.on_callback_query(filters.regex("^fb_manage_"))
async def placeholder_manage(bot, query: CallbackQuery):
    await query.answer("Feature in code but collapsed for length (Add edit logic here)", show_alert=True)
