import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import pyrebase
from info import *  # Ensure ADMINS, LOG_CHANNEL, STREAM_URL are defined in info.py

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

# --- 2. Session Management ---
# Structure: {user_id: {'cat': id, 'batch': id, 'mod': id, 'sub_mod': id, 'is_sub': bool, 'state': str}}
user_session = {}

# --- 3. Helper Functions ---

def get_name(data):
    """Safe way to get name from Firebase data"""
    if not data: return "Unnamed"
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or "Unnamed"
    return "Unnamed"

async def get_stream_link(message: Message):
    """Generates Stream Link & Clean Filename"""
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        
        if message.video:
            file_name = message.video.file_name or f"Video_{log_msg.id}.mp4"
        elif message.document:
            file_name = message.document.file_name or f"File_{log_msg.id}.pdf"
        else:
            file_name = f"File_{log_msg.id}"
            
        name_without_ext = os.path.splitext(file_name)[0]
        clean_name = name_without_ext.replace("_", " ").replace("-", " ")
        
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name, log_msg.id
    except Exception as e:
        print(f"Link Gen Error: {e}")
        return None, None, None

# --- 4. Main Command & Navigation ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    user_session[user_id] = {"state": "idle", "is_sub": False} # Reset
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!\nSelect a Category:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")]
        ])
    )

