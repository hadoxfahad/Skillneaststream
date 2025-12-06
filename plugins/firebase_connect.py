import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import pyrebase
from info import *  # Make sure ADMINS, LOG_CHANNEL, STREAM_URL are here

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
        return data.get("name") or data.get("title") or "Unnamed"
    return "Unnamed"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    # Reset Session
    user_session[user_id] = {
        "state": "idle", 
        "fast_mode": False, 
        "is_sub_module": False,
        "sub_mod_id": None
    }
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!\nSelect a Category to start:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Switch Mode (File/URL)", callback_data="fb_mode_menu")]
        ])
    )

# --- Navigation ---

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
        await query.message.edit_text(f"Error fetching categories: {e}")

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
        await query.message.edit_text(f"**📂 Category ID:** `{cat_id}`\n\nSelect a **Batch**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# 3. Modules List
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
                        # CHANGED: Now goes to Module Menu instead of dashboard
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

# --- 4. Module Menu & Sub-Module Logic (IMPORTANT FIX) ---

@Client.on_callback_query(filters.regex("^fb_mod_menu_"))
async def module_menu_handler(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["is_sub_module"] = False 
    user_session[user_id]["sub_mod_id"] = None
    
    buttons = [
        [InlineKeyboardButton("✅ Select This Module", callback_data=f"fb_set_final_main")],
        [InlineKeyboardButton("📂 Show Sub-Modules", callback_data=f"fb_list_submod_{module_id}")],
        [InlineKeyboardButton("➕ Create Sub-Module", callback_data=f"fb_create_submod_ask")],
        [InlineKeyboardButton("🔙 Back to Modules", callback_data=f"fb_sel_batch_{user_session[user_id]['batch_id']}")]
    ]
    
    await query.message.edit_text(f"**📺 Module Selected:** `{module_id}`\n\nIs module ke andar kya karna hai?", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_list_submod_"))
async def list_sub_modules(bot, query: CallbackQuery):
    mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    
    try:
        # Path: modules -> {id} -> subModules
        sub_mods = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod_id).child("subModules").get().val()
        buttons = []
        
        if sub_mods and isinstance(sub_mods, dict):
            for key, val in sub_mods.items():
                buttons.append([InlineKeyboardButton(f"📑 {get_name(val)}", callback_data=f"fb_set_submod_{key}")])
        
        if not buttons:
            buttons.append([InlineKeyboardButton("🚫 No Sub-Modules Found", callback_data="ignore")])
            
        buttons.append([InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_create_submod_ask")])
        buttons.append([InlineKeyboardButton("🔙 Back to Menu", callback_data=f"fb_mod_menu_{mod_id}")])
        
        await query.message.edit_text("**📂 Sub-Modules List**\nSelect one to upload inside it:", reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        await query.message.edit_text(f"Error loading Sub-modules: {e}")

# --- 5. Set Active Target (Main or Sub) ---

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
    
    # Info for Display
    mod_id = user_session[user_id]["module_id"]
    sub_id = user_session[user_id].get("sub_mod_id", "None")
    
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    # Submodule title text fix
    target_display = "SUB-MODULE" if user_session[user_id]["is_sub_module"] else "MAIN MODULE"
    
    text = (
        f"✅ **Target Locked: {target_display}**\n"
        f"📂 **Path:** `.../modules/{mod_id}/`"
    )
    if user_session[user_id]["is_sub_module"]:
        text += f"`subModules/{sub_id}`"
        
    text += f"\n\n⚡ **Fast Mode:** {fast_status}\n⬇️ **Send Files Now:**"
    
    buttons = [
        [InlineKeyboardButton("✏️ Manage/Delete Content", callback_data=f"fb_manage_idx")],
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🔙 Change Selection", callback_data=f"fb_mod_menu_{mod_id}")]
    ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# --- Feature: Fast Mode ---
@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    current = user_session[user_id].get("fast_mode", False)
    
    if not current:
        buttons = [[InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"), InlineKeyboardButton("📄 Resources", callback_data="fb_set_fast_res")]]
        await query.message.edit_text("**⚡ Fast Mode Setup**\n\nUploads automatically kaha add karein?", reply_markup=InlineKeyboardMarkup(buttons))
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

# --- Feature: Manage Content (List/Del) ---
@Client.on_callback_query(filters.regex("^fb_manage_idx"))
async def manage_content_list(bot, query: CallbackQuery):
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    # Logic to select Main or Sub Module Path
    if user_session[user_id]["is_sub_module"]:
        sub_mod = user_session[user_id]["sub_mod_id"]
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod)
    else:
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
    
    try:
        # Showing lectures by default
        lectures_data = base_path.child("lectures").get().val()
        buttons = []
        
        if lectures_data:
            if isinstance(lectures_data, dict):
                for key, val in lectures_data.items():
                    buttons.append([InlineKeyboardButton(f"🗑 {get_name(val)}", callback_data=f"fb_del_item_{key}")])
        
        type_name = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
        buttons.append([InlineKeyboardButton("🔙 Back to Upload", callback_data="fb_back_dash")])
        
        await query.message.edit_text(f"**🗑 Delete Content from {type_name}**\nClick to delete permanently:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_back_dash"))
async def back_to_dash(bot, query: CallbackQuery):
    type_name = "Sub-Module" if user_session[query.from_user.id]["is_sub_module"] else "Main Module"
    await show_dashboard(bot, query, type_name)

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
    await query.answer("🗑 Deleted!", show_alert=True)
    await manage_content_list(bot, query) # Refresh

# --- File Handler (The Core) ---
@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    # Check if active
    if user_session.get(user_id, {}).get("state") != "active_firebase":
        stream_link, clean_name, _ = await get_stream_link(message)
        if stream_link:
            await message.reply_text(f"✅ **Link:**\n`{stream_link}`\n\nSelect a Module to add this.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔥 Open Panel", callback_data="fb_cat_list")]]))
        return

    # Generate Link
    stream_link, clean_name, log_id = await get_stream_link(message)
    if not stream_link: return await message.reply("Error generating link.")

    # Determine Path Logic (Main vs Sub)
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    if user_session[user_id]["is_sub_module"]:
        sub_mod = user_session[user_id]["sub_mod_id"]
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod)
    else:
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)

    # FAST MODE UPLOAD
    if user_session[user_id].get("fast_mode"):
        def_type = user_session[user_id]["default_type"]
        target = "lectures" if def_type == "lec" else "resources"
        ts = int(time.time() * 1000)
        
        path = base_path.child(target)
        ref = path.push({"name": clean_name, "link": stream_link, "order": ts})
        key = ref['name']
        path.child(key).update({"id": key})
        
        loc_txt = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
        await message.reply_text(f"⚡ **Added to {loc_txt} ({target}):**\n`{clean_name}`")
        return

    # NORMAL MODE (Ask Name/Type)
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    buttons = [
        [InlineKeyboardButton("✅ Add (Keep Name)", callback_data="fb_name_keep")], 
        [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")], 
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_back_dash")]
    ]
    await message.reply_text(f"📂 **File Ready:** `{clean_name}`\nRename or Add?", reply_markup=InlineKeyboardMarkup(buttons))

# --- Text Handler (Rename & Create) ---
@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state", "")
    
    # 1. Rename File
    if state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, new_name, user_session[user_id]["temp_data"]["url"], user_session[user_id])

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

    # 3. Create Sub-Module (CORRECTED)
    elif state == "waiting_submod_creation":
        sub_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        ts = int(time.time() * 1000)
        
        # Creating SubModule inside the specific module
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules")
        ref = path.push({"name": sub_name, "order": ts, "isSubModule": True})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"✅ **Sub-Module Created:** {sub_name}\n\nGo back to list to see it.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data=f"fb_mod_menu_{mod}")]]))
        user_session[user_id]["state"] = "idle"

# --- Common Callbacks ---
@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_default_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"], data["url"], user_session[user_id])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def ask_for_rename_manual(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **New Name likho:**")

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
    
    try:
        # Determine Path (Fix for Submodule)
        if user_session[user_id]["is_sub_module"]:
            sub_mod = user_session[user_id]["sub_mod_id"]
            path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod).child(target)
        else:
            path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
            
        ref = path.push(entry)
        key = ref['name']
        path.child(key).update({"id": key})
        
        await query.message.edit_text(f"✅ **Added Successfully!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Upload More", callback_data="fb_back_dash")]]))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# --- Creators ---
@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_trig(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("🆕 **Enter Module Name:**")

@Client.on_callback_query(filters.regex("^fb_create_submod_ask"))
async def create_submod_trig(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_submod_creation"
    await query.message.edit_text(f"🆕 **Enter Sub-Module Name:**\n(Ye `{user_session[user_id]['module_id']}` ke andar banega)")
