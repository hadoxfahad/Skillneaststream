import asyncio
import os
import urllib.parse
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import pyrebase
from info import *  # Ensure ADMINS, LOG_CHANNEL, STREAM_URL are defined

# --- Firebase Config ---
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

# --- Session ---
user_session = {}

# --- Helpers ---

async def get_stream_link(message: Message):
    try:
        log_msg = await message.forward(LOG_CHANNEL)
        fname = "Unknown"
        ftype = "file"
        
        if message.video:
            fname = message.video.file_name or f"Video {log_msg.id}.mp4"
            ftype = "video"
        elif message.document:
            fname = message.document.file_name or f"File {log_msg.id}.pdf"
            ftype = "pdf"
            
        safe_name = urllib.parse.quote_plus(fname)
        link = f"{STREAM_URL}/dl/{log_msg.id}/{safe_name}"
        clean_name = os.path.splitext(fname)[0].replace("_", " ")
        return link, clean_name, ftype
    except:
        return None, None, None

def get_name(data):
    if isinstance(data, dict):
        return data.get("name") or data.get("title") or "Unnamed"
    return "Unnamed"

# --- Main Command ---

@Client.on_message(filters.command("firebase") & filters.user(ADMINS))
async def start_panel(bot, message):
    uid = message.from_user.id
    user_session[uid] = {"state": "idle", "path": {}}
    
    await message.reply_text(
        "**🔥 Firebase Manager**\nSelect Category:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📂 Load Categories", callback_data="fb_list_cats")]])
    )

# --- Navigation Handlers ---

@Client.on_callback_query(filters.regex("^fb_list_cats"))
async def show_cats(bot, query: CallbackQuery):
    try:
        data = db.child("categories").get().val()
        btns = []
        if data:
            # Handle both list and dict from Firebase
            items = data.items() if isinstance(data, dict) else enumerate(data)
            for k, v in items:
                if v: btns.append([InlineKeyboardButton(f"📂 {get_name(v)}", callback_data=f"fb_sel_cat_{k}")])
        
        await query.message.edit_text("**Select Category:**", reply_markup=InlineKeyboardMarkup(btns))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_sel_cat_"))
async def show_batches(bot, query: CallbackQuery):
    cid = query.data.split("_")[3]
    user_session[query.from_user.id]["path"]["cat"] = cid
    
    try:
        data = db.child("categories").child(cid).child("batches").get().val()
        btns = []
        if data:
            items = data.items() if isinstance(data, dict) else enumerate(data)
            for k, v in items:
                if v: btns.append([InlineKeyboardButton(f"🎓 {get_name(v)}", callback_data=f"fb_sel_batch_{k}")])
        
        btns.append([InlineKeyboardButton("🔙 Back", callback_data="fb_list_cats")])
        await query.message.edit_text("**Select Batch:**", reply_markup=InlineKeyboardMarkup(btns))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_sel_batch_"))
async def show_modules(bot, query: CallbackQuery):
    bid = query.data.split("_")[3]
    user_session[query.from_user.id]["path"]["batch"] = bid
    cid = user_session[query.from_user.id]["path"]["cat"]
    
    try:
        data = db.child("categories").child(cid).child("batches").child(bid).child("modules").get().val()
        btns = []
        if data:
            items = data.items() if isinstance(data, dict) else enumerate(data)
            for k, v in items:
                if v: btns.append([InlineKeyboardButton(f"📺 {get_name(v)}", callback_data=f"fb_mod_opt_{k}")])
        
        btns.append([InlineKeyboardButton("➕ Create Module", callback_data="fb_mk_mod")])
        btns.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_cat_{cid}")])
        await query.message.edit_text("**Select Module:**", reply_markup=InlineKeyboardMarkup(btns))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

# --- Module vs SubModule Logic ---