# -- Category List --
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        cats = db.child("categories").get().val()
        buttons = []
        if cats:
            iterable = cats.items() if isinstance(cats, dict) else enumerate(cats)
            for key, val in iterable:
                if val: buttons.append([InlineKeyboardButton(f"📂 {get_name(val)}", callback_data=f"fb_sel_cat_{key}")])
        
        await query.message.edit_text("**📂 Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# -- Batch List --
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_session[query.from_user.id]["cat"] = cat_id
    
    try:
        batches = db.child("categories").child(cat_id).child("batches").get().val()
        buttons = []
        if batches:
            iterable = batches.items() if isinstance(batches, dict) else enumerate(batches)
            for key, val in iterable:
                if val: buttons.append([InlineKeyboardButton(f"🎓 {get_name(val)}", callback_data=f"fb_sel_batch_{key}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**📂 Category:** `{cat_id}`\nSelect Batch:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# -- Module List --
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["batch"] = batch_id
    cat_id = user_session[user_id]["cat"]
    
    try:
        modules = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get().val()
        buttons = []
        if modules:
            iterable = modules.items() if isinstance(modules, dict) else enumerate(modules)
            for key, val in iterable:
                if val: buttons.append([InlineKeyboardButton(f"📺 {get_name(val)}", callback_data=f"fb_mod_menu_{key}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        
        await query.message.edit_text(f"**🎓 Batch:** `{batch_id}`\nSelect Module:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# --- 5. Module & Sub-Module Logic (The Core Request) ---

@Client.on_callback_query(filters.regex("^fb_mod_menu_"))
async def module_menu(bot, query: CallbackQuery):
    mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["mod"] = mod_id
    user_session[user_id]["is_sub"] = False # Reset submodule flag
    user_session[user_id]["sub_mod"] = None

    buttons = [
        [InlineKeyboardButton("✅ Upload to THIS Module", callback_data="fb_set_active_main")],
        [InlineKeyboardButton("📂 Open Sub-Modules", callback_data=f"fb_list_sub_{mod_id}")],
        [InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_create_sub_ask")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_batch_{user_session[user_id]['batch']}")]
    ]
    await query.message.edit_text(f"**📺 Module:** `{mod_id}`\nWhat do you want to do?", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_list_sub_"))
async def list_sub_modules(bot, query: CallbackQuery):
    mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    cat, batch = user_session[user_id]["cat"], user_session[user_id]["batch"]
    
    try:
        # Fetching SubModules
        sub_mods = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod_id).child("subModules").get().val()
        buttons = []
        
        if sub_mods:
            iterable = sub_mods.items() if isinstance(sub_mods, dict) else enumerate(sub_mods)
            for key, val in iterable:
                buttons.append([InlineKeyboardButton(f"📑 {get_name(val)}", callback_data=f"fb_set_active_sub_{key}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_create_sub_ask")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_mod_menu_{mod_id}")])
        
        await query.message.edit_text(f"**📂 Sub-Modules inside `{mod_id}`**\nSelect one to upload inside it:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# --- 6. Set Active Dashboard ---

@Client.on_callback_query(filters.regex("^fb_set_active_"))
async def set_dashboard(bot, query: CallbackQuery):
    data = query.data.split("_")
    mode = data[3] # 'main' or 'sub'
    user_id = query.from_user.id
    
    if mode == "sub":
        sub_id = data[4]
        user_session[user_id]["is_sub"] = True
        user_session[user_id]["sub_mod"] = sub_id
        target_name = "Sub-Module"
    else:
        user_session[user_id]["is_sub"] = False
        user_session[user_id]["sub_mod"] = None
        target_name = "Main Module"
        
    user_session[user_id]["state"] = "active"
    await refresh_dashboard(bot, query.message, user_id, target_name)

async def refresh_dashboard(bot, message, user_id, target_name):
    sess = user_session[user_id]
    fast_mode = sess.get("fast", False)
    fast_emoji = "🟢 ON" if fast_mode else "🔴 OFF"
    
    details = f"📺 **Mod:** `{sess['mod']}`"
    if sess['is_sub']:
        details += f"\n📑 **Sub-Mod:** `{sess['sub_mod']}`"
        
    text = (f"✅ **Target Locked: {target_name}**\n{details}\n\n"
            f"⚡ **Fast Mode:** {fast_emoji}\n"
            "⬇️ **Send Video/PDF now to upload!**")
            
    buttons = [
        [InlineKeyboardButton("⚡ Toggle Fast Mode", callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("🔙 Back / Stop", callback_data=f"fb_mod_menu_{sess['mod']}")]
    ]
    
    # Check if called from callback or message
    if isinstance(message, Message):
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast(bot, query: CallbackQuery):
    user_id = query.from_user.id
    curr = user_session[user_id].get("fast", False)
    
    if not curr:
        # Enable logic
        await query.message.edit_text(
            "**⚡ Fast Mode Setup**\nSelect default upload type:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Always Lectures", callback_data="fb_fast_set_lectures")],
                [InlineKeyboardButton("📄 Always Resources", callback_data="fb_fast_set_resources")]
            ])
        )
    else:
        # Disable
        user_session[user_id]["fast"] = False
        target = "Sub-Module" if user_session[user_id]["is_sub"] else "Main Module"
        await refresh_dashboard(bot, query.message, user_id, target)

@Client.on_callback_query(filters.regex("^fb_fast_set_"))
async def set_fast_type(bot, query: CallbackQuery):
    u_type = query.data.split("_")[3] # lectures or resources
    user_session[query.from_user.id]["fast"] = True
    user_session[query.from_user.id]["fast_type"] = u_type
    target = "Sub-Module" if user_session[query.from_user.id]["is_sub"] else "Main Module"
    await query.answer("⚡ Fast Mode Activated!")
    await refresh_dashboard(bot, query.message, query.from_user.id, target)

# --- 7. File Upload Handler ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def handle_file(bot, message):
    user_id = message.from_user.id
    if user_session.get(user_id, {}).get("state") != "active":
        return await message.reply("⚠️ **Dashboard not active!**\nUse /firebase to start.")
        
    sess = user_session[user_id]
    
    # 1. Generate Link
    processing = await message.reply("🔄 Processing...")
    stream_link, clean_name, _ = await get_stream_link(message)
    
    if not stream_link:
        return await processing.edit("❌ Error generating link.")
    
    # 2. Check Fast Mode
    if sess.get("fast"):
        upload_type = sess["fast_type"]
        await push_to_firebase(bot, message, user_id, clean_name, stream_link, upload_type)
        await processing.delete()
        return

    # 3. Manual Mode
    user_session[user_id]["temp"] = {"name": clean_name, "link": stream_link}
    await processing.delete()
    await message.reply_text(
        f"📂 **File:** `{clean_name}`\n\nWhere to add?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 As Lecture", callback_data="fb_confirm_lectures")],
            [InlineKeyboardButton("📄 As Resource", callback_data="fb_confirm_resources")],
            [InlineKeyboardButton("✏️ Rename", callback_data="fb_ask_rename")]
        ])
    )

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def manual_confirm(bot, query: CallbackQuery):
    u_type = query.data.split("_")[2]
    user_id = query.from_user.id
    data = user_session[user_id]["temp"]
    await push_to_firebase(bot, query.message, user_id, data["name"], data["link"], u_type)

async def push_to_firebase(bot, message, user_id, name, link, u_type):
    sess = user_session[user_id]
    cat, batch, mod = sess["cat"], sess["batch"], sess["mod"]
    
    # Determine Base Path
    if sess["is_sub"]:
        sub_mod = sess["sub_mod"]
        # Path: modules -> mod -> subModules -> subMod -> type (lectures/resources)
        db_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules").child(sub_mod).child(u_type)
        loc_text = f"Sub-Module ({u_type})"
    else:
        # Path: modules -> mod -> type
        db_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(u_type)
        loc_text = f"Main Module ({u_type})"

    # Data Payload
    ts = int(time.time() * 1000) # Order by timestamp
    payload = {
        "name": name,
        "link": link,
        "order": ts
    }
    
    # Add extra 'type' field for resources (PDFs)
    if u_type == "resources":
        payload["type"] = "pdf" 

    try:
        ref = db_path.push(payload)
        key = ref['name']
        # Update ID inside the object
        db_path.child(key).update({"id": key})
        
        if isinstance(message, Message):
            await message.reply_text(f"✅ **Uploaded to {loc_text}**\n📂 `{name}`")
        else:
            await message.edit_text(f"✅ **Uploaded to {loc_text}**\n📂 `{name}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Upload More", callback_data="fb_back_dash")]]))
            
    except Exception as e:
        err_text = f"❌ Error: {e}"
        if isinstance(message, Message): await message.reply(err_text)
        else: await message.edit_text(err_text)

