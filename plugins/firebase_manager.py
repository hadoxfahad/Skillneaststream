# plugins/firebase_connect.py

import asyncio
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

# --- 2. User State Management ---
# Admin kis step par hai, ye track karne ke liye
user_session = {} 
# Structure: {user_id: {"cat_id": "xyz", "course_id": "abc", "module_id": "123", "mode": "file/url"}}

# --- 3. Helper Functions ---
async def get_stream_link(message: Message):
    """File ko Log Channel me forward karke Stream URL banata hai"""
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        # Unique ID ke liye message ID ka use
        stream_link = f"{STREAM_URL}/watch/{log_msg.id}"
        file_name = message.video.file_name if message.video else message.document.file_name if message.document else "Unknown File"
        return stream_link, file_name, log_msg.id
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None, None

# --- 4. Main Command (/firebase) ---
@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nNiche diye gaye options se start karein:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category & Module", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Change Mode (File/URL)", callback_data="fb_mode_menu")]
        ])
    )

# --- 5. Navigation Callbacks (Category -> Course -> Module) ---

# A. Categories List
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    cats = db.child("categories").get()
    buttons = []
    if cats.each():
        for cat in cats.each():
            # Button Name = Category Name, Data = Category ID
            c_name = cat.val().get("name", "Unnamed")
            buttons.append([InlineKeyboardButton(c_name, callback_data=f"fb_sel_cat_{cat.key()}")])
    
    await query.message.edit_text(
        "**Select Category:**\nWebsite se categories load ho gayi hain.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# B. Courses List
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_courses(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["cat_id"] = cat_id
    
    all_courses = db.child("courses").get()
    buttons = []
    if all_courses.each():
        for course in all_courses.each():
            c_data = course.val()
            # Check agar ye course selected category ka hai
            # Note: Database me field name check karein (categoryId vs category_id)
            if c_data.get("categoryId") == cat_id or c_data.get("category_id") == cat_id:
                buttons.append([InlineKeyboardButton(c_data.get("name", "Unnamed"), callback_data=f"fb_sel_course_{course.key()}")])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
    await query.message.edit_text(f"**Category ID:** `{cat_id}`\n\nAb Course select karein:", reply_markup=InlineKeyboardMarkup(buttons))

# C. Modules List
@Client.on_callback_query(filters.regex("^fb_sel_course_"))
async def list_modules(bot, query: CallbackQuery):
    course_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["course_id"] = course_id
    
    all_modules = db.child("modules").get()
    buttons = []
    if all_modules.each():
        for mod in all_modules.each():
            m_data = mod.val()
            if m_data.get("courseId") == course_id or m_data.get("course_id") == course_id:
                buttons.append([InlineKeyboardButton(m_data.get("name", "Unnamed"), callback_data=f"fb_set_mod_{mod.key()}")])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{user_session[user_id]['cat_id']}")])
    await query.message.edit_text(f"**Course ID:** `{course_id}`\n\nAb Module select karein:", reply_markup=InlineKeyboardMarkup(buttons))

# D. Set Module (Final Selection)
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["mode"] = user_session[user_id].get("mode", "file") # Default file mode
    
    await query.message.edit_text(
        f"✅ **Module Set Successfully!**\n\nModule ID: `{module_id}`\nMode: **{user_session[user_id]['mode'].upper()}**\n\nAb aap Video bhejein (File Mode) ya Link bhejein (URL Mode).",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Clear Selection", callback_data="fb_clear")]])
    )

# --- 6. File Handler (Video Upload -> Stream Link -> Firebase Button) ---
@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    # Check session
    if user_id not in user_session or "module_id" not in user_session[user_id]:
        return # Agar module set nahi hai to normal bot ki tarah behave karega
        
    if user_session[user_id].get("mode") == "url":
        return await message.reply("⚠️ Aapka mode 'URL' par set hai. File upload karne ke liye mode change karein.")

    processing = await message.reply_text("🔄 **Generating Stream Link & Preparing...**")
    
    stream_link, file_name, log_id = await get_stream_link(message)
    if not stream_link:
        return await processing.edit("Error generating link.")
    
    # Buttons create karna
    buttons = [
        [
            InlineKeyboardButton("➕ Add Lecture", callback_data=f"fb_add_lec_{log_id}"),
            InlineKeyboardButton("➕ Add Resource", callback_data=f"fb_add_res_{log_id}")
        ],
        [
            InlineKeyboardButton("📥 Download", url=stream_link),
            InlineKeyboardButton("▶️ Play Online", url=stream_link)
        ]
    ]
    
    await processing.edit_text(
        f"**File:** `{file_name}`\n\n**Stream Link:**\n`{stream_link}`\n\nNiche buttons se select karein ki isse Firebase me kaise add karna hai:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- 7. Final Add to Firebase Callback ---
@Client.on_callback_query(filters.regex("^fb_add_"))
async def push_to_firebase(bot, query: CallbackQuery):
    data = query.data.split("_")
    type_ = data[2] # 'lec' or 'res'
    log_id = data[3]
    
    user_id = query.from_user.id
    if user_id not in user_session or "module_id" not in user_session[user_id]:
        return await query.answer("Session Expired. Dobara /firebase start karein.", show_alert=True)
    
    module_id = user_session[user_id]["module_id"]
    stream_link = f"{STREAM_URL}/watch/{log_id}"
    
    # Data structure for Firebase
    new_entry = {
        "moduleId": module_id,
        "title": f"Lecture {log_id}" if type_ == "lec" else f"Resource {log_id}", 
        "url": stream_link,
        "type": "video" if type_ == "lec" else "pdf", # Aap isse aur customize kar sakte hain
        "createdAt": {".sv": "timestamp"}
    }
    
    # Push to Database
    try:
        db.child("lectures").push(new_entry)
        await query.message.edit_text(
            f"✅ **Successfully Added to Website!**\n\n**Type:** {type_.upper()}\n**Module:** `{module_id}`\n**Link:** `{stream_link}`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Close", callback_data="fb_clear")]])
        )
    except Exception as e:
        await query.message.edit_text(f"❌ Error adding to Firebase: {e}")

