import sys
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

print("----- LOADING FIREBASE PANEL PLUGIN -----") # Log check

# -----------------------------------------------------------------
# 1. CONFIGURATION (Hardcoded to avoid Import Errors)
# -----------------------------------------------------------------
# Yahan apni website ka link daalein (Bina '/' last me)
MY_WEBSITE_URL = "https://adminneast.firebaseapp.com" 

# Firebase Config
FIREBASE_CONFIG = {
  "apiKey": "AIzaSyChwpbFb6M4HtG6zwjg0AXh7Lz9KjnrGZk",
  "authDomain": "adminneast.firebaseapp.com",
  "databaseURL": "https://adminneast-default-rtdb.firebaseio.com",
  "projectId": "adminneast",
  "storageBucket": "adminneast.firebasestorage.app",
  "messagingSenderId": "883877553418",
  "appId": "1:883877553418:web:84ce8200f4b471bfffc6f3",
  "measurementId": "G-PCH99BDF1S"
}

# -----------------------------------------------------------------
# 2. INITIALIZE FIREBASE
# -----------------------------------------------------------------
db = None
try:
    import pyrebase
    firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
    db = firebase.database()
    print("✅ Firebase Connected Successfully")
except ImportError:
    print("❌ ERROR: pyrebase4 install nahi hai. requirements.txt check karein.")
except Exception as e:
    print(f"❌ Firebase Connection Error: {e}")

# User Sessions
user_sessions = {}

# -----------------------------------------------------------------
# 3. HELPERS
# -----------------------------------------------------------------
# Log Channel ID lene ki koshish
try:
    from info import LOG_CHANNEL
except ImportError:
    print("⚠️ Warning: LOG_CHANNEL not found in info.py")
    LOG_CHANNEL = None # Code crash hone se bachayega

# -----------------------------------------------------------------
# 4. COMMANDS
# -----------------------------------------------------------------

@Client.on_message(filters.command("testfb"))
async def test_firebase(bot, message):
    """Test command to check if bot is listening"""
    if db:
        await message.reply("✅ Bot is working and Firebase is connected!")
    else:
        await message.reply("⚠️ Bot is working but Firebase NOT connected. Check logs.")

