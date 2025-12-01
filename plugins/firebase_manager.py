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

# --- 2. User State Management ---
# user_session structure:
# {
#   user_id: {
#       "cat_id": "...", 
#       "course_id": "...", 
#       "module_id": "...", 
#       "mode": "file",
#       "temp_data": {"title": "...", "link": "..."}  <-- Data hold karne ke liye
#   }
# }
user_session = {} 

# --- 3. Helper Functions ---

async def get_stream_link(message: Message):
    """File ko Log Channel me forward karke Stream URL banata hai"""
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        stream_link = f"{STREAM_URL}/watch/{log_msg.id}"
        
        # File Name nikalna
        if message.video:
            file_name = message.video.file_name or "Unknown Video"
        elif message.document:
            file_name = message.document.file_name or "Unknown File"
        else:
            file_name = "Unknown_File"
            
        # Extension hatana (Example: 'Video.mp4' -> 'Video')
        clean_name = os.path.splitext(file_name)[0]
        
        return stream_link, clean_name, log_msg.id
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None, None

# --- 4. Main Command ---
@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nCategory select karke start karein:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Change Mode (File/Link)", callback_data="fb_mode_menu")]
        ])
    )

# --- 5. Navigation (Fix for Courses Not Showing) ---

# A. Categories List
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        cats = db.child("categories").get()
        buttons = []
        if cats.each():
            for cat in cats.each():
                c_name = cat.val().get("name", "Unnamed")
                buttons.append([InlineKeyboardButton(c_name, callback_data=f"fb_sel_cat_{cat.key()}")])
        
        await query.message.edit_text("**Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error fetching categories: {e}")

# B. Courses List (FIXED LOGIC)
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_courses(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["cat_id"] = cat_id
    
    try:
        all_courses = db.child("courses").get()
        buttons = []
        
        if all_courses.each():
            for course in all_courses.each():
                c_data = course.val()
                
                # Fetching IDs from DB
                # DB me kabhi 'categoryId' hota hai kabhi 'category_id'
                # Aur kabhi ye Integer hota hai kabhi String
                db_cat_id = c_data.get("categoryId") or c_data.get("category_id")
                
                # STRICT COMPARISON: Dono ko String bana kar match karein
                if str(db_cat_id) == str(cat_id):
                    c_name = c_data.get("name", "Unnamed")
                    buttons.append([InlineKeyboardButton(c_name, callback_data=f"fb_sel_course_{course.key()}")])
        
        if not buttons:
            buttons.append([InlineKeyboardButton("No Courses Found", callback_data="ignore")])
            
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**Category ID:** `{cat_id}`\n\nAb Course select karein:", reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        await query.message.edit_text(f"Error fetching courses: {e}")

# C. Modules List
@Client.on_callback_query(filters.regex("^fb_sel_course_"))
async def list_modules(bot, query: CallbackQuery):
    course_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["course_id"] = course_id
    
    try:
        all_modules = db.child("modules").get()
        buttons = []
        if all_modules.each():
            for mod in all_modules.each():
                m_data = mod.val()
                db_course_id = m_data.get("courseId") or m_data.get("course_id")
                
                # String comparison fix here too
                if str(db_course_id) == str(course_id):
                    m_name = m_data.get("name", "Unnamed")
                    buttons.append([InlineKeyboardButton(m_name, callback_data=f"fb_set_mod_{mod.key()}")])
        
        if not buttons:
            buttons.append([InlineKeyboardButton("No Modules Found", callback_data="ignore")])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{user_session[user_id]['cat_id']}")])
        await query.message.edit_text(f"**Course ID:** `{course_id}`\n\nAb Module select karein:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error fetching modules: {e}")

# D. Set Module
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["mode"] = user_session[user_id].get("mode", "file")
    
    await query.message.edit_text(
        f"✅ **Module Selected!**\nID: `{module_id}`\n\nAb Video/File bhejein. Main uska Naam aur Link khud nikal lunga.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Reset", callback_data="fb_cat_list")]])
    )