# --- 8. Direct URL Mode Logic ---
@Client.on_callback_query(filters.regex("^fb_mode_menu"))
async def mode_menu(bot, query: CallbackQuery):
    buttons = [
        [InlineKeyboardButton("📂 File Mode (Default)", callback_data="fb_setmode_file")],
        [InlineKeyboardButton("🔗 Direct URL Mode", callback_data="fb_setmode_url")]
    ]
    await query.message.edit_text("Select Mode:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_setmode_"))
async def set_mode_func(bot, query: CallbackQuery):
    mode = query.data.split("_")[2]
    user_id = query.from_user.id
    if user_id not in user_session: user_session[user_id] = {}
    
    user_session[user_id]["mode"] = mode
    await query.answer(f"Mode changed to: {mode.upper()}", show_alert=True)
    
    msg = f"Mode: **{mode.upper()}** selected."
    if "module_id" in user_session[user_id]:
        msg += f"\nActive Module: `{user_session[user_id]['module_id']}`"
    else:
        msg += "\nAb category select karne ke liye /firebase command dein."
        
    await query.message.edit_text(msg)

@Client.on_message(filters.text & filters.user(ADMINS))
async def direct_url_handler(bot, message):
    user_id = message.from_user.id
    
    # Check if URL Mode is active and Module is set
    if (user_id in user_session and 
        user_session[user_id].get("mode") == "url" and 
        "module_id" in user_session[user_id]):
            
            url = message.text.strip()
            if not url.startswith("http"):
                return # Ignore normal chat
            
            module_id = user_session[user_id]["module_id"]
            
            # Push Direct URL to Firebase
            new_entry = {
                "moduleId": module_id,
                "title": "Direct Link Lecture",
                "url": url,
                "type": "video",
                "createdAt": {".sv": "timestamp"}
            }
            
            db.child("lectures").push(new_entry)
            await message.reply_text(f"✅ **Direct Link Added!**\nModule: `{module_id}`\nURL: {url}")

# Clear Session
@Client.on_callback_query(filters.regex("^fb_clear"))
async def clear_session(bot, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in user_session:
        del user_session[user_id]
    await query.message.edit_text("✅ Session Cleared.")
