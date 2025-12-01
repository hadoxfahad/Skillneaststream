import asyncio
import pyrebase
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# -----------------------------------------------------------------
# ERROR FIXING PART (Import Handling)
# -----------------------------------------------------------------
try:
    # Pehle koshish karega URL aur LOG_CHANNEL info.py se lene ki
    from info import URL, LOG_CHANNEL
except ImportError:
    # Agar URL nahi mila, to FQDN (dusra common naam) try karega
    try:
        from info import FQDN as URL, LOG_CHANNEL
    except ImportError:
        # Agar wo bhi nahi mila, toh hum yahan manually define kar rahe hain
        # IMPORTANT: Agar bot start ho jaye par link kaam na kare, 
        # to neeche wali line me apni website ka link daal dena.
        print("⚠️ Warning: URL variable not found in info.py, using manual fallback.")
        URL = "https://adminneast.firebaseapp.com" # Yahan apna Stream Link/Site URL likhein agar automatic fail ho
        from info import LOG_CHANNEL

# -----------------------------------------------------------------
# FIREBASE CONFIGURATION
# -----------------------------------------------------------------
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

# Firebase Initialize
try:
    firebase = pyrebase.initialize_app(firebaseConfig)
    db = firebase.database()
except Exception as e:
    print(f"Firebase Error: {e}")

# User Sessions
user_sessions = {}

# -----------------------------------------------------------------
# BOT LOGIC
# -----------------------------------------------------------------

@Client.on_message(filters.command("panel") & filters.private)
async def open_panel(bot, message):
    try:
        categories = db.child("categories").get()
        
        if not categories.val():
            await message.reply_text("❌ Database me koi Category nahi mili.\nPehle Website/Admin panel se categories add karein.")
            return

        buttons = []
        for cat in categories.each():
            key = cat.key()
            val = cat.val()
            cat_name = val.get("name", key) 
            buttons.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"cat_{key}")])

        await message.reply_text(
            "**Select a Category:**",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await message.reply_text(f"❌ Error connecting to Firebase: {e}")

@Client.on_callback_query(filters.regex(r"^(cat_|course_|mod_)"))
async def handle_callbacks(bot, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data.startswith("cat_"):
        cat_id = data.split("_")[1]
        courses = db.child("courses").order_by_child("category_id").equal_to(cat_id).get()
        
        if not courses.val():
            await query.answer("Empty Category.", show_alert=True)
            return

        buttons = []
        for course in courses.each():
            key = course.key()
            val = course.val()
            c_name = val.get("name", key)
            buttons.append([InlineKeyboardButton(f"🎓 {c_name}", callback_data=f"course_{key}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
        
        await query.message.edit_text(
            f"**Selected Category ID:** `{cat_id}`\nAb **Course** select karein:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("course_"):
        course_id = data.split("_")[1]
        modules = db.child("modules").order_by_child("course_id").equal_to(course_id).get()

        if not modules.val():
            await query.answer("Empty Course.", show_alert=True)
            return

        buttons = []
        for mod in modules.each():
            key = mod.key()
            val = mod.val()
            m_name = val.get("name", key)
            buttons.append([InlineKeyboardButton(f"📑 {m_name}", callback_data=f"mod_{key}_{m_name}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])

        await query.message.edit_text(
            f"**Selected Course ID:** `{course_id}`\nAb **Module** select karein:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("mod_"):
        parts = data.split("_")
        # Handle cases where name might contain underscores
        mod_id = parts[1]
        mod_name = "_".join(parts[2:]) if len(parts) > 2 else "Selected Module"

        user_sessions[user_id] = {
            "module_id": mod_id,
            "module_name": mod_name,
            "mode": "upload"
        }
        
        buttons = [
            [InlineKeyboardButton("🔗 Upload via Direct URL", callback_data="set_mode_url")],
            [InlineKeyboardButton("📁 Upload via Telegram File", callback_data="set_mode_file")]
        ]

        await query.message.edit_text(
            f"✅ **Module Set:** {mod_name}\nID: `{mod_id}`\n\nAb video bhejein ya URL add karein.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

@Client.on_callback_query(filters.regex("back_home"))
async def back_home(bot, query: CallbackQuery):
    await open_panel(bot, query.message)

@Client.on_callback_query(filters.regex(r"^set_mode_"))
async def set_upload_mode(bot, query: CallbackQuery):
    mode = query.data.split("_")[2]
    user_id = query.from_user.id
    
    if user_id not in user_sessions:
        await query.answer("Session expired.", show_alert=True)
        return

    user_sessions[user_id]["mode"] = mode
    if mode == "url":
        await query.message.edit_text("✅ Mode: **Direct URL**\nUse: `/add Link | Name`")
    else:
        await query.message.edit_text("✅ Mode: **Telegram File**\nVideo forward karein.")

@Client.on_message(filters.video | filters.document)
async def handle_video(bot, message: Message):
    user_id = message.from_user.id
    
    # Normal streaming logic continues...
    try:
        file = message.video or message.document
        filename = file.file_name if file.file_name else "Video File"
        
        log_msg = await message.forward(LOG_CHANNEL)
        stream_link = f"{URL}/watch/{log_msg.id}" 
        download_link = f"{URL}/download/{log_msg.id}"
        
        text = f"**File:** `{filename}`\n🔗 [Stream]({stream_link}) | 📥 [Download]({download_link})"
        
        buttons = []
        if user_id in user_sessions and user_sessions[user_id].get("mode") == "file":
            mod_name = user_sessions[user_id]['module_name']
            buttons.append([InlineKeyboardButton(f"Add to {mod_name} (Lec)", callback_data=f"addfb_lec_{log_msg.id}")])
            buttons.append([InlineKeyboardButton(f"Add to {mod_name} (Res)", callback_data=f"addfb_res_{log_msg.id}")])
        
        buttons.append([InlineKeyboardButton("Download Now", url=download_link)])
        
        await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)
            
    except Exception as e:
        print(f"Error: {e}")

@Client.on_callback_query(filters.regex(r"^addfb_"))
async def add_to_firebase(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data.split("_")
    type_ = data[1]
    log_id = data[2]
    
    if user_id not in user_sessions:
        await query.answer("Session expired.", show_alert=True)
        return
        
    session = user_sessions[user_id]
    stream_link = f"{URL}/watch/{log_id}"
    
    file_name = "New Video"
    if query.message.reply_to_message:
        media = query.message.reply_to_message.video or query.message.reply_to_message.document
        if media and media.file_name:
            file_name = media.file_name

    db_path = "lectures" if type_ == "lec" else "resources"
    
    try:
        db.child(db_path).push({
            "name": file_name,
            "url": stream_link,
            "module_id": session["module_id"],
            "type": "video"
        })
        await query.answer("✅ Saved!", show_alert=True)
        await query.message.edit_text(f"{query.message.text}\n\n✅ **Added to DB**")
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)

@Client.on_message(filters.command("add") & filters.private)
async def add_direct_url(bot, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_sessions or user_sessions[user_id].get("mode") != "url":
        await message.reply("❌ Panel se 'Direct URL' mode select karein.")
        return

    try:
        if "|" in message.text:
            text = message.text.split(" ", 1)[1]
            url, name = text.split("|")
            db.child("lectures").push({
                "name": name.strip(),
                "url": url.strip(),
                "module_id": user_sessions[user_id]["module_id"],
                "type": "external"
            })
            await message.reply(f"✅ **Added!** {name.strip()}")
        else:
            await message.reply("❌ Use: `/add Link | Name`")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
