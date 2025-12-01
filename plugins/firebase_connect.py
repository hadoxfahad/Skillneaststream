import asyncio
import os
import json
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

user_session = {} 

# --- Helper: Safe ID Comparison ---
def check_id_match(data, target_id, keys_to_check):
    """Multiple keys check karta hai match ke liye"""
    target_str = str(target_id).strip()
    
    for key in keys_to_check:
        if key in data:
            val = str(data[key]).strip()
            if val == target_str:
                return True
    return False

async def get_stream_link(message: Message):
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

# --- Main Command ---
@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    await message.reply_text(
        "**🔥 Firebase Admin Panel**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Change Mode", callback_data="fb_mode_menu")]
        ])
    )

# --- Navigation Callbacks ---

# 1. Categories
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        cats = db.child("categories").get()
        buttons = []
        print("\n--- DEBUG: CATEGORIES ---")
        if cats.each():
            for cat in cats.each():
                c_data = cat.val()
                c_key = cat.key()
                c_name = c_data.get("name", "Unnamed")
                print(f"Key: {c_key}, Name: {c_name}")
                buttons.append([InlineKeyboardButton(c_name, callback_data=f"fb_sel_cat_{c_key}")])
        
        await query.message.edit_text("**Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# 2. Courses (FIXED)
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_courses(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["cat_id"] = cat_id
    
    try:
        all_courses = db.child("courses").get()
        buttons = []
        
        print(f"\n--- DEBUG: LOOKING FOR CAT_ID: {cat_id} ---")
        
        if all_courses.each():
            for course in all_courses.each():
                c_data = course.val()
                c_key = course.key()
                
                # Debug Print: Logs me check karna agar button na aaye
                print(f"Checking Course: {c_data.get('name')} | Data: {c_data}")

                # Check multiple possible field names
                is_match = check_id_match(c_data, cat_id, ["categoryId", "category_id", "cat_id", "catId", "parent_id"])
                
                if is_match:
                    c_name = c_data.get("name", "Unnamed")
                    buttons.append([InlineKeyboardButton(c_name, callback_data=f"fb_sel_course_{c_key}")])
        
        if not buttons:
            buttons.append([InlineKeyboardButton("No Courses Found (Check Logs)", callback_data="ignore")])
            
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**Category ID:** `{cat_id}`\n\nCourse select karein:", reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        print(f"Error in courses: {e}")
        await query.message.edit_text(f"Error fetching courses: {e}")

# 3. Modules (FIXED)
@Client.on_callback_query(filters.regex("^fb_sel_course_"))
async def list_modules(bot, query: CallbackQuery):
    course_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["course_id"] = course_id
    
    try:
        all_modules = db.child("modules").get()
        buttons = []
        
        print(f"\n--- DEBUG: LOOKING FOR COURSE_ID: {course_id} ---")

        if all_modules.each():
            for mod in all_modules.each():
                m_data = mod.val()
                m_key = mod.key()
                
                print(f"Checking Module: {m_data.get('name')} | Data: {m_data}")

                # Check multiple possible field names
                is_match = check_id_match(m_data, course_id, ["courseId", "course_id", "course_Id", "parent_id"])
                
                if is_match:
                    m_name = m_data.get("name", "Unnamed")
                    buttons.append([InlineKeyboardButton(m_name, callback_data=f"fb_set_mod_{m_key}")])
        
        if not buttons:
            buttons.append([InlineKeyboardButton("No Modules Found", callback_data="ignore")])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{user_session[user_id]['cat_id']}")])
        await query.message.edit_text(f"**Course ID:** `{course_id}`\n\nModule select karein:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error fetching modules: {e}")

# 4. Set Module
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
        return await message.reply("⚠️ Mode 'Link' hai. File ke liye mode change karein.")

    status_msg = await message.reply_text("🔄 **Processing...**")
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
        f"**File:** `{clean_name}`\n\nAdd to Website?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Confirm Add ---
@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_to_firebase(bot, query: CallbackQuery):
    action = query.data.split("_")[2]
    user_id = query.from_user.id
    
    if user_id not in user_session or "temp_data" not in user_session[user_id]:
        return await query.answer("Session expired.", show_alert=True)
    
    data = user_session[user_id]["temp_data"]
    module_id = user_session[user_id]["module_id"]
    type_ = "video" if action == "lec" else "pdf"
    
    new_entry = {
        "moduleId": module_id,
        "title": data["title"],
        "url": data["url"],
        "type": type_,
        "createdAt": {".sv": "timestamp"}
    }
    
    try:
        db.child("lectures").push(new_entry)
        await query.message.edit_text(f"✅ **Added!**\n{data['title']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close", callback_data="ignore")]]))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# --- Mode & URL ---
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
    await query.message.edit_text(f"✅ Mode: **{mode.upper()}**")

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

        db.child("lectures").push({
            "moduleId": user_session[user_id]["module_id"],
            "title": title,
            "url": url,
            "type": "video",
            "createdAt": {".sv": "timestamp"}
        })
        await message.reply_text(f"✅ Added: {title}")
