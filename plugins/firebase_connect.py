import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import pyrebase
from info import *  # Ensure ADMINS, LOG_CHANNEL, STREAM_URL are here

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

# --- Session Management ---
user_session = {}

# --- Helper Functions ---

async def get_stream_link(message: Message):
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        
        file_type = "file"
        if message.video:
            file_name = message.video.file_name or f"Video {log_msg.id}.mp4"
            file_type = "video"
        elif message.document:
            file_name = message.document.file_name or f"File {log_msg.id}.pdf"
            file_type = "pdf"
        else:
            file_name = f"File {log_msg.id}"
            
        name_without_ext = os.path.splitext(file_name)[0]
        clean_name = name_without_ext.replace("_", " ")
        
        safe_filename = urllib.parse.quote_plus(file_name)
        stream_link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_filename}"
        
        return stream_link, clean_name, log_msg.id, file_type
    except Exception as e:
        print(f"Error: {e}")
        return None, None, None, None

def get_name(data):
    if not data: return "Unnamed"
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or "Unnamed"
    return "Unnamed"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def firebase_panel(bot, message):
    user_id = message.from_user.id
    user_session[user_id] = {
        "state": "idle",
        "fast_mode": False,
        "is_sub_module": False,
        "sub_mod_id": None,
        "cat_id": None, 
        "batch_id": None, 
        "module_id": None
    }
    
    await message.reply_text(
        "**🔥 Firebase Admin Panel**\n\nDatabase Connected!\nSelect Category:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📂 Select Category", callback_data="fb_cat_list")]])
    )

# --- Navigation ---