@Client.on_callback_query(filters.regex("^fb_mod_opt_"))
async def module_options(bot, query: CallbackQuery):
    mid = query.data.split("_")[3]
    uid = query.from_user.id
    user_session[uid]["path"]["module"] = mid
    user_session[uid]["is_sub"] = False # Reset
    user_session[uid]["sub_id"] = None
    
    btns = [
        [InlineKeyboardButton("✅ Add Content Here", callback_data="fb_set_main")],
        [InlineKeyboardButton("📂 Open Sub-Modules", callback_data=f"fb_list_subs_{mid}")],
        [InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_mk_sub")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"fb_sel_batch_{user_session[uid]['path']['batch']}")]
    ]
    await query.message.edit_text(f"**Module Selected:** `{mid}`\nWhat to do?", reply_markup=InlineKeyboardMarkup(btns))

@Client.on_callback_query(filters.regex("^fb_list_subs_"))
async def list_submodules(bot, query: CallbackQuery):
    mid = query.data.split("_")[3]
    uid = query.from_user.id
    path_d = user_session[uid]["path"]
    
    try:
        # Looking inside 'lectures' folder for items with isSubModule: true
        base = db.child("categories").child(path_d["cat"]).child("batches").child(path_d["batch"]).child("modules").child(mid).child("lectures")
        data = base.get().val()
        
        btns = []
        if data and isinstance(data, dict):
            for k, v in data.items():
                if v.get("isSubModule") is True:
                     btns.append([InlineKeyboardButton(f"📑 {get_name(v)}", callback_data=f"fb_sel_sub_{k}")])
        
        btns.append([InlineKeyboardButton("➕ Create Sub-Module", callback_data="fb_mk_sub")])
        btns.append([InlineKeyboardButton("🔙 Back", callback_data=f"fb_mod_opt_{mid}")])
        await query.message.edit_text("**Sub-Modules List:**", reply_markup=InlineKeyboardMarkup(btns))
    except Exception as e:
        await query.message.edit_text(f"Error: {e}")

@Client.on_callback_query(filters.regex("^fb_set_main"))
async def set_main_target(bot, query: CallbackQuery):
    uid = query.from_user.id
    user_session[uid]["is_sub"] = False
    await show_dashboard(bot, query, "Main Module")

@Client.on_callback_query(filters.regex("^fb_sel_sub_"))
async def set_sub_target(bot, query: CallbackQuery):
    sid = query.data.split("_")[3]
    uid = query.from_user.id
    user_session[uid]["is_sub"] = True
    user_session[uid]["sub_id"] = sid
    await show_dashboard(bot, query, "Sub-Module")

async def show_dashboard(bot, query, label):
    uid = query.from_user.id
    user_session[uid]["state"] = "active"
    mid = user_session[uid]["path"]["module"]
    
    txt = f"✅ **Active Target:** `{label}`\n"
    if user_session[uid]["is_sub"]:
        txt += f"📑 Sub-ID: `{user_session[uid]['sub_id']}`"
    
    btns = [[InlineKeyboardButton("🔙 Back to Menu", callback_data=f"fb_mod_opt_{mid}")]]
    await query.message.edit_text(f"{txt}\n\n⬇️ **Send File/Video Now!**", reply_markup=InlineKeyboardMarkup(btns))

# --- Content Upload (The Fix) ---

@Client.on_message((filters.video | filters.document) & filters.user(ADMINS))
async def handle_upload(bot, message):
    uid = message.from_user.id
    if user_session.get(uid, {}).get("state") != "active": return
    
    link, name, ftype = await get_stream_link(message)
    if not link: return await message.reply("❌ Error getting link.")
    
    status = await message.reply(f"⬆️ Uploading: `{name}`...")
    
    p = user_session[uid]["path"]
    is_sub = user_session[uid]["is_sub"]
    
    # --- PATH CONSTRUCTION (Critical) ---
    base = db.child("categories").child(p["cat"]).child("batches").child(p["batch"]).child("modules").child(p["module"])
    
    if is_sub:
        # Path: modules -> {id} -> lectures -> {sub_id}
        target_base = base.child("lectures").child(user_session[uid]["sub_id"])
    else:
        # Path: modules -> {id}
        target_base = base
        
    # Decide folder: 'lectures' or 'resources'
    folder = "lectures" if ftype == "video" else "resources"
    
    ts = int(time.time() * 1000)
    payload = {
        "name": name,
        "link": link,
        "order": ts
    }
    if folder == "resources":
        payload["type"] = "pdf" if ftype == "pdf" else "file"
        
    try:
        # 1. Push data
        ref = target_base.child(folder).push(payload)
        key = ref['name']
        
        # 2. UPDATE ID IMMEDIATELY (Fixes undefined issue)
        target_base.child(folder).child(key).update({"id": key})
        
        await status.edit(f"✅ **Saved!**\n📂 Path: {folder}\n📝 Name: {name}")
    except Exception as e:
        await status.edit(f"❌ Error: {e}")

# --- Creations (Modules/SubModules) ---

@Client.on_callback_query(filters.regex("^fb_mk_"))
async def ask_create_name(bot, query: CallbackQuery):
    mode = query.data.split("_")[2] # mod or sub
    user_session[query.from_user.id]["create_mode"] = mode
    user_session[query.from_user.id]["state"] = "waiting_name"
    await query.message.edit_text("✏️ **Enter Name:**")

@Client.on_message(filters.text & filters.user(ADMINS))
async def create_item(bot, message):
    uid = message.from_user.id
    if user_session.get(uid, {}).get("state") != "waiting_name": return
    
    name = message.text.strip()
    mode = user_session[uid]["create_mode"]
    p = user_session[uid]["path"]
    ts = int(time.time() * 1000)
    
    try:
        if mode == "mod":
            # Create Module
            path = db.child("categories").child(p["cat"]).child("batches").child(p["batch"]).child("modules")
            data = {"name": name, "order": ts}
            ref = path.push(data)
            path.child(ref['name']).update({"id": ref['name']})
            await message.reply(f"✅ Module **{name}** Created!")
            
        elif mode == "sub":
            # Create SubModule (Inside 'lectures' folder with flag)
            mid = p["module"]
            path = db.child("categories").child(p["cat"]).child("batches").child(p["batch"]).child("modules").child(mid).child("lectures")
            data = {
                "name": name,
                "order": ts,
                "isSubModule": True
            }
            ref = path.push(data)
            path.child(ref['name']).update({"id": ref['name']})
            await message.reply(f"✅ Sub-Module **{name}** Created!")
            
        user_session[uid]["state"] = "idle"
        
    except Exception as e:
        await message.reply(f"Error: {e}")
