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
# {user_id: {"cat_id": "...", "batch_id": "...", "module_id": "...", "cat_name": "...", "batch_name": "...", "mod_name": "...", "state": "idle"}}
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
            
        # Extension Hatana aur Underscore Hatana
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
    # Reset Session
    user_session[user_id] = {"state": "idle"}
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected Successfully!\nSelect a Category to manage content:",
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
        cats = db.child("categories").get()
        buttons = []
        if cats.each():
            for cat in cats.each():
                c_name = get_name(cat.val())
                # Note: We can't pass name in callback data (size limit), so we fetch/store later or use IDs
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
        # Fetch Category Name for UI (Optional, skips if slow)
        # cat_info = db.child("categories").child(cat_id).get()
        # user_session[user_id]["cat_name"] = get_name(cat_info.val()) 
        
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
        
        buttons.append([InlineKeyboardButton("➕ Create New Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        
        await query.message.edit_text(f"**🎓 Batch ID:** `{batch_id}`\n\nSelect a **Module**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error: {e}")

# 4. Set Module (Final Step)
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["state"] = "active_firebase" # Mark as ready for upload
    
    # Store Names (Simplified for speed - Fetching names here if needed)
    # For now, we use IDs to confirm path
    
    await query.message.edit_text(
        f"✅ **Target Set Successfully!**\n\n"
        f"📂 **Category:** `{user_session[user_id]['cat_id']}`\n"
        f"🎓 **Batch:** `{user_session[user_id]['batch_id']}`\n"
        f"📺 **Module:** `{module_id}`\n\n"
        f"⬇️ **Now Send Video/File to add to this module.**\n"
        f"_(Send /stop_firebase to stop adding to this module)_",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel Selection", callback_data="fb_clear_session")]])
    )

# --- Clear Session ---
@Client.on_callback_query(filters.regex("^fb_clear_session"))
async def clear_session(bot, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in user_session:
        del user_session[user_id]
    await query.message.edit_text("✅ **Selection Cleared.**\nNow files will generate normal links only.")

# --- FILE HANDLER (Dual Logic) ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    # 1. Generate Link Common for both
    status_msg = await message.reply_text("🔄 **Processing...**")
    stream_link, clean_name, log_id = await get_stream_link(message)
    
    if not stream_link:
        return await status_msg.edit("❌ Error generating link.")

    # 2. Check Logic: Firebase or Normal?
    is_firebase_active = False
    if user_id in user_session and "module_id" in user_session[user_id] and user_session[user_id].get("state") == "active_firebase":
        is_firebase_active = True
    
    # --- SCENARIO A: Normal Mode (No Module Set) ---
    if not is_firebase_active:
        text = (
            f"✅ **Link Generated!**\n\n"
            f"📄 **Name:** `{clean_name}`\n"
            f"🔗 **Direct URL:**\n`{stream_link}`\n\n"
            f"⚠️ _File NOT added to website because no module is selected._"
        )
        buttons = [
            [InlineKeyboardButton("⬇️ Download", url=stream_link)],
            [InlineKeyboardButton("🔥 Select Module", callback_data="fb_cat_list")]
        ]
        await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        return

    # --- SCENARIO B: Firebase Mode (Module Set) ---
    # Save Temp Data for Confirmation
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    
    text = (
        f"🚀 **Ready to Add to Website**\n\n"
        f"📄 **Name:** `{clean_name}`\n"
        f"🔗 **Link:** Created\n"
        f"📂 **Location:** `{user_session[user_id]['module_id']}`\n\n"
        f"**Rename File?**"
    )
    
    buttons = [
        [InlineKeyboardButton("✅ Keep Name & Add", callback_data="fb_name_keep")],
        [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")],
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_clear_session")]
    ]
    
    await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

# --- FIREBASE LOGIC (Naming & Upload) ---

@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_default_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"], data["url"], user_session[user_id])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def ask_for_rename(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **Send New Name:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")]]))

@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text_inputs(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state")
    
    # 1. Rename
    if state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase" # Restore active state
        await message.reply_text(f"✅ Name Updated: **{new_name}**")
        await ask_file_type(message, new_name, user_session[user_id]["temp_data"]["url"], user_session[user_id])
        
    # 2. Create Module
    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat_id = user_session[user_id]["cat_id"]
        batch_id = user_session[user_id]["batch_id"]
        timestamp = int(time.time() * 1000)
        
        try:
            path_ref = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules")
            push_ref = path_ref.push({"name": mod_name, "order": timestamp})
            gen_key = push_ref['name']
            path_ref.child(gen_key).update({"id": gen_key})
            
            await message.reply_text(f"✅ **Module Created:** {mod_name}\nRefresh list to see it.")
            user_session[user_id]["state"] = "idle"
        except Exception as e:
            await message.reply_text(f"Error: {e}")

async def ask_file_type(message, title, url, session_data):
    # Fancy UI Confirmation
    cat = session_data.get('cat_id', 'Unknown')
    batch = session_data.get('batch_id', 'Unknown')
    mod = session_data.get('module_id', 'Unknown')
    
    text = (
        f"📥 **Confirm Addition**\n\n"
        f"📚 **Path Info:**\n"
        f"  ├ 📂 `{cat}`\n"
        f"  ├ 🎓 `{batch}`\n"
        f"  └ 📺 `{mod}`\n\n"
        f"🎬 **Content:**\n"
        f"  ├ 🏷 `{title}`\n"
        f"  └ 🔗 `Link Generated`\n\n"
        f"**Select Type:**"
    )
    
    buttons = [
        [
            InlineKeyboardButton("🎬 Add Lecture", callback_data="fb_confirm_lec"),
            InlineKeyboardButton("📄 Add Resource", callback_data="fb_confirm_res")
        ]
    ]
    
    if isinstance(message, Message):
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=enums.ParseMode.MARKDOWN)
    else:
        # Fallback if coming from callback loop
        pass

# --- FINAL PUSH ---

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_to_firebase(bot, query: CallbackQuery):
    action = query.data.split("_")[2]
    user_id = query.from_user.id
    
    if user_id not in user_session or "temp_data" not in user_session[user_id]:
        return await query.answer("Session expired.", show_alert=True)
    
    data = user_session[user_id]["temp_data"]
    # Retrieve IDs
    cat_id = user_session[user_id]["cat_id"]
    batch_id = user_session[user_id]["batch_id"]
    module_id = user_session[user_id]["module_id"]
    
    target_node = "lectures" if action == "lec" else "resources"
    timestamp_order = int(time.time() * 1000)
    
    entry_data = {
        "name": data["title"],
        "link": data["url"],
        "order": timestamp_order
    }
    
    try:
        path_ref = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(module_id).child(target_node)
        push_ref = path_ref.push(entry_data)
        gen_key = push_ref['name']
        path_ref.child(gen_key).update({"id": gen_key})
        
        await query.message.edit_text(
            f"✅ **Successfully Added!**\n\n"
            f"🏷 **Title:** {data['title']}\n"
            f"📂 **Added To:** {target_node.upper()}\n"
            f"🆔 **Key:** `{gen_key}`\n\n"
            f"Send next file to continue adding here.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="fb_cat_list")]])
        )
    except Exception as e:
        await query.message.edit_text(f"❌ Error: {e}")

# --- Create Module Handler ---
@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_callback(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("🆕 **Enter New Module Name:**")