# --- 8. Creation & Renaming Logic ---

@Client.on_callback_query(filters.regex("^fb_ask_rename"))
async def ask_rename(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "awaiting_rename"
    await query.message.edit_text("✏️ Send new name:")

@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def ask_create_mod(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "awaiting_create_mod"
    await query.message.edit_text("🆕 Send **Module Name**:")

@Client.on_callback_query(filters.regex("^fb_create_sub_ask"))
async def ask_create_sub(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "awaiting_create_sub"
    await query.message.edit_text(f"🆕 Send **Sub-Module Name** for `{user_session[query.from_user.id]['mod']}`:")

@Client.on_callback_query(filters.regex("^fb_back_dash"))
async def back_to_dash(bot, query: CallbackQuery):
    user_id = query.from_user.id
    target = "Sub-Module" if user_session[user_id]["is_sub"] else "Main Module"
    await refresh_dashboard(bot, query.message, user_id, target)

@Client.on_message(filters.text & filters.user(ADMINS))
async def text_handler(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state")
    text = message.text.strip()
    
    # Rename File
    if state == "awaiting_rename":
        user_session[user_id]["temp"]["name"] = text
        user_session[user_id]["state"] = "active"
        await message.reply_text(f"✅ Renamed to: `{text}`", 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 As Lecture", callback_data="fb_confirm_lectures")],
                [InlineKeyboardButton("📄 As Resource", callback_data="fb_confirm_resources")]
            ]))

    # Create Module
    elif state == "awaiting_create_mod":
        cat, batch = user_session[user_id]["cat"], user_session[user_id]["batch"]
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ts = int(time.time() * 1000)
        ref = path.push({"name": text, "order": ts})
        path.child(ref['name']).update({"id": ref['name']})
        
        await message.reply_text(f"✅ Module `{text}` created!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Batch", callback_data=f"fb_sel_batch_{batch}")]]))
        user_session[user_id]["state"] = "idle"

    # Create Sub-Module
    elif state == "awaiting_create_sub":
        cat, batch, mod = user_session[user_id]["cat"], user_session[user_id]["batch"], user_session[user_id]["mod"]
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules")
        ts = int(time.time() * 1000)
        
        # Structure as per image: isSubModule: true
        ref = path.push({"name": text, "order": ts, "isSubModule": True})
        path.child(ref['name']).update({"id": ref['name']})
        
        await message.reply_text(f"✅ Sub-Module `{text}` created!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Module", callback_data=f"fb_mod_menu_{mod}")]]))
        user_session[user_id]["state"] = "idle"
