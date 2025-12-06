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
        return data.get("name") or data.get("title") or data.get("description") or "Unnamed"
    return "Unnamed"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    user_session[user_id] = {"state": "idle", "fast_mode": False}
    
    await message.reply_text(
        "**ðŸ”¥ Firebase Admin Panel**\n\nDatabase Connected!\nSelect a Category to start:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("ðŸ“‚ Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("âš™ï¸ Switch Mode", callback_data="fb_mode_menu")]
        ])
    )

# --- Navigation ---

# 1. Categories
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        # Use .val() instead of .each() for reliability
        cats_data = db.child("categories").get().val()
        buttons = []
        
        if cats_data:
            # Handle Dictionary (Standard Firebase)
            if isinstance(cats_data, dict):
                for key, val in cats_data.items():
                    c_name = get_name(val)
                    buttons.append([InlineKeyboardButton(f"ðŸ“‚ {c_name}", callback_data=f"fb_sel_cat_{key}")])
            # Handle List (Rare case)
            elif isinstance(cats_data, list):
                for i, val in enumerate(cats_data):
                    if val:
                        c_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"ðŸ“‚ {c_name}", callback_data=f"fb_sel_cat_{i}")])
        
        await query.message.edit_text("**ðŸ“‚ Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error fetching categories: {e}")

# 2. Batches (FIXED FOR YOUR SCREENSHOT)
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["cat_id"] = cat_id
    
    try:
        # Directly fetch values (.val())
        batches_data = db.child("categories").child(cat_id).child("batches").get().val()
        
        buttons = []
        
        if batches_data:
            # Check if it's a Dictionary (Keys like -Oe1E...)
            if isinstance(batches_data, dict):
                for key, val in batches_data.items():
                    if isinstance(val, dict): # Ensure it's not a property like 'enabled'
                        b_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"ðŸŽ“ {b_name}", callback_data=f"fb_sel_batch_{key}")])
            
            # Check if it's a List (Keys 0, 1, 2...)
            elif isinstance(batches_data, list):
                for i, val in enumerate(batches_data):
                    if val and isinstance(val, dict):
                        b_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"ðŸŽ“ {b_name}", callback_data=f"fb_sel_batch_{i}")])
        
        if not buttons:
             buttons.append([InlineKeyboardButton("ðŸš« No Batches Found", callback_data="ignore")])

        buttons.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**ðŸ“‚ Category ID:** `{cat_id}`\n\nSelect a **Batch**:", reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        print(f"Batch Error: {e}")
        await query.message.edit_text(f"âŒ Error loading batches: {e}\nTry again.")

