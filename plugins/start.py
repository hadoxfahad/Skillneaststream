import random
import requests
import humanize
import base64
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, CallbackQuery
from info import LOG_CHANNEL, LINK_URL, ADMIN
from plugins.database import checkdb, db, get_count, get_withdraw, record_withdraw, record_visit
from urllib.parse import quote_plus, urlencode
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size
from TechVJ.util.human_readable import humanbytes

# ... (encode and decode functions - no changes needed here) ...

@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    # ... (start function - no changes needed here) ...
    pass

@Client.on_message(filters.command("update") & filters.private)
async def update(client, message):
    # ... (update function - no changes needed here) ...
    pass

@Client.on_message(filters.private & (filters.document | filters.video))
async def stream_start(client, message):
    file = getattr(message, message.media.value)
    fileid = file.file_id
    user_id = message.from_user.id
    
    print(f"[{message.from_user.id}] - Received file. File ID: {fileid}") # Debug log

    log_msg = None # Initialize log_msg
    try:
        log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
        print(f"[{message.from_user.id}] - Sent to LOG_CHANNEL. Log Message ID: {log_msg.id}") # Debug log
    except Exception as e:
        print(f"[{message.from_user.id}] - Error sending cached media to LOG_CHANNEL: {e}") # Debug log
        # If sending to log channel fails, we can't get a direct link
        return await message.reply("Failed to process file. Could not save to log channel.")

    if not log_msg: # If log_msg is None for some reason
        print(f"[{message.from_user.id}] - log_msg is None after sending to LOG_CHANNEL.") # Debug log
        return await message.reply("Failed to process file. Log message not created.")

    # --- Generate Website URL ---
    params = {'u': user_id, 'w': str(log_msg.id), 's': str(0), 't': str(0)}
    url_params_encoded = urlencode(params)
    link_encoded_base64 = await encode(url_params_encoded)
    website_url = f"{LINK_URL}?Tech_VJ={link_encoded_base64}"
    
    # --- Generate Direct Stream URL ---
    direct_stream_url = "Could not generate direct stream URL." # Default message
    try:
        # Pass the log_msg object directly to get_file_link
        direct_file_link = await client.get_file_link(log_msg)
        direct_stream_url = str(direct_file_link)
        print(f"[{message.from_user.id}] - Successfully generated direct stream URL: {direct_stream_url}") # Debug log
    except Exception as e:
        print(f"[{message.from_user.id}] - Error generating direct file link for log_msg (ID: {log_msg.id}): {e}") # Debug log

    # Send both URLs
    response_text = f"<b>Website URL:</b>\n<code>{website_url}</code>\n\n"
    response_text += f"<b>Direct Stream URL:</b>\n<code>{direct_stream_url}</code>"
    
    rm=InlineKeyboardMarkup([[InlineKeyboardButton("🖇️ Open Website Link", url=website_url)]])
    await message.reply_text(text=response_text, reply_markup=rm, disable_web_page_preview=True)

# ... (rest of your code - quality_link, link_start, account, withdraw, notify functions) ...
