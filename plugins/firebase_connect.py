import asyncio
import os
import urllib.parse
import time
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

# Session Structure
user_session = {} 

# --- Helper Functions ---

async def get_stream_link(message: Message):
    """Generates Direct Link & Cleans Filename (Removes _ )"""
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        
        if message.video:
            file_name = message.video.file_name or f"Video {log_msg.id}.mp4"
        elif message.document:
            file_name = message.document.file_name or f"File {log_msg.id}.pdf"
        else:
            file_name = f"File {log_msg.id}"
            
        # 1. Extension Hatana
        name_without_ext = os.path.splitext(file_name)[0]
        
        # 2. Underscore (_) ko Space ( ) se replace karna
        clean_name = name_without_ext.replace("_", " ")
        
        # URL Safe Filename (Link ke liye)
        safe_filename = urllib.parse.quote_plus(file_name)
        
        # Direct Download Link (/dl/)
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
    user_session[user_id] = {"state": "idle"}
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Change Mode", callback_data="fb_mode_menu")]
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

# 3. Modules (With CREATE Option)
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    cat_id = user_session[user_id].get("cat_id")
    user_session[user_id]["batch_id"] = batch_id
    user_session[user_id]["state"] = "idle"
    
    try:
        modules_ref = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get()
        buttons = []
        if modules_ref.each():
            for mod in modules_ref.each():
                m_name = get_name(mod.val())
                buttons.append([InlineKeyboardButton(m_name, callback_data=f"fb_set_mod_{mod.key()}")])
        
        # Add "Create Module" Button
        buttons.append([InlineKeyboardButton("➕ Create New Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        
        await query.message.edit_text(f"**Batch Selected!**\n\nModule select karein ya naya banayein:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error: {e}")

# 4. Set Module (And Show Existing Lectures)
@Client.on_callback_query(filters.regex("^fb_set_mod_"))
async def set_active_module(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    cat_id = user_session[user_id]["cat_id"]
    batch_id = user_session[user_id]["batch_id"]
    
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["state"] = "idle"
    user_session[user_id]["mode"] = user_session[user_id].get("mode", "file")
    
    # Fetch existing lectures to show
    msg_text = f"✅ **Module Configured!**\nID: `{module_id}`\n\n"
    
    try:
        lectures = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(module_id).child("lectures").get()
        
        if lectures.each():
            msg_text += "**📜 Existing Lectures:**\n"
            count = 1
            for l in lectures.each():
                l_name = get_name(l.val())
                msg_text += f"{count}. {l_name}\n"
                count += 1
                if count > 10: # Limit display
                    msg_text += "...and more"
                    break
        else:
            msg_text += "🚫 No lectures found yet."
            
    except:
        msg_text += "Error fetching lectures list."

    msg_text += "\n\n⬇️ **Ab Video upload karein:**"
    
    await query.message.edit_text(
        msg_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Reset", callback_data="fb_cat_list")]])
    )

# --- CREATE MODULE LOGIC ---

@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def ask_module_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_mod_creation"
    await query.message.edit_text(
        "🆕 **Create New Module**\n\nModule ka naam likh kar bhejein:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"fb_sel_batch_{user_session[user_id]['batch_id']}")]]))

# --- TEXT HANDLER (Rename & Create Module & URL Mode) ---

@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text_inputs(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    
    state = user_session[user_id].get("state")
    
    # 1. Creating New Module
    if state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat_id = user_session[user_id]["cat_id"]
        batch_id = user_session[user_id]["batch_id"]
        
        timestamp = int(time.time() * 1000)
        
        entry_data = {
            "name": mod_name,
            "order": timestamp
        }
        
        try:
            path_ref = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules")
            push_ref = path_ref.push(entry_data)
            gen_key = push_ref['name']
            path_ref.child(gen_key).update({"id": gen_key})
            
            await message.reply_text(f"✅ **Module Created!**\nName: {mod_name}")
            
            # Refresh List (Trick: send user back to list)
            # Cannot trigger callback via message, so sending text instructions
            await message.reply_text("List refresh karne ke liye `/firebase` dabayein ya Back button use karein.")
            user_session[user_id]["state"] = "idle"
            
        except Exception as e:
            await message.reply_text(f"Error creating module: {e}")

    # 2. Renaming Video
    elif state == "waiting_for_name":
        if message.text.startswith("/"): return 
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "idle" 
        await message.reply_text(f"✅ Name set: **{new_name}**")
        await ask_file_type(message, new_name, user_session[user_id]["temp_data"]["url"])

    # 3. URL Mode
    elif user_session[user_id].get("mode") == "url" and "module_id" in user_session[user_id]:
        await direct_url_logic(bot, message)

# --- FILE PROCESSING ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session or "module_id" not in user_session[user_id]:
        return
    if user_session[user_id].get("state") == "waiting_mod_creation": return
    if user_session[user_id].get("mode") == "url":
        return await message.reply("⚠️ URL Mode Active. File allow nahi hai.")

    status_msg = await message.reply_text("🔄 **Generating Direct Link...**")
    stream_link, clean_name, log_id = await get_stream_link(message)
    
    if not stream_link:
        return await status_msg.edit("Error generating link.")
    
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    
    buttons = [
        [InlineKeyboardButton("✅ Use Default Name", callback_data="fb_name_keep")],
        [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")]
    ]
    
    await status_msg.edit_text(
        f"**✅ Link Generated!**\n\n"
        f"**Name:** `{clean_name}`\n"
        f"**Link:** `{stream_link}`\n\n"
        f"Select Name Option:",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

# --- NAMING & TYPE ---

@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_default_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"], data["url"])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def ask_for_rename(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **New Name Type Karein:**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="fb_cat_list")]]))

async def ask_file_type(message, title, url):
    buttons = [
        [
            InlineKeyboardButton("🎬 Add Lecture", callback_data="fb_confirm_lec"),
            InlineKeyboardButton("📄 Add Resource", callback_data="fb_confirm_res")
        ]
    ]
    text = f"**📌 Final Confirmation**\n\n**Name:** `{title}`\n**Link:** `{url}`\n\nAdd to Firebase?"
    if isinstance(message, Message):
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
    else:
        pass

# --- FIREBASE PUSH ---

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_to_firebase(bot, query: CallbackQuery):
    action = query.data.split("_")[2]
    user_id = query.from_user.id
    
    if user_id not in user_session or "temp_data" not in user_session[user_id]:
        return await query.answer("Session expired.", show_alert=True)
    
    data = user_session[user_id]["temp_data"]
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
            f"✅ **Success!**\n\nAdded to {target_node}\n**Name:** {data['title']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Close", callback_data="fb_cat_list")]])
        )
    except Exception as e:
        await query.message.edit_text(f"❌ Error: {e}")

# --- URL MODE ---

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
    timestamp = int(time.time() * 1000)

    entry_data = {"name": title, "link": url, "order": timestamp}
    path_ref = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").child(module_id).child("lectures")
    push_ref = path_ref.push(entry_data)
    gen_key = push_ref['name']
    path_ref.child(gen_key).update({"id": gen_key})
    
    await message.reply_text(f"✅ **Link Added!**\nName: {title}", disable_web_page_preview=True)