# 3. Modules
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    cat_id = user_session[user_id].get("cat_id")
    user_session[user_id]["batch_id"] = batch_id
    
    try:
        # Use .val() here too
        modules_data = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get().val()
        buttons = []
        
        if modules_data:
            if isinstance(modules_data, dict):
                for key, val in modules_data.items():
                    if isinstance(val, dict):
                        m_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"ðŸ“º {m_name}", callback_data=f"fb_set_mod_{key}")])
            elif isinstance(modules_data, list):
                for i, val in enumerate(modules_data):
                    if val and isinstance(val, dict):
                        m_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"ðŸ“º {m_name}", callback_data=f"fb_set_mod_{i}")])
        
        buttons.append([InlineKeyboardButton("âž• Create Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("ðŸ”™ Back", callback_data=f"fb_sel_cat_{cat_id}")])
        
        await query.message.edit_text(f"**ðŸŽ“ Batch ID:** `{batch_id}`\n\nSelect a **Module**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error: {e}")

# 4. Set Module (Dashboard)
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["state"] = "active_firebase"
    
    # Check Fast Mode
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "ðŸŸ¢ ON" if is_fast else "ðŸ”´ OFF"
    fast_text = "âš¡ Disable Fast Mode" if is_fast else "âš¡ Enable Fast Mode"
    
    buttons = [
        [InlineKeyboardButton("âœï¸ Manage Content (Edit/Del)", callback_data=f"fb_manage_{module_id}")],
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("âŒ Stop / Cancel", callback_data="fb_clear_session")]
    ]

    await query.message.edit_text(
        f"âœ… **Target Set!**\n\n"
        f"ðŸ“‚ **Category:** `{user_session[user_id]['cat_id']}`\n"
        f"ðŸŽ“ **Batch:** `{user_session[user_id]['batch_id']}`\n"
        f"ðŸ“º **Module:** `{module_id}`\n\n"
        f"âš¡ **Fast Mode:** {fast_status}\n\n"
        f"â¬‡ï¸ **Send Files Now:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Feature: Fast Mode ---
@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    current_status = user_session[user_id].get("fast_mode", False)
    
    if not current_status:
        buttons = [[InlineKeyboardButton("ðŸŽ¬ Lectures", callback_data="fb_set_fast_lec"), InlineKeyboardButton("ðŸ“„ Resources", callback_data="fb_set_fast_res")]]
        await query.message.edit_text("**âš¡ Fast Mode Setup**\n\nDefault Type kya rakhein?", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        user_session[user_id]["fast_mode"] = False
        mod_id = user_session[user_id]["module_id"]
        query.data = f"fb_set_mod_{mod_id}"
        await set_active_module(bot, query)

@Client.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(bot, query: CallbackQuery):
    user_id = query.from_user.id
    type_ = query.data.split("_")[3]
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = type_
    await query.answer("âš¡ Fast Mode Enabled!", show_alert=True)
    
    mod_id = user_session[user_id]["module_id"]
    query.data = f"fb_set_mod_{mod_id}"
    await set_active_module(bot, query)

# --- Feature: Manage Content ---
@Client.on_callback_query(filters.regex("^fb_manage_"))
async def manage_content_list(bot, query: CallbackQuery):
    module_id = query.data.split("_")[2]
    user_id = query.from_user.id
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    
    try:
        lectures_data = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(module_id).child("lectures").get().val()
        buttons = []
        
        if lectures_data:
            if isinstance(lectures_data, dict):
                for key, val in lectures_data.items():
                    name = get_name(val)
                    buttons.append([InlineKeyboardButton(f"ðŸ“ {name}", callback_data=f"fb_item_opt_{key}")])
            elif isinstance(lectures_data, list):
                for i, val in enumerate(lectures_data):
                    if val:
                        name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"ðŸ“ {name}", callback_data=f"fb_item_opt_{i}")])
        
        buttons.append([InlineKeyboardButton("ðŸ”™ Back to Upload", callback_data=f"fb_set_mod_{module_id}")])
        await query.message.edit_text(f"**ðŸ—‘ Manage Content**\n\nClick item to **Edit** or **Delete**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_item_opt_"))
