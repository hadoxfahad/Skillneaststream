import asyncio
import os
from pyrogram import Client, filters
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

# Session Structure: Stores selected IDs to build the path
# {user_id: {"cat_id": "...", "batch_id": "...", "module_id": "...", "mode": "file"}}
user_session = {} 

# --- Helper Functions ---

async def get_stream_link(message: Message):
    """Generates Stream Link & Extracts Filename"""
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        stream_link = f"{STREAM_URL}/watch/{log_msg.id}"
        
        if message.video:
            file_name = message.video.file_name or "Unknown Video"
        elif message.document:
            file_name = message.document.file_name or "Unknown File"
        else:
            file_name = "Unknown_File"
            
        clean_name = os.path.splitext(file_name)[0]
        return stream_link, clean_name, log_msg.id
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None, None

def get_name(data):
    """Extracts Name/Title/Description from Data"""
    return data.get("name") or data.get("title") or data.get("description") or "Unnamed"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected Successfully!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Change Mode", callback_data="fb_mode_menu")]
        ])
    )

# --- Navigation (Nested Logic) ---

# 1. Categories List (Root Level)
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        cats = db.child("categories").get()
        buttons = []
        
        if cats.each():
            for cat in cats.each():
                c_data = cat.val()
                c_name = get_name(c_data)
                # Category ID store kar rahe hain
                buttons.append([InlineKeyboardButton(c_name, callback_data=f"fb_sel_cat_{cat.key()}")])
        
        await query.message.edit_text("**Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# 2. Batches List (Inside Selected Category)
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["cat_id"] = cat_id
    
    try:
        # LOGIC CHANGE: Path is categories/{cat_id}/batches
        batches = db.child("categories").child(cat_id).child("batches").get()
        buttons = []
        
        if batches.each():
            for batch in batches.each():
                b_data = batch.val()
                b_name = get_name(b_data)
                buttons.append([InlineKeyboardButton(b_name, callback_data=f"fb_sel_batch_{batch.key()}")])
        
        if not buttons:
            buttons.append([InlineKeyboardButton("No Batches Found", callback_data="ignore")])
            
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**Category Selected!**\n\nAb Batch select karein:", reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        await query.message.edit_text(f"Error fetching batches: {e}")

# 3. Modules List (Inside Selected Batch)
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    cat_id = user_session[user_id].get("cat_id")
    user_session[user_id]["batch_id"] = batch_id
    
    try:
        # LOGIC CHANGE: Path is categories/{cat_id}/batches/{batch_id}/modules
        modules = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get()
        buttons = []
        
        if modules.each():
            for mod in modules.each():
                m_data = mod.val()
                m_name = get_name(m_data)
                buttons.append([InlineKeyboardButton(m_name, callback_data=f"fb_set_mod_{mod.key()}")])
        
        if not buttons:
            buttons.append([InlineKeyboardButton("No Modules Found", callback_data="ignore")])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        await query.message.edit_text(f"**Batch Selected!**\n\nAb Module select karein:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error fetching modules: {e}")

# 4. Set Module (Final Selection)
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["mode"] = user_session[user_id].get("mode", "file")
    
    await query.message.edit_text(
        f"✅ **Module Selected!**\nID: `{module_id}`\n\nAb Video upload karein ya Link bhejein.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Reset", callback_data="fb_cat_list")]])
    )

# --- File Handler ---
@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session or "module_id" not in user_session[user_id]:
        return
    if user_session[user_id].get("mode") == "url":
        return await message.reply("⚠️ Aapka Mode 'Link' hai. File bhejne ke liye Mode change karein.")

    status_msg = await message.reply_text("🔄 **Generating Link...**")
    stream_link, clean_name, log_id = await get_stream_link(message)
    
    if not stream_link:
        return await status_msg.edit("Error generating link.")
    
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    
    buttons = [
        [InlineKeyboardButton("➕ Add Lecture", callback_data="fb_confirm_lec"),
         InlineKeyboardButton("➕ Add Resource", callback_data="fb_confirm_res")],
        [InlineKeyboardButton("▶️ Watch Online", url=stream_link)]
    ]
    
    await status_msg.edit_text(
        f"**Title:** `{clean_name}`\n\nIsse website par kaise add karna hai?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Confirm Add (Writing to Nested Path) ---
@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_to_firebase(bot, query: CallbackQuery):
    action = query.data.split("_")[2] # 'lec' or 'res'
    user_id = query.from_user.id
    
    if user_id not in user_session or "temp_data" not in user_session[user_id]:
        return await query.answer("Session expired.", show_alert=True)
    
    data = user_session[user_id]["temp_data"]
    
    # Getting full path IDs
    cat_id = user_session[user_id]["cat_id"]
    batch_id = user_session[user_id]["batch_id"]
    module_id = user_session[user_id]["module_id"]
    
    type_ = "video" if action == "lec" else "pdf"
    
    new_entry = {
        "title": data["title"],
        "url": data["url"],
        "type": type_,
        "createdAt": {".sv": "timestamp"}
    }
    
    try:
        # LOGIC CHANGE: Saving inside the specific module path
        # Path: categories/{cat_id}/batches/{batch_id}/modules/{module_id}/lectures
        db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(module_id).child("lectures").push(new_entry)
        
        await query.message.edit_text(
            f"✅ **Added Successfully!**\n\n**Category:** {cat_id}\n**Module:** {module_id}\n**Title:** {data['title']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Send Next Video", callback_data="ignore")]])
        )
    except Exception as e:
        await query.message.edit_text(f"❌ Error Saving: {e}")

# --- URL Mode ---
@Client.on_callback_query(filters.regex("^fb_mode_menu"))
async def mode_menu(bot, query: CallbackQuery):
    await query.message.edit_text("Select Mode:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 File Mode", callback_data="fb_setmode_file")],
        [InlineKeyboardButton("🔗 URL Mode", callback_data="fb_setmode_url")]
    ]))

@Client.on_callback_query(filters.regex("^fb_setmode_"))
async def set_mode_func(bot, query: CallbackQuery):
    mode = query.data.split("_")[2]
    user_id = query.from_user.id
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["mode"] = mode
    await query.message.edit_text(f"✅ Mode Updated: **{mode.upper()}**")

@Client.on_message(filters.text & filters.user(ADMINS))
async def direct_url_handler(bot, message):
    user_id = message.from_user.id
    if user_id in user_session and user_session[user_id].get("mode") == "url" and "module_id" in user_session[user_id]:
        text = message.text.strip()
        if "|" in text:
            parts = text.split("|", 1)
            title, url = parts[0].strip(), parts[1].strip()
        elif "http" in text:
            title, url = "External Link", text
        else:
            return

        cat_id = user_session[user_id]["cat_id"]
        batch_id = user_session[user_id]["batch_id"]
        module_id = user_session[user_id]["module_id"]

        db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(module_id).child("lectures").push({
            "title": title,
            "url": url,
            "type": "video",
            "createdAt": {".sv": "timestamp"}
        })
        await message.reply_text(f"✅ Added Link: {title}")