@Client.on_message(filters.command("panel") & filters.private)
async def open_panel(bot, message):
    if db is None:
        await message.reply("❌ Error: Firebase library not installed or config wrong.")
        return

    status_msg = await message.reply("🔄 Fetching data from Database...")
    
    try:
        # Fetch Categories
        categories = db.child("categories").get()
        
        if not categories.val():
            await status_msg.edit("❌ Database connect hua par koi 'categories' nahi mili.\nKya database khali hai?")
            return

        buttons = []
        for cat in categories.each():
            key = cat.key()
            val = cat.val()
            cat_name = val.get("name", key) 
            buttons.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"cat_{key}")])

        await status_msg.edit(
            "**Select a Category:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await status_msg.edit(f"❌ Error occurred: {e}")

@Client.on_callback_query(filters.regex(r"^(cat_|course_|mod_)"))
async def handle_callbacks(bot, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    try:
        if data.startswith("cat_"):
            cat_id = data.split("_")[1]
            courses = db.child("courses").order_by_child("category_id").equal_to(cat_id).get()
            
            if not courses.val():
                await query.answer("No courses found here.", show_alert=True)
                return

            buttons = []
            for course in courses.each():
                key = course.key()
                val = course.val()
                c_name = val.get("name", key)
                buttons.append([InlineKeyboardButton(f"🎓 {c_name}", callback_data=f"course_{key}")])
            
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
            await query.message.edit_text(f"Selected Category ID: `{cat_id}`\nChoose Course:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("course_"):
            course_id = data.split("_")[1]
            modules = db.child("modules").order_by_child("course_id").equal_to(course_id).get()

            if not modules.val():
                await query.answer("No modules found.", show_alert=True)
                return

            buttons = []
            for mod in modules.each():
                key = mod.key()
                val = mod.val()
                m_name = val.get("name", key)
                buttons.append([InlineKeyboardButton(f"📑 {m_name}", callback_data=f"mod_{key}_{m_name}")])
            
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
            await query.message.edit_text(f"Selected Course ID: `{course_id}`\nChoose Module:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("mod_"):
            parts = data.split("_")
            mod_id = parts[1]
            mod_name = "_".join(parts[2:]) if len(parts) > 2 else "Module"

            user_sessions[user_id] = {"module_id": mod_id, "module_name": mod_name, "mode": "upload"}
            
            buttons = [
                [InlineKeyboardButton("🔗 Direct URL Mode", callback_data="set_mode_url")],
                [InlineKeyboardButton("📁 Telegram File Mode", callback_data="set_mode_file")]
            ]
            await query.message.edit_text(f"✅ **Module Set:** {mod_name}\n\nAb video bhejein ya URL add karein.", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)

@Client.on_callback_query(filters.regex("back_home"))
async def back_home(bot, query: CallbackQuery):
    await open_panel(bot, query.message)

@Client.on_callback_query(filters.regex(r"^set_mode_"))
async def set_upload_mode(bot, query: CallbackQuery):
    mode = query.data.split("_")[2]
    user_id = query.from_user.id
    if user_id in user_sessions:
        user_sessions[user_id]["mode"] = mode
        msg = "✅ Mode: **Direct URL**\nUse `/add Link | Name`" if mode == "url" else "✅ Mode: **Telegram File**\nJust forward video here."
        await query.message.edit_text(msg)
    else:
        await query.answer("Session expired. Type /panel", show_alert=True)

# Handle Video Uploads
@Client.on_message(filters.video | filters.document)
async def handle_video(bot, message: Message):
    # Try getting LOG_CHANNEL if not imported
    log_ch = LOG_CHANNEL
    if not log_ch:
        # Fallback: Agar LOG_CHANNEL info.py me nahi mila to error print hoga
        print("Log Channel ID missing") 
        return

    try:
        # Standard processing
        log_msg = await message.forward(log_ch)
        stream_link = f"{MY_WEBSITE_URL}/watch/{log_msg.id}"
        dl_link = f"{MY_WEBSITE_URL}/download/{log_msg.id}"
        
        buttons = []
        user_id = message.from_user.id
        
        # Check if user wants to add to firebase
        if user_id in user_sessions and user_sessions[user_id].get("mode") == "file":
            mod_name = user_sessions[user_id]['module_name']
            buttons.append([InlineKeyboardButton(f"Add to {mod_name}", callback_data=f"addfb_lec_{log_msg.id}")])
        
        buttons.append([InlineKeyboardButton("Download", url=dl_link)])
        
        await message.reply_text(
            f"**File:** `{message.video.file_name if message.video else message.document.file_name}`\n\nLINK: {stream_link}",
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )
    except Exception as e:
        print(f"Upload Error: {e}")

# Handle Add Button Click
@Client.on_callback_query(filters.regex(r"^addfb_"))
async def add_to_firebase(bot, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in user_sessions:
        await query.answer("Session expired.", show_alert=True)
        return

    data = query.data.split("_")
    log_id = data[2]
    session = user_sessions[user_id]
    
    stream_link = f"{MY_WEBSITE_URL}/watch/{log_id}"
    
    # Simple Name Logic
    fname = "Video Lecture"
    if query.message.reply_to_message:
        media = query.message.reply_to_message.video or query.message.reply_to_message.document
        if media: fname = media.file_name

    try:
        db.child("lectures").push({
            "name": fname,
            "url": stream_link,
            "module_id": session["module_id"],
            "type": "video"
        })
        await query.answer("Saved to Database!", show_alert=True)
        await query.message.edit_text(query.message.text + "\n\n✅ **Added to Course!**")
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)

# Handle Direct URL Command
@Client.on_message(filters.command("add"))
async def add_url(bot, message: Message):
    user_id = message.from_user.id
    if user_id not in user_sessions or user_sessions[user_id].get("mode") != "url":
        await message.reply("Please select 'Direct URL' mode in /panel first.")
        return
        
    try:
        _, text = message.text.split(" ", 1)
        url, name = text.split("|")
        
        db.child("lectures").push({
            "name": name.strip(),
            "url": url.strip(),
            "module_id": user_sessions[user_id]["module_id"],
            "type": "external"
        })
        await message.reply(f"✅ Added: {name.strip()}")
    except Exception as e:
        await message.reply(f"Usage: `/add Link | Name`\nError: {e}")