async def item_options(bot, query: CallbackQuery):
    key = query.data.split("_")[3]
    user_id = query.from_user.id
    mod_id = user_session[user_id]["module_id"]
    
    buttons = [
        [InlineKeyboardButton("ðŸ—‘ Delete Permanently", callback_data=f"fb_del_{key}")],
        [InlineKeyboardButton("âœï¸ Rename (Edit)", callback_data=f"fb_edit_ask_{key}")],
        [InlineKeyboardButton("ðŸ”™ Back to List", callback_data=f"fb_manage_{mod_id}")]
    ]
    await query.message.edit_text(f"**âš™ï¸ Options for Item ID:** `{key}`", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_del_"))
async def delete_item(bot, query: CallbackQuery):
    key = query.data.split("_")[2]
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(key).remove()
    await query.answer("ðŸ—‘ Deleted!", show_alert=True)
    query.data = f"fb_manage_{mod}"
    await manage_content_list(bot, query)

@Client.on_callback_query(filters.regex("^fb_edit_ask_"))
async def edit_ask(bot, query: CallbackQuery):
    key = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["state"] = f"waiting_edit_{key}"
    await query.message.edit_text(f"âœï¸ **Send New Name** for this item:")

# --- File Handler ---
@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    stream_link, clean_name, log_id = await get_stream_link(message)
    if not stream_link: return await message.reply("Error.")

    is_active = user_session.get(user_id, {}).get("state") == "active_firebase"
    
    if not is_active:
        text = f"âœ… **Link Generated!**\nðŸ“„ `{clean_name}`\nðŸ”— `{stream_link}`"
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ”¥ Add to Firebase", callback_data="fb_cat_list")]]), disable_web_page_preview=True)
        return

    # Fast Mode
    if user_session[user_id].get("fast_mode"):
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        def_type = user_session[user_id]["default_type"]
        target = "lectures" if def_type == "lec" else "resources"
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
        ref = path.push({"name": clean_name, "link": stream_link, "order": ts})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"âš¡ **Added:** `{clean_name}`")
        return

    # Normal Mode
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    buttons = [[InlineKeyboardButton("âœ… Add (Keep Name)", callback_data="fb_name_keep")], [InlineKeyboardButton("âœï¸ Rename", callback_data="fb_name_rename")], [InlineKeyboardButton("âŒ Cancel", callback_data="fb_clear_session")]]
    await message.reply_text(f"ðŸ“‚ **Ready to Add:** `{clean_name}`\nRename or Keep?", reply_markup=InlineKeyboardMarkup(buttons))

# --- Text Handler ---
@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state", "")
    
    if state.startswith("waiting_edit_"):
        key = state.split("_")[2]
        new_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        
        db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(key).update({"name": new_name})
        await message.reply_text(f"âœ… Renamed!")
        user_session[user_id]["state"] = "active_firebase"
        await message.reply_text("Click Manage Content again to see changes.")

    elif state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, new_name, user_session[user_id]["temp_data"]["url"], user_session[user_id])

    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        ts = int(time.time() * 1000)
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ref = path.push({"name": mod_name, "order": ts})
        key = ref['name']
        path.child(key).update({"id": key})
        await message.reply_text(f"âœ… Created: {mod_name}")
        user_session[user_id]["state"] = "idle"

    elif user_session[user_id].get("mode") == "url" and "module_id" in user_session[user_id]:
        await direct_url_logic(bot, message)

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
    await query.message.edit_text("âœï¸ **New Name:**")

async def ask_file_type(message, title, url, session):
    buttons = [[InlineKeyboardButton("ðŸŽ¬ Lecture", callback_data="fb_confirm_lec"), InlineKeyboardButton("ðŸ“„ Resource", callback_data="fb_confirm_res")]]
    await message.reply_text(f"ðŸ“Œ **Confirm:**\nName: `{title}`", reply_markup=InlineKeyboardMarkup(buttons))

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
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(target)
        ref = path.push(entry)
        key = ref['name']
        path.child(key).update({"id": key})
        
        await query.message.edit_text(f"âœ… **Added!**\nKey: `{key}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Next", callback_data="fb_clear_session")]]))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_clear_session"))
async def clear_s(bot, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in user_session: del user_session[user_id]
    await query.message.edit_text("âœ… Stopped.")

@Client.on_callback_query(filters.regex("^fb_mode_menu"))
async def mode_menu(bot, query: CallbackQuery):
    await query.message.edit_text("Select Mode:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ“‚ File", callback_data="fb_setmode_file"), InlineKeyboardButton("ðŸ”— URL", callback_data="fb_setmode_url")]]))

@Client.on_callback_query(filters.regex("^fb_setmode_"))
async def set_mode(bot, query: CallbackQuery):
    mode = query.data.split("_")[2]
    user_id = query.from_user.id
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["mode"] = mode
    await query.answer(f"Mode: {mode}")

async def direct_url_logic(bot, message):
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
    await message.reply_text(f"âœ… URL Added: {title}")

@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_trig(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("ðŸ†• **Enter Name:**")
