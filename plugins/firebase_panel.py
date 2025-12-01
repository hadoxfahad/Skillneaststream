import asyncio
import pyrebase
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from info import URL, LOG_CHANNEL 

# -----------------------------------------------------------------
# FIREBASE CONFIGURATION (Directly Added Here)
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
firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

# User Sessions (Temporary memory to store user selection)
user_sessions = {}

# -----------------------------------------------------------------
# BOT LOGIC STARTS HERE
# -----------------------------------------------------------------

# --- 1. Command to Start the Panel ---
@Client.on_message(filters.command("panel") & filters.private)
async def open_panel(bot, message):
    try:
        # Firebase se Categories fetch karega
        categories = db.child("categories").get()
        
        if not categories.val():
            await message.reply_text("❌ Database me koi Category nahi mili.\nPehle Website/Admin panel se categories add karein.")
            return

        buttons = []
        # Categories ke buttons banao
        for cat in categories.each():
            key = cat.key()
            val = cat.val()
            # Try to get name, if not found use key
            cat_name = val.get("name", key) 
            buttons.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"cat_{key}")])

        await message.reply_text(
            "**Select a Category:**\nJis category me lecture add karna hai use select karein.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await message.reply_text(f"❌ Error connecting to Firebase: {e}")

# --- 2. Handle Callback Queries (Navigation) ---
@Client.on_callback_query(filters.regex(r"^(cat_|course_|mod_)"))
async def handle_callbacks(bot, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    # -- Category Clicked -> Show Courses --
    if data.startswith("cat_"):
        cat_id = data.split("_")[1]
        courses = db.child("courses").order_by_child("category_id").equal_to(cat_id).get()
        
        if not courses.val():
            await query.answer("Is category me koi course nahi hai.", show_alert=True)
            return

        buttons = []
        for course in courses.each():
            key = course.key()
            val = course.val()
            c_name = val.get("name", key)
            buttons.append([InlineKeyboardButton(f"🎓 {c_name}", callback_data=f"course_{key}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
        
        await query.message.edit_text(
            f"**Selected Category ID:** `{cat_id}`\n\nAb **Course** select karein:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # -- Course Clicked -> Show Modules --
    elif data.startswith("course_"):
        course_id = data.split("_")[1]
        modules = db.child("modules").order_by_child("course_id").equal_to(course_id).get()

        if not modules.val():
            await query.answer("Is course me koi module nahi hai.", show_alert=True)
            return

        buttons = []
        for mod in modules.each():
            key = mod.key()
            val = mod.val()
            m_name = val.get("name", key)
            # Button click par module set ho jayega
            buttons.append([InlineKeyboardButton(f"📑 {m_name}", callback_data=f"mod_{key}_{m_name}")])
        
        # Note: Back logic can be improved to remember IDs, currently basic
        buttons.append([InlineKeyboardButton("🔙 Back (Restart)", callback_data="back_home")]) 

        await query.message.edit_text(
            f"**Selected Course ID:** `{course_id}`\n\nAb **Module** select karein jisme video daalni hai:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # -- Module Clicked -> Set Session --
    elif data.startswith("mod_"):
        try:
            _, mod_id, mod_name = data.split("_", 2)
        except ValueError:
             _, mod_id, mod_name = data.split("_", 2) if len(data.split("_")) > 2 else (None, data.split("_")[1], "Unknown")

        # User ka session save kar rahe hain
        user_sessions[user_id] = {
            "module_id": mod_id,
            "module_name": mod_name,
            "mode": "upload" # Default mode file upload
        }
        
        buttons = [
            [InlineKeyboardButton("🔗 Upload via Direct URL", callback_data="set_mode_url")],
            [InlineKeyboardButton("📁 Upload via Telegram File", callback_data="set_mode_file")]
        ]

        await query.message.edit_text(
            f"✅ **Module Set Successfully!**\n\n"
            f"📌 **Selected Module:** {mod_name}\n"
            f"🆔 **ID:** `{mod_id}`\n\n"
            f"Ab aap jo bhi **Video** bhejenge ya **URL** denge wo is module me add hoga.\n\n"
            f"Agar direct link add karni hai toh 'Upload via Direct URL' select karein.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

@Client.on_callback_query(filters.regex("back_home"))
async def back_home(bot, query: CallbackQuery):
    await open_panel(bot, query.message)

# --- 3. Mode Selection (Direct URL vs File) ---
@Client.on_callback_query(filters.regex(r"^set_mode_"))
async def set_upload_mode(bot, query: CallbackQuery):
    mode = query.data.split("_")[2] # url or file
    user_id = query.from_user.id
    
    if user_id not in user_sessions:
        await query.answer("Session expired. /panel again.", show_alert=True)
        return

    user_sessions[user_id]["mode"] = mode
    
    if mode == "url":
        await query.message.edit_text("✅ Mode: **Direct URL**\n\nAb command use karein:\n`/add <Link> | <Name>`\n\nExample:\n`/add http://vids.com/lec1.mp4 | Introduction`")
    else:
        await query.message.edit_text("✅ Mode: **Telegram File**\n\nAb bas video forward karein ya upload karein is chat me.")


# --- 4. Handle Video Uploads (Logic to Generate Link & Show Add Button) ---
@Client.on_message(filters.video | filters.document)
async def handle_video(bot, message: Message):
    user_id = message.from_user.id
    
    # Check if user has selected a module
    if user_id not in user_sessions or user_sessions[user_id].get("mode") != "file":
        # Agar panel set nahi hai, to normal bot ki tarah behave karega
        pass

    # File process karke Log Channel me forward karna
    try:
        file = message.video or message.document
        filename = file.file_name if file.file_name else "Video File"
        
        # Forward to Log Channel
        log_msg = await message.forward(LOG_CHANNEL)
        
        # Generate Stream Link (Using Info.py URL)
        stream_link = f"{URL}/watch/{log_msg.id}" 
        download_link = f"{URL}/download/{log_msg.id}"
        
        text = f"**File Name:** `{filename}`\n\n" \
               f"🖥 **Stream:** {stream_link}\n" \
               f"📥 **Download:** {download_link}"
        
        buttons = []
        
        # Agar user ne Module set kiya hai, toh Firebase button dikhao
        if user_id in user_sessions and user_sessions[user_id].get("mode") == "file":
            mod_name = user_sessions[user_id]['module_name']
            buttons.append([InlineKeyboardButton(f"➕ Add to {mod_name} (Lec)", callback_data=f"addfb_lec_{log_msg.id}")])
            buttons.append([InlineKeyboardButton(f"➕ Add to {mod_name} (Res)", callback_data=f"addfb_res_{log_msg.id}")])
        
        buttons.append([InlineKeyboardButton("Download Now", url=download_link)])
        
        await message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )
            
    except Exception as e:
        print(f"Error in handle_video: {e}")
        pass

# --- 5. Handle "Add to Firebase" Button Click ---
@Client.on_callback_query(filters.regex(r"^addfb_"))
async def add_to_firebase(bot, query: CallbackQuery):
    user_id = query.from_user.id
    dat