# --- 6. File Handler (Video Upload -> Name/Link Extraction) ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    if user_id not in user_session or "module_id" not in user_session[user_id]:
        return # Module not selected
        
    if user_session[user_id].get("mode") == "url":
        return await message.reply("⚠️ Mode 'Link' par hai. File upload ke liye Mode change karein.")

    status_msg = await message.reply_text("🔄 **Processing...**\nLink generate kar raha hu aur Naam nikal raha hu...")
    
    stream_link, clean_name, log_id = await get_stream_link(message)
    
    if not stream_link:
        return await status_msg.edit("Error: Link generate nahi hua.")
    
    # Store data temporarily for the button click
    user_session[user_id]["temp_data"] = {
        "title": clean_name,
        "url": stream_link,
        "type": "video" # default
    }
    
    buttons = [
        [
            InlineKeyboardButton("➕ Add as Lecture", callback_data="fb_confirm_lec"),
            InlineKeyboardButton("➕ Add as Resource", callback_data="fb_confirm_res")
        ],
        [
            InlineKeyboardButton("▶️ Check Link", url=stream_link)
        ]
    ]
    
    await status_msg.edit_text(
        f"**File Name:** `{clean_name}`\n**Stream URL:** Available\n\nKya isse website par add karu?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- 7. Final Add to Firebase (Button Click) ---

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_to_firebase(bot, query: CallbackQuery):
    action = query.data.split("_")[2] # 'lec' or 'res'
    user_id = query.from_user.id
    
    if user_id not in user_session or "temp_data" not in user_session[user_id]:
        return await query.answer("Session expired. Dobara file bhejein.", show_alert=True)
    
    data = user_session[user_id]["temp_data"]
    module_id = user_session[user_id]["module_id"]
    
    # Set type based on button
    final_type = "video" if action == "lec" else "pdf"
    
    new_entry = {
        "moduleId": module_id,
        "title": data["title"], # File ka real naam
        "url": data["url"],     # Stream Link
        "type": final_type,
        "createdAt": {".sv": "timestamp"}
    }
    
    try:
        db.child("lectures").push(new_entry)
        await query.message.edit_text(
            f"✅ **Added Successfully!**\n\n**Name:** {data['title']}\n**Module:** `{module_id}`\n\nWebsite check karein.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Send Next Video", callback_data="ignore")]])
        )
    except Exception as e:
        await query.message.edit_text(f"❌ Error: {e}")

# --- 8. Direct URL Mode (Custom Name | Link) ---

@Client.on_callback_query(filters.regex("^fb_mode_menu"))
async def mode_menu(bot, query: CallbackQuery):
    buttons = [
        [InlineKeyboardButton("📂 File Mode", callback_data="fb_setmode_file")],
        [InlineKeyboardButton("🔗 URL/Link Mode", callback_data="fb_setmode_url")]
    ]
    await query.message.edit_text("Select Mode:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_setmode_"))
async def set_mode_func(bot, query: CallbackQuery):
    mode = query.data.split("_")[2]
    user_id = query.from_user.id
    if user_id not in user_session: user_session[user_id] = {}
    
    user_session[user_id]["mode"] = mode
    await query.message.edit_text(f"✅ Mode Set: **{mode.upper()}**\nAb aap category select kar sakte hain.")

@Client.on_message(filters.text & filters.user(ADMINS))
async def direct_url_handler(bot, message):
    user_id = message.from_user.id
    
    # Check Valid Session
    if (user_id in user_session and 
        user_session[user_id].get("mode") == "url" and 
        "module_id" in user_session[user_id]):
            
            text = message.text.strip()
            
            # Format: Name | Link
            if "|" in text:
                parts = text.split("|", 1)
                title = parts[0].strip()
                url = parts[1].strip()
            elif "http" in text:
                title = "External Link"
                url = text
            else:
                return # Not a link
            
            new_entry = {
                "moduleId": user_session[user_id]["module_id"],
                "title": title,
                "url": url,
                "type": "video",
                "createdAt": {".sv": "timestamp"}
            }
            
            db.child("lectures").push(new_entry)
            await message.reply_text(f"✅ **Link Added!**\nName: {title}\nLink: {url}")
