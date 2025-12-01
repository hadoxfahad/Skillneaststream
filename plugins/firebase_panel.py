import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from firebase_cfg import db, user_sessions
from info import URL, LOG_CHANNEL # Ensure info.py has your Website URL and Log Channel ID

# --- 1. Command to Start the Panel ---
@Client.on_message(filters.command("panel") & filters.private)
async def open_panel(bot, message):
    # Firebase se Categories fetch karega
    categories = db.child("categories").get()
    
    if not categories.val():
        await message.reply_text("❌ Database me koi Category nahi mili.")
        return

    buttons = []
    # Categories ke buttons banao
    for cat in categories.each():
        key = cat.key()
        val = cat.val()
        # Assuming category structure has 'name'
        cat_name = val.get("name", key)
        buttons.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"cat_{key}")])

    await message.reply_text(
        "**Select a Category:**\nJis category me lecture add karna hai use select karein.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

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
        
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_cat")]) # Logic needs cat_id persistence ideally

        await query.message.edit_text(
            f"**Selected Course ID:** `{course_id}`\n\nAb **Module** select karein jisme video daalni hai:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # -- Module Clicked -> Set Session --
    elif data.startswith("mod_"):
        _, mod_id, mod_name = data.split("_", 2)
        
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
        # Normal bot behavior (Just generate link, don't ask for DB)
        # Yahan return nahi kar rahe taaki normal functionality chalti rahe, 
        # bas "Add to Firebase" button tabhi dikhega jab module set ho.
        pass

    # File process karke Log Channel me forward karna (Standard Stream Bot Logic)
    try:
        # File ID generate (Assuming standard bot structure)
        file = message.video or message.document
        filename = file.file_name
        
        # Forward to Log Channel
        log_msg = await message.forward(LOG_CHANNEL)
        
        # Generate Stream Link (Using Info.py URL)
        # Pattern: https://site.com/watch/LogID/MsgID
        stream_link = f"{URL}/watch/{log_msg.id}" 
        download_link = f"{URL}/download/{log_msg.id}"
        
        text = f"**File Name:** `{filename}`\n\n" \
               f"🖥 **Stream:** {stream_link}\n" \
               f"📥 **Download:** {download_link}"
        
        buttons = []
        
        # Agar user ne Module set kiya hai, toh Firebase button dikhao
        if user_id in user_sessions:
            mod_name = user_sessions[user_id]['module_name']
            # Data pack kar rahe hain callback me: action|msg_id
            buttons.append([InlineKeyboardButton(f"➕ Add to {mod_name} (Lec)", callback_data=f"addfb_lec_{log_msg.id}")])
            buttons.append([InlineKeyboardButton(f"➕ Add to {mod_name} (Res)", callback_data=f"addfb_res_{log_msg.id}")])
        
        buttons.append([InlineKeyboardButton("Download Now", url=download_link)])
        
        await message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )
            
    except Exception as e:
        print(e)
        pass

# --- 5. Handle "Add to Firebase" Button Click ---
@Client.on_callback_query(filters.regex(r"^addfb_"))
async def add_to_firebase(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data.split("_") # addfb, type, log_id
    type_ = data[1] # lec or res
    log_id = data[2]
    
    if user_id not in user_sessions:
        await query.answer("❌ Module select nahi hai. /panel use karein.", show_alert=True)
        return
        
    session = user_sessions[user_id]
    module_id = session["module_id"]
    
    # Link regenerate kar rahe hain confirm karne ke liye
    stream_link = f"{URL}/watch/{log_id}"
    
    # Message se filename nikalna thoda tricky hai callback me, 
    # isliye hum default name use karenge ya user se input mangenge.
    # Abhi ke liye hum message text se nikalne ki koshish karte hain agar available ho.
    # Better approach: Just save URL, edit name later via website dashboard.
    
    # Let's try to get file name from the message attached to the button
    file_name = "New Lecture"
    if query.message.reply_to_message:
        media = query.message.reply_to_message.video or query.message.reply_to_message.document
        if media:
            file_name = media.file_name

    db_path = "lectures" if type_ == "lec" else "resources"
    
    data_to_save = {
        "name": file_name,
        "url": stream_link,
        "module_id": module_id,
        "type": "video"
    }
    
    # Firebase push
    db.child(db_path).push(data_to_save)
    
    await query.answer(f"✅ Added to {session['module_name']}!", show_alert=True)
    await query.message.edit_text(f"{query.message.text}\n\n✅ **Saved to Database!**")

# --- 6. Handle Direct URL Add Command ---
@Client.on_message(filters.command("add") & filters.private)
async def add_direct_url(bot, message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_sessions:
        await message.reply("❌ Pehle /panel se module select karein.")
        return
        
    session = user_sessions[user_id]
    if session.get("mode") != "url":
        await message.reply("❌ Mode 'Direct URL' par set nahi hai. Button se change karein.")
        return

    try:
        # Command format: /add http://link.com | My Video Name
        text = message.text.split(" ", 1)[1]
        if "|" in text:
            url, name = text.split("|")
        else:
            await message.reply("❌ Format galat hai.\nUse: `/add Link | Name`")
            return
            
        url = url.strip()
        name = name.strip()
        
        data_to_save = {
            "name": name,
            "url": url,
            "module_id": session["module_id"],
            "type": "external"
        }
        
        db.child("lectures").push(data_to_save)
        await message.reply(f"✅ **Lecture Added!**\nName: {name}\nModule: {session['module_name']}")
        
    except IndexError:
        await message.reply("❌ Format: `/add Link | Name`")
