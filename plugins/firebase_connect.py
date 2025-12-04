import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters, enums
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
    """Generates Direct Link & Cleans Filename"""
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        
        if message.video:
            file_name = message.video.file_name or f"Video {log_msg.id}.mp4"
        elif message.document:
            file_name = message.document.file_name or f"File {log_msg.id}.pdf"
        else:
            file_name = f"File {log_msg.id}"
            
        # Clean Name
        name_without_ext = os.path.splitext(file_name)[0]
        clean_name = name_without_ext.replace("_", " ")
        
        # Safe URL
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name, log_msg.id
    except Exception as e:
        print(f"Error generating link: {e}")
        return None, None, None

def get_name(data):
    if not data: return "Unnamed"
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or data.get("description") or "Unnamed"
    return "Unnamed"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    # Reset Session
    user_session[user_id] = {"state": "idle", "fast_mode": False}
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!\nSelect a Category to start:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")],
            [InlineKeyboardButton("⚙️ Switch Input Mode", callback_data="fb_mode_menu")]
        ])
    )

# --- Navigation ---

# 1. Categories
@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        cats_data = db.child("categories").get().val()
        buttons = []
        
        if cats_data:
            if isinstance(cats_data, dict):
                for key, val in cats_data.items():
                    c_name = get_name(val)
                    buttons.append([InlineKeyboardButton(f"📂 {c_name}", callback_data=f"fb_sel_cat_{key}")])
            elif isinstance(cats_data, list):
                for i, val in enumerate(cats_data):
                    if val:
                        c_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"📂 {c_name}", callback_data=f"fb_sel_cat_{i}")])
        
        await query.message.edit_text("**📂 Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error fetching categories: {e}")

# 2. Batches
@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["cat_id"] = cat_id
    user_session[user_id].pop("batch_id", None) # Clear forward history
    
    try:
        batches_data = db.child("categories").child(cat_id).child("batches").get().val()
        buttons = []
        
        if batches_data:
            if isinstance(batches_data, dict):
                for key, val in batches_data.items():
                    if isinstance(val, dict):
                        b_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"🎓 {b_name}", callback_data=f"fb_sel_batch_{key}")])
            elif isinstance(batches_data, list):
                for i, val in enumerate(batches_data):
                    if val and isinstance(val, dict):
                        b_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"🎓 {b_name}", callback_data=f"fb_sel_batch_{i}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**📂 Category ID:** `{cat_id}`\n\nSelect a **Batch**:", reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        await query.message.edit_text(f"❌ Error loading batches: {e}")