@Client.on_callback_query(filters.regex("^fb_cat_list"))
async def list_categories(bot, query: CallbackQuery):
    try:
        cats = db.child("categories").get().val()
        buttons = []
        if cats:
            for k, v in (cats.items() if isinstance(cats, dict) else enumerate(cats)):
                if v: buttons.append([InlineKeyboardButton(f"📂 {get_name(v)}", callback_data=f"fb_sel_cat_{k}")])
        await query.message.edit_text("**📂 Select Category:**", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def list_batches(bot, query: CallbackQuery):
    cat_id = query.data.split("_")[3]
    user_session[query.from_user.id]["cat_id"] = cat_id
    try:
        batches = db.child("categories").child(cat_id).child("batches").get().val()
        buttons = []
        if batches:
            for k, v in (batches.items() if isinstance(batches, dict) else enumerate(batches)):
                if v: buttons.append([InlineKeyboardButton(f"🎓 {get_name(v)}", callback_data=f"fb_sel_batch_{k}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_cat_list")])
        await query.message.edit_text(f"**📂 Cat:** `{cat_id}`\nSelect Batch:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def list_modules(bot, query: CallbackQuery):
    batch_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["batch_id"] = batch_id
    cat = user_session[user_id]["cat_id"]
    
    try:
        # Fetch Modules
        modules = db.child("categories").child(cat).child("batches").child(batch_id).child("modules").get().val()
        buttons = []
        if modules:
            for k, v in (modules.items() if isinstance(modules, dict) else enumerate(modules)):
                if v: buttons.append([InlineKeyboardButton(f"📺 {get_name(v)}", callback_data=f"fb_mod_menu_{k}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_create_mod")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cat}")])
        await query.message.edit_text(f"**🎓 Batch:** `{batch_id}`\nSelect Module:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# --- Module & Sub-Module Logic (UPDATED FOR IMAGE STRUCTURE) ---

@Client.on_callback_query(filters.regex("^fb_mod_menu_"))
async def module_menu_handler(bot, query: CallbackQuery):
    module_id = query.data.split("_")[3]
    user_id = query.from_user.id
    user_session[user_id]["module_id"] = module_id
    user_session[user_id]["is_sub_module"] = False
    user_session[user_id]["sub_mod_id"] = None

    buttons = [
        [InlineKeyboardButton("✅ Upload to Main Module", callback_data=f"fb_set_final_main")],
        [InlineKeyboardButton("📂 Open Sub-Modules", callback_data=f"fb_list_submod_{module_id}")],
        [InlineKeyboardButton("➕ Create Sub-Module", callback_data=f"fb_create_submod_ask")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_batch_{user_session[user_id]['batch_id']}")]
    ]
    await query.message.edit_text(f"**📺 Module:** `{module_id}`\nChoose Action:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_list_submod_"))
async def list_sub_modules(bot, query: CallbackQuery):
    mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]

    try:
        # IMAGE LOGIC: Submodules are inside 'lectures' key but have isSubModule=True
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod_id).child("lectures")
        data = path.get().val()
        
        buttons = []
        if data and isinstance(data, dict):
            for key, val in data.items():
                # Filter: Only show items that are actually SubModules
                if val.get("isSubModule") is True:
                    buttons.append([InlineKeyboardButton(f"📑 {get_name(val)}", callback_data=f"fb_set_submod_{key}")])
        
        buttons.append([InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_create_submod_ask")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_mod_menu_{mod_id}")])
        
        await query.message.edit_text("**📂 Sub-Modules List**\n(Filtered from Lectures)", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# --- Set Target ---

@Client.on_callback_query(filters.regex("^fb_set_final_main"))
async def set_main_module_active(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["is_sub_module"] = False
    user_session[user_id]["sub_mod_id"] = None
    await show_dashboard(bot, query, "Main Module")

@Client.on_callback_query(filters.regex("^fb_set_submod_"))
async def set_sub_module_active(bot, query: CallbackQuery):
    sub_mod_id = query.data.split("_")[3]
    user_id = query.from_user.id
    
    user_session[user_id]["is_sub_module"] = True
    user_session[user_id]["sub_mod_id"] = sub_mod_id
    
    await show_dashboard(bot, query, "Sub-Module")

async def show_dashboard(bot, query, type_name):
    user_id = query.from_user.id
    user_session[user_id]["state"] = "active_firebase"
    
    mod = user_session[user_id]["module_id"]
    sub = user_session[user_id].get("sub_mod_id", "None")
    
    is_fast = user_session[user_id].get("fast_mode", False)
    fast_status = "🟢 ON" if is_fast else "🔴 OFF"

    text = f"✅ **Target: {type_name}**\n📺 Module: `{mod}`\n"
    if user_session[user_id]["is_sub_module"]:
        text += f"📑 Sub-Module: `{sub}`\n"
    
    text += f"\n⚡ Fast Mode: {fast_status}\n⬇️ **Send Video/File Now!**"
    
    buttons = [
        [InlineKeyboardButton(f"⚡ Toggle Fast Mode", callback_data="fb_toggle_fast")],
        [InlineKeyboardButton("👀 Show Content (Del)", callback_data="fb_manage_idx")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"fb_mod_menu_{mod}")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# --- Fast Mode ---

@Client.on_callback_query(filters.regex("^fb_toggle_fast"))
async def toggle_fast_mode(bot, query: CallbackQuery):
    user_id = query.from_user.id
    if not user_session[user_id].get("fast_mode"):
        buttons = [[InlineKeyboardButton("🎬 Lectures", callback_data="fb_set_fast_lec"), InlineKeyboardButton("📄 Resources", callback_data="fb_set_fast_res")]]
        await query.message.edit_text("**⚡ Fast Mode: Auto Upload to?**", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        user_session[user_id]["fast_mode"] = False
        type_n = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
        await show_dashboard(bot, query, type_n)

@Client.on_callback_query(filters.regex("^fb_set_fast_"))
async def set_fast_type(bot, query: CallbackQuery):
    user_id = query.from_user.id
    user_session[user_id]["fast_mode"] = True
    user_session[user_id]["default_type"] = query.data.split("_")[3]
    await query.answer("⚡ Fast Mode ON")
    type_n = "Sub-Module" if user_session[user_id]["is_sub_module"] else "Main Module"
    await show_dashboard(bot, query, type_n)

# --- Upload Handler (CORRECTED PATH LOGIC) ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def incoming_file_handler(bot, message):
    user_id = message.from_user.id
    if user_session.get(user_id, {}).get("state") != "active_firebase": return

    msg = await message.reply("🔄 Processing...")
    link, name, _, ftype = await get_stream_link(message)
    if not link: return await msg.edit("❌ Error.")

    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    # --- PATH LOGIC BASED ON YOUR IMAGE ---
    if user_session[user_id]["is_sub_module"]:
        sub_mod = user_session[user_id]["sub_mod_id"]
        # Path: modules -> {mod} -> lectures -> {subMod}
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(sub_mod)
        loc_txt = "Sub-Module"
    else:
        # Path: modules -> {mod}
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
        loc_txt = "Main Module"

    def push_data(folder, fname, flink):
        ts = int(time.time() * 1000)
        data = {"name": fname, "link": flink, "order": ts}
        
        # Add type for resources (from image: type="pdf")
        if folder == "resources":
            data["type"] = "pdf" if ftype == "pdf" else "file"
            
        # Push to 'lectures' or 'resources' folder INSIDE the SubModule
        ref = base_path.child(folder).push(data)
        base_path.child(folder).child(ref['name']).update({"id": ref['name']})
        return ref['name']

    # Fast Mode
    if user_session[user_id].get("fast_mode"):
        ft = user_session[user_id]["default_type"] # lec or res
        target = "lectures" if ft == "lec" else "resources"
        push_data(target, name, link)
        await msg.edit(f"⚡ **Added to {loc_txt} ({target})**\n`{name}`")
        return

    # Normal Mode
    user_session[user_id]["temp_data"] = {"title": name, "url": link, "ftype": ftype}
    buttons = [
        [InlineKeyboardButton("✅ Add", callback_data="fb_name_keep"), InlineKeyboardButton("✏️ Rename", callback_data="fb_name_rename")], 
        [InlineKeyboardButton("❌ Cancel", callback_data="fb_cancel_up")]
    ]
    await msg.edit(f"📂 **File:** `{name}`\nAdd to **{loc_txt}**?", reply_markup=InlineKeyboardMarkup(buttons))

# --- Creation & Rename ---

@Client.on_message(filters.text & filters.user(ADMINS))
async def handle_text(bot, message):
    user_id = message.from_user.id
    if user_id not in user_session: return
    state = user_session[user_id].get("state", "")
    
    if state == "waiting_for_name":
        user_session[user_id]["temp_data"]["title"] = message.text.strip()
        user_session[user_id]["state"] = "active_firebase"
        await ask_file_type(message, user_session[user_id]["temp_data"]["title"])

    elif state == "waiting_mod_creation":
        ts = int(time.time() * 1000)
        path = db.child("categories").child(user_session[user_id]["cat_id"]).child("batches").child(user_session[user_id]["batch_id"]).child("modules")
        ref = path.push({"name": message.text.strip(), "order": ts})
        path.child(ref['name']).update({"id": ref['name']})
        await message.reply("✅ Module Created.")
        user_session[user_id]["state"] = "idle"

    elif state == "waiting_submod_creation":
        ts = int(time.time() * 1000)
        cat = user_session[user_id]["cat_id"]
        batch = user_session[user_id]["batch_id"]
        mod = user_session[user_id]["module_id"]
        
        # IMAGE STRUCTURE: Create submodule inside 'lectures' folder of the module
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures")
        
        data = {
            "name": message.text.strip(),
            "order": ts,
            "isSubModule": True # Key flag for your structure
        }
        ref = path.push(data)
        path.child(ref['name']).update({"id": ref['name']})
        await message.reply(f"✅ Sub-Module Created (in lectures folder).\nName: {message.text.strip()}")
        user_session[user_id]["state"] = "idle"

# --- Callbacks ---

@Client.on_callback_query(filters.regex("^fb_name_keep"))
async def keep_name(bot, query: CallbackQuery):
    await ask_file_type(query.message, user_session[query.from_user.id]["temp_data"]["title"])

@Client.on_callback_query(filters.regex("^fb_name_rename"))
async def rename_ask(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_for_name"
    await query.message.edit_text("✏️ New Name:")

@Client.on_callback_query(filters.regex("^fb_cancel_up"))
async def cancel_u(bot, query: CallbackQuery):
    await query.message.delete()

async def ask_file_type(message, title):
    buttons = [[InlineKeyboardButton("🎬 Lecture", callback_data="fb_confirm_lec"), InlineKeyboardButton("📄 Resource", callback_data="fb_confirm_res")]]
    msg_func = message.reply_text if isinstance(message, Message) else message.edit_text
    await msg_func(f"📌 **Confirm:**\n`{title}`\nSelect Type:", reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("^fb_confirm_"))
async def final_push(bot, query: CallbackQuery):
    action = query.data.split("_")[2]
    user_id = query.from_user.id
    data = user_session[user_id]["temp_data"]
    
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    folder = "lectures" if action == "lec" else "resources"

    if user_session[user_id]["is_sub_module"]:
        sub = user_session[user_id]["sub_mod_id"]
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(sub).child(folder)
    else:
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(folder)

    ts = int(time.time() * 1000)
    entry = {"name": data["title"], "link": data["url"], "order": ts}
    if folder == "resources":
        entry["type"] = "pdf" if data.get("ftype") == "pdf" else "file"

    try:
        ref = path.push(entry)
        path.child(ref['name']).update({"id": ref['name']})
        await query.message.edit_text("✅ Saved!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=f"fb_mod_menu_{mod}")]]))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_create_mod"))
async def trig_mod(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_mod_creation"
    await query.message.edit_text("Enter Module Name:")

@Client.on_callback_query(filters.regex("^fb_create_submod_ask"))
async def trig_sub(bot, query: CallbackQuery):
    user_session[query.from_user.id]["state"] = "waiting_submod_creation"
    await query.message.edit_text("Enter Sub-Module Name:")

# --- View/Delete Content (Updated to show Lectures AND Resources) ---

@Client.on_callback_query(filters.regex("^fb_manage_idx"))
async def manage_content_list(bot, query: CallbackQuery):
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    # Path selection
    if user_session[user_id]["is_sub_module"]:
        sub = user_session[user_id]["sub_mod_id"]
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(sub)
        type_n = "Sub-Module"
    else:
        base_path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod)
        type_n = "Main Module"

    try:
        buttons = []
        # Fetch Lectures
        lecs = base_path.child("lectures").get().val()
        if lecs:
            buttons.append([InlineKeyboardButton("➖➖ Lectures ➖➖", callback_data="ignore")])
            for k, v in lecs.items():
                buttons.append([InlineKeyboardButton(f"🎬 {get_name(v)}", callback_data=f"fb_del_lec_{k}")])
        
        # Fetch Resources (Added this part so you can see resources too)
        ress = base_path.child("resources").get().val()
        if ress:
            buttons.append([InlineKeyboardButton("➖➖ Resources ➖➖", callback_data="ignore")])
            for k, v in ress.items():
                buttons.append([InlineKeyboardButton(f"📄 {get_name(v)}", callback_data=f"fb_del_res_{k}")])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="fb_back_dash")])
        await query.message.edit_text(f"**📂 Content in {type_n}:**\n(Click to Delete)", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_del_"))
async def delete_item(bot, query: CallbackQuery):
    data = query.data.split("_")
    itype = data[2] # lec or res
    key = data[3]
    
    user_id = query.from_user.id
    cat = user_session[user_id]["cat_id"]
    batch = user_session[user_id]["batch_id"]
    mod = user_session[user_id]["module_id"]
    
    folder = "lectures" if itype == "lec" else "resources"

    if user_session[user_id]["is_sub_module"]:
        sub = user_session[user_id]["sub_mod_id"]
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child("lectures").child(sub).child(folder)
    else:
        path = db.child("categories").child(cat).child("batches").child(batch).child("modules").child(mod).child(folder)
    
    path.child(key).remove()
    await query.answer("🗑 Deleted!", show_alert=True)
    await manage_content_list(bot, query) # Refresh list

@Client.on_callback_query(filters.regex("^fb_back_dash"))
async def back_dash(bot, query: CallbackQuery):
    t = "Sub-Module" if user_session[query.from_user.id]["is_sub_module"] else "Main Module"
    await show_dashboard(bot, query, t)
