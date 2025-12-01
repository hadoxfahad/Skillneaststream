import asyncio
import os
import urllib.parse
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

# --- Session Structure ---
user_session = {} 

# --- Helper Functions ---

async def get_stream_link(message: Message):
    """
    Generates Direct Stream Link (Raw File Link)
    Format: STREAM_URL/ID/Filename
    """
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        
        # File Name & Clean Name logic
        if message.video:
            file_name = message.video.file_name or f"Video_{log_msg.id}.mp4"
        elif message.document:
            file_name = message.document.file_name or f"File_{log_msg.id}.pdf"
        else:
            file_name = f"File_{log_msg.id}"
            
        clean_name = os.path.splitext(file_name)[0]
        
        # URL Encoding for safe link
        safe_filename = urllib.parse.quote_plus(file_name)
        
        # --- DIRECT STREAM LINK GENERATION ---
        # Ye link direct player me chalega (No Watch Page)
        stream_link = f"{STREAM_URL}/{log_msg.id}/{safe_filename}"
        
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
    user_session[user_id] = {"state": "idle"}
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nReady to add Content!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Change Mode (File/URL)", callback_data="fb_mode_menu")]
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
                buttons.append([InlineKeyboardButton(c_name, callback_data=f"fb_sel_cat_{cat.key()}")])
        
        await query.message.edit_text("**Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# 2. Batches
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["cat_id"] = cat_id
    user_session[user_id]["state"] = "idle"
    
    try:
        batches = db.child("categories").child(cat_id).child("batches").get()
        buttons = []
        if batches.each():
            for batch in batches.each():
                b_name = get_name(batch.val())
                buttons.append([InlineKeyboardButton(b_name, callback_data=f"fb_sel_batch_{batch.key()}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**Category Selected!**\n\nAb Batch select karein:", reply_markup=InlineKeyboardMarkup(buttons))
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
                buttons.append([InlineKeyboardButton(m_name, callback_data=f"fb_set_mod_{mod.key()}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        await query.message.edit_text(f"**Batch Selected!**\n\nAb Module select karein:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error: {e}")

# 4. Set Module
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["state"] = "idle"
    user_session[user_id]["mode"] = user_session[user_id].get("mode", "file")
    
    await query.message.edit_text(
        f"✅ **Module Configured!**\nID: `{module_id}`\n\nAb Video upload karein. Direct Stream Link banega.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Reset", callback_data="fb_cat_list")]])
    )

# --- STEP 1: Process File & Generate Direct Link ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session or "module_id" not in user_session[user_id]:
        return
    if user_session[user_id].get("mode") == "url":
        return await message.reply("⚠️ URL Mode Active. File allow nahi hai.")

    status_msg = await message.reply_text("🔄 **Generating Direct Stream Link...**")
    stream_link, clean_name, log_id = await get_stream_link(message)
    
    if not stream_link:
        return await status_msg.edit("Error generating link.")
    
    # Save Temp Data
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    
    # Buttons
    buttons = [
        [InlineKeyboardButton("✅ Use Default Name", callback_data="fb_name_keep")],
        [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")]
    ]
    
    # --- HERE: SHOWING LINK IN MESSAGE ---
    await status_msg.edit_text(
        f"**✅ Link Generated!**\n\n"
        f"**📂 Name:** `{clean_name}`\n"
        f"**🔗 Direct URL:**\n`{stream_link}`\n\n"
        f"Select Name Option:",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

# --- STEP 2: Naming Logic ---

@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_default_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    # Proceed to Type Selection
    await ask_file_type(query.message, user_session[user_id]["temp_data"]["title"], user_session[user_id]["temp_data"]["url"])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def ask_for_rename(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_for_name"
    await query.message.edit_text(
        "✏️ **Send New Name:**\n\nType karke bhejein.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="fb_cat_list")]])
    )

@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_rename_text(bot, message):
    user_id = message.from_user.id
    
    # Rename Handling
    if user_id in user_session and user_session[user_id].get("state") == "waiting_for_name":
        if message.text.startswith("/"): return 
        
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "idle" 
        
        await message.reply_text(f"✅ Renamed to: **{new_name}**")
        # Call final step
        await ask_file_type(message, new_name, user_session[user_id]["temp_data"]["url"])

    # URL Mode Handling
    elif user_id in user_session and user_session[user_id].get("mode") == "url" and "module_id" in user_session[user_id]:
        await direct_url_logic(bot, message)

# --- STEP 3: Ask Type (Lecture/Resource) ---

async def ask_file_type(message, title, url):
    buttons = [
        [
            InlineKeyboardButton("🎬 Add Lecture", callback_data="fb_confirm_lec"),
            InlineKeyboardButton("📄 Add Resource", callback_data="fb_confirm_res")
        ]
    ]
    
    text = f"**📌 Final Confirmation**\n\n**Name:** `{title}`\n**Link:** `{url}`\n\nAdd to Website?"
    
    if isinstance(message, Message):
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        # If passed from callback, edit won't work easily if message structure changed, so send new
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

# --- STEP 4: Push to Firebase ---

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_to_firebase(bot, query: CallbackQuery):
    action = query.data.split("_")[2] # 'lec' or 'res'
    user_id = query.from_user.id
    
    if user_id not in user_session or "temp_data" not in user_session[user_id]:
        return await query.answer("Session expired.", show_alert=True)
    
    data = user_session[user_id]["temp_data"]
    cat_id = user_session[user_id]["cat_id"]
    batch_id = user_session[user_id]["batch_id"]
    module_id = user_session[user_id]["module_id"]
    
    target_node = "lectures" if action == "lec" else "resources"
    type_tag = "video" if action == "lec" else "pdf"
    
    new_entry = {
        "title": data["title"],
        "url": data["url"], # Direct Stream Link
        "type": type_tag,
        "createdAt": {".sv": "timestamp"}
    }
    
    try:
        # Saving to specific path
        db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(module_id).child(target_node).push(new_entry)
        
        await query.message.edit_text(
            f"✅ **Saved to Website!**\n\n**Name:** {data['title']}\n**Link:** `{data['url']}`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Close", callback_data="fb_cat_list")]])
        )
    except Exception as e:
        await query.message.edit_text(f"❌ Error: {e}")

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

async def direct_url_logic(bot, message):
    user_id = message.from_user.id
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
    await message.reply_text(f"✅ **Link Added!**\nLink: `{url}`", disable_web_page_preview=True)