# 3. Modules List
@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    cat_id = user_session[user_id].get("cat_id")
    user_session[user_id]["batch_id"] = batch_id
    user_session[user_id].pop("module_id", None) # Clear forward history
    
    try:
        modules_data = db.child("categories").child(cat_id).child("batches").child(batch_id).child("modules").get().val()
        buttons = []
        
        if modules_data:
            if isinstance(modules_data, dict):
                for key, val in modules_data.items():
                    if isinstance(val, dict):
                        m_name = get_name(val)
                        # Instead of setting directly, we open Module Menu
                        buttons.append([InlineKeyboardButton(f"📺 {m_name}", callback_data=f"fb_mod_menu_{key}")])
            elif isinstance(modules_data, list):
                for i, val in enumerate(modules_data):
                    if val and isinstance(val, dict):
                        m_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"📺 {m_name}", callback_data=f"fb_mod_menu_{i}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat_id}")])
        
        await query.message.edit_text(f"**🎓 Batch:** `{batch_id}`\n\nSelect a **Module**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
         await query.message.edit_text(f"Error: {e}")

# --- 4. Module Menu (Logic Changed for Sub Modules) ---
@Client.on_callback_query(filters.regex("^fb_mod_menu_"))
async def module_menu_options(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["module_id"] = module_id
    # Reset sub module
    user_session[user_id].pop("sub_module_id", None)

    buttons = [
        [InlineKeyboardButton("📂 View Sub-Modules", callback_data=f"fb_list_sub_{module_id}")],
        [InlineKeyboardButton("⬆️ Upload Files Here (Main)", callback_data=f"fb_set_target_main_{module_id}")],
        [InlineKeyboardButton("🔙 Back to Modules", callback_data=f"fb_sel_batch_{user_session[user_id]['batch_id']}")]
    ]
    await query.message.edit_text(f"**📺 Module Selected:** `{module_id}`\n\nKya karna chahte ho?", reply_markup=InlineKeyboardMarkup(buttons))

# --- 5. Sub Modules List ---
@Client.on_callback_query(filters.regex("^fb_list_sub_"))
async def list_sub_modules(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    
    try:
        # Fetching Submodules
        sub_data = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(module_id).child("subModules").get().val()
        buttons = []
        
        if sub_data:
            if isinstance(sub_data, dict):
                for key, val in sub_data.items():
                    if isinstance(val, dict):
                        s_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"🔹 {s_name}", callback_data=f"fb_set_sub_{key}")])
            elif isinstance(sub_data, list):
                for i, val in enumerate(sub_data):
                    if val and isinstance(val, dict):
                        s_name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"🔹 {s_name}", callback_data=f"fb_set_sub_{i}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_create_submod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_mod_menu_{module_id}")])
        
        await query.message.edit_text(f"**📂 Sub-Modules inside:** `{module_id}`", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error loading submodules: {e}")

# --- 6. Set Active Target (Main Module or Sub Module) ---

# Target: Main Module
@Client.on_callback_query(filters.regex("^fb_set_target_main_"))
async def set_main_module_active(bot, query: CallbackQuery):
    mod_id = query.data.split("_")[4]
    user_id = query.from_user.id
    user_session[user_id]["module_id"] = mod_id
    user_session[user_id]["sub_module_id"] = None # Ensure no sub module is set
    await show_upload_dashboard(bot, query.message, user_id, f"Module: {mod_id}")

# Target: Sub Module
@Client.on_callback_query(filters.regex("^fb_set_sub_"))
async def set_sub_module_active(bot, query: CallbackQuery):
    sub_mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["sub_module_id"] = sub_mod_id
    await show_upload_dashboard(bot, query.message, user_id, f"Sub-Module: {sub_mod_id}")

# Common Dashboard Function
async def show_upload_dashboard(bot, message, user_id, context_text):
    user_session[user_id]["state"] = "active_firebase"
    
    # Check Fast Mode
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"
    fast_text = "⚡ Disable Fast Mode" if is_fast else "⚡ Enable Fast Mode"
    
    buttons = [
        [InlineKeyboardButton("✏️ Manage Content (Edit/Del)", callback_data="fb_manage_curr")],
        [InlineKeyboardButton(fast_text, callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("❌ Stop Session", callback_data="fb_clear_session")]
    ]
    
    sub_text = f"\n🔹 **Sub-Module:** `{user_session[user_id].get('sub_module_id')}`" if user_session[user_id].get("sub_module_id") else ""

    await message.edit_text(
        f"✅ **Target Set!**\n"
        f"Ready to upload to: **{context_text}**\n\n"
        f"📂 **Category:** `{user_session[user_id]['cat_id']}`\n"
        f"🎓 **Batch:** `{user_session[user_id]['batch_id']}`\n"
        f"📺 **Module:** `{user_session[user_id]['module_id']}`"
        f"{sub_text}\n\n"
        f"⚡ **Fast Mode:** {fast_status}\n\n"
        f"⬇️ **Send Video/Files/URL Now:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# --- Feature: Fast Mode & Toggle ---
@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    current_status = user_session[user_id].get("fast_mode", False)
    
    if not current_status:
        buttons = [[InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"), InlineKeyboardButton("📄 Resources", callback_data="fb_set_fast_res")]]
        await query.message.edit_text("**⚡ Fast Mode Setup**\n\nDefault Type kya rakhein?", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        user_session[user_id]["fast_mode"] = False
        # Refill dashboard
        c_text = "Sub-Module" if user_session[user_id].get("sub_module_id") else "Module"
        await show_upload_dashboard(bot, query.message, user_id, c_text)

@Client.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(bot, query: CallbackQuery):
    user_id = query.from_user.id
    type_ = query.data.split("_")[3]
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = type_
    
    c_text = "Sub-Module" if user_session[user_id].get("sub_module_id") else "Module"
    await query.answer("⚡ Fast Mode Enabled!", show_alert=True)
    await show_upload_dashboard(bot, query.message, user_id, c_text)

# --- Feature: Manage Content (Unified) ---
@Client.on_callback_query(filters.regex("^fb_manage_curr"))
async def manage_content_list(bot, query: CallbackQuery):
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    sub_mod = user_session[user_id].get("sub_module_id")
    
    try:
        # Dynamic Path
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
        if sub_mod:
            path = path.child("subModules").child(sub_mod)
        
        # Combine lectures and resources for list or just lectures (simplified)
        lectures_data = path.child("lectures").get().val()
        
        buttons = []
        if lectures_data:
            if isinstance(lectures_data, dict):
                for key, val in lectures_data.items():
                    name = get_name(val)
                    buttons.append([InlineKeyboardButton(f"📝 {name}", callback_data=f"fb_item_opt_{key}")])
            elif isinstance(lectures_data, list):
                for i, val in enumerate(lectures_data):
                    if val:
                        name = get_name(val)
                        buttons.append([InlineKeyboardButton(f"📝 {name}", callback_data=f"fb_item_opt_{i}")])
        
        buttons.append([InlineKeyboardButton("🔙 Back to Upload", callback_data="fb_return_dash")])
        await query.message.edit_text(f"**🗑 Manage Content**\n\nClick item to **Edit** or **Delete**:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_return_dash"))
async def return_dash(bot, query: CallbackQuery):
    user_id = query.from_user.id
    c_text = "Sub-Module" if user_session[user_id].get("sub_module_id") else "Module"
    await show_upload_dashboard(bot, query.message, user_id, c_text)

@Client.on_callback_query(filters.regex("^fb_item_opt_"))
async def item_options(bot, query: CallbackQuery):
    key = query.data.split("_")[3]
    buttons = [
        [InlineKeyboardButton("🗑 Delete", callback_data=f"fb_del_{key}")],
        [InlineKeyboardButton("✏️ Rename", callback_data=f"fb_edit_ask_{key}")],
        [InlineKeyboardButton("🔙 Back", callback_data="fb_manage_curr")]
    ]
    await query.message.edit_text(f"**Item ID:** `{key}`", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_del_"))
async def delete_item(bot, query: CallbackQuery):
    key = query.data.split("_")[2]
    user_id = query.from_user.id
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    sub_mod = user_session[user_id].get("sub_module_id")
    
    path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
    if sub_mod: path = path.child("subModules").child(sub_mod)
    
    # Try deleting from lectures first
    path.child("lectures").child(key).remove()
    await query.answer("🗑 Deleted!", show_alert=True)
    
    # Refresh list
    query.data = "fb_manage_curr"
    await manage_content_list(bot, query)

@Client.on_callback_query(filters.regex("^fb_edit_ask_"))
async def edit_ask(bot, query: CallbackQuery):
    key = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["state"] = f"waiting_edit_{key}"
    await query.message.edit_text(f"✏️ **Send New Name** for this item:")

# --- Creation Logic (Modules & Sub-Modules) ---

@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def create_mod_trig(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("🆕 **Enter Name for New Module:**")

@Client.on_callback_query(filters.regex("^fb_create_submod"))
async def create_submod_trig(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_submod_creation"
    await query.message.edit_text("🆕 **Enter Name for New Sub-Module:**")

# --- Message Handlers (Files & Text) ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    
    # Generate Link
    stream_link, clean_name, log_id = await get_stream_link(message)
    if not stream_link: return await message.reply("Error generating link.")

    is_active = user_session.get(user_id, {}).get("state") == "active_firebase"
    
    if not is_active:
        text = f"✅ **Link Generated!**\n📄 `{clean_name}`\n🔗 `{stream_link}`"
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔥 Add to Firebase", callback_data="fb_cat_list")]]), disable_web_page_preview=True)
        return

    # Check Path
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    sub_mod = user_session[user_id].get("sub_module_id")
    
    # Base Path
    path_ref = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
    if sub_mod:
        path_ref = path_ref.child("subModules").child(sub_mod)
    
    # 1. Fast Mode Logic
    if user_session[user_id].get("fast_mode"):
        def_type = user_session[user_id]["default_type"]
        target = "lectures" if def_type == "lec" else "resources"
        ts = int(time.time() * 1000)
        
        entry = {"name": clean_name, "link": stream_link, "order": ts}
        ref = path_ref.child(target).push(entry)
        key = ref['name']
        path_ref.child(target).child(key).update({"id": key})
        
        dest = "Sub-Module" if sub_mod else "Module"
        await message.reply_text(f"⚡ **Fast Added to {dest}:**\n`{clean_name}`")
        return

    # 2. Normal Mode Logic
    user_session[user_id]["temp_data"] = {"title": clean_name, "url": stream_link}
    buttons = [[InlineKeyboardButton("✅ Add (Keep Name)", callback_data="fb_name_keep")], [InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")], [InlineKeyboardButton("❌ Cancel", callback_data="fb_clear_session")]]
    await message.reply_text(f"📂 **File Received:** `{clean_name}`\nRename or Keep?", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state", "")
    
    # Rename Content
    if state.startswith("waiting_edit_"):
        key = state.split("_")[2]
        new_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        sub_mod = user_session[user_id].get("sub_module_id")
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
        if sub_mod: path = path.child("subModules").child(sub_mod)
        
        path.child("lectures").child(key).update({"name": new_name})
        await message.reply_text(f"✅ Renamed to: {new_name}")
        user_session[user_id]["state"] = "active_firebase"
        await message.reply_text("Click Manage Content again to refresh.")

    # Create Module
    elif state == "waiting_mod_creation":
        mod_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        ts = int(time.time() * 1000)
        
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules")
        ref = path.push({"name": mod_name, "order": ts, "isSubModule": False})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"✅ Module Created: {mod_name}")
        user_session[user_id]["state"] = "idle"

    # Create Sub-Module
    elif state == "waiting_submod_creation":
        sub_name = message.text.strip()
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        ts = int(time.time() * 1000)
        
        # Save to subModules node
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("subModules")
        ref = path.push({"name": sub_name, "order": ts, "isSubModule": True})
        key = ref['name']
        path.child(key).update({"id": key})
        
        await message.reply_text(f"✅ Sub-Module Created: {sub_name}\nGo back and open Sub-modules list.")
        user_session[user_id]["state"] = "idle"

    # Rename File during upload
    elif state == "waiting_for_name":
        new_name = message.text.strip()
        user_session[user_id]["temp_data"]["title"] = new_name
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, new_name, user_session[user_id]["temp_data"]["url"], user_session[user_id])

    # URL Mode
    elif user_session[user_id].get("mode") == "url" and "module_id" in user_session[user_id]:
        await direct_url_logic(bot, message)

# --- Common Upload Logic ---
@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_default_name(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    await ask_file_type(query.message, data["title"], data["url"], user_session[user_id])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def ask_for_rename_manual(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ **New Name:**")

async def ask_file_type(message, title, url, session):
    buttons = [[InlineKeyboardButton("🎬 Lecture", callback_data="fb_confirm_lec"), InlineKeyboardButton("📄 Resource", callback_data="fb_confirm_res")]]
    await message.reply_text(f"📌 **Confirm Type:**\nName: `{title}`", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def push_firebase_manual(bot, query: CallbackQuery):
    action = query.data.split("_")[2]
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    sub_mod = user_session[user_id].get("sub_module_id")
    target = "lectures" if action == "lec" else "resources"
    ts = int(time.time() * 1000)
    
    path_ref = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
    if sub_mod: path_ref = path_ref.child("subModules").child(sub_mod)
    
    try:
        ref = path_ref.child(target).push({"name": data["title"], "link": data["url"], "order": ts})
        key = ref['name']
        path_ref.child(target).child(key).update({"id": key})
        
        await query.message.edit_text(f"✅ **Added Successfully!**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Upload More", callback_data="fb_return_dash")]]))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_clear_session"))
async def clear_s(bot, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id in user_session: del user_session[user_id]
    await query.message.edit_text("✅ Session Ended.")

# --- URL Logic & Mode Switch ---
@Client.on_callback_query(filters.regex("^fb_mode_menu"))
async def mode_menu(bot, query: CallbackQuery):
    await query.message.edit_text("Select Mode:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📂 File Mode", callback_data="fb_setmode_file"), InlineKeyboardButton("🔗 URL Mode", callback_data="fb_setmode_url")]]))

@Client.on_callback_query(filters.regex("^fb_setmode_"))
async def set_mode(bot, query: CallbackQuery):
    mode = query.data.split("_")[2]
    user_id = query.from_user.id
    if user_id not in user_session: user_session[user_id] = {}
    user_session[user_id]["mode"] = mode
    await query.answer(f"Mode Set: {mode}")

async def direct_url_logic(bot, message):
    user_id = message.from_user.id
    text = message.text.strip()
    if "|" in text: title, url = text.split("|", 1)
    else: title, url = "External Link", text
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    sub_mod = user_session[user_id].get("sub_module_id")
    ts = int(time.time() * 1000)
    
    path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
    if sub_mod: path = path.child("subModules").child(sub_mod)
    
    ref = path.child("lectures").push({"name": title.strip(), "link": url.strip(), "order": ts})
    key = ref['name']
    path.child("lectures").child(key).update({"id": key})
    
    dest = "Sub-Module" if sub_mod else "Module"
    await message.reply_text(f"✅ URL Added to {dest}: {title}")
