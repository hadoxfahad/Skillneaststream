# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import random
import requests
import humanize
import base64
import binascii
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, CallbackQuery
from info import LOG_CHANNEL, LINK_URL, ADMIN
from plugins.database import checkdb, db, get_count, get_withdraw, record_withdraw, record_visit
from urllib.parse import quote_plus, urlencode
# Make sure TechVJ.util is correctly installed/accessible
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size
from TechVJ.util.human_readable import humanbytes

# Ek naya function jo direct stream URL banayega
async def get_stream_url(client, message_id, use_telegram_cdn=False):
    """
    Generates a direct stream/download URL for a file.
    
    :param client: The Pyrogram client instance.
    :param message_id: The message ID of the file in the LOG_CHANNEL.
    :param use_telegram_cdn: If True, uses Telegram's built-in get_file_link.
                             If False (default), uses the custom render.com domain.
    """
    try:
        msg = await client.get_messages(LOG_CHANNEL, message_id)
        
        if use_telegram_cdn:
            # Use Pyrogram's built-in method for Telegram CDN links
            direct_file_link = await client.get_file_link(msg)
            return str(direct_file_link)
        else:
            # Use your custom render.com domain and custom hash/name logic
            file_name = get_name(msg) # Assumes get_name handles all media types
            file_hash = get_hash(msg) # Assumes get_hash handles all media types
            
            # Critical check: if get_name or get_hash fail, we can't build the URL
            if not file_name:
                print(f"DEBUG: get_name returned None for message_id {message_id}")
                return None
            if not file_hash:
                print(f"DEBUG: get_hash returned None for message_id {message_id}")
                # Decide if you want to proceed without hash or also return None
                # For now, let's assume hash is crucial for your render.com endpoint
                return None 
            
            # Make sure LINK_URL is correctly defined in info.py and points to your website
            # For the direct link, use the base URL for your streaming backend on Render.
            # Example: if your backend is 'https://skill-neast.onrender.com', then use that.
            # I'll use a placeholder `STREAM_SERVER_URL` for clarity.
            # You NEED to define STREAM_SERVER_URL in your info.py if you use this.
            # If your LINK_URL is already `https://skill-neast.onrender.com/` then fine.
            
            # Assuming 'skill-neast.onrender.com' is your actual streaming backend
            # Make sure it can handle the /{message_id}/{quote_plus(file_name)}?hash={file_hash} format
            return f"https://skill-neast.onrender.com/dl/{message_id}/{quote_plus(file_name)}?hash={file_hash}"
            
    except Exception as e:
        print(f"Error in get_stream_url for message_id {message_id}: {e}")
        return None

async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

async def decode(base64_string):
    try:
        base64_string = base64_string.strip("=")
        base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
        string_bytes = base64.urlsafe_b64decode(base64_bytes)
        string = string_bytes.decode("ascii")
        return string
    except (binascii.Error, TypeError):
        print(f"DEBUG: Decode failed for '{base64_string}'") # Added debug
        return None


@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if not await checkdb.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        name = await client.ask(message.chat.id, "<b>Welcome To VJ Disk.\n\nIts Time To Create Account On VJ Disk\n\nNow Send Me Your Business Name Which Show On Website\nEx :- <code>Tech VJ</code></b>")
        if name.text:
            await db.set_name(message.from_user.id, name=name.text)
        else:
            return await message.reply("Wrong Input Start Your Process Again By Hitting /start")
        link = await client.ask(message.chat.id, "<b>Now Send Me Your Telegram Channel Link, Channel Link Will Show On Your Website.\n\nSend Like This <code>https://t.me/VJ_Bots</code> ✅\n\nDo not send like this @VJ_Bots ❌</b>")
        if link.text and link.text.startswith(('http://', 'https://')):
            await db.set_link(message.from_user.id, link=link.text)
        else:
            return await message.reply("Wrong Input Start Your Process Again By Hitting /start")
        await checkdb.add_user(message.from_user.id, message.from_user.first_name)
        return await message.reply("<b>Congratulations 🎉\n\nYour Account Created Successfully.\n\nFor Uploading File In Quality Option Use Command /quality\n\nMore Commands Are /account and /update and /withdraw\n\nFor Without Quality Option Direct Send File To Bot.</b>")
    else:
        rm = InlineKeyboardMarkup([[InlineKeyboardButton("✨ Update Channel", url="https://t.me/VJ_Disk")]])
        await client.send_message(
            chat_id=message.from_user.id,
            text=script.START_TXT.format(message.from_user.mention),
            reply_markup=rm,
            parse_mode=enums.ParseMode.HTML
        )
        return

@Client.on_message(filters.command("update") & filters.private)
async def update(client, message):
    vj = True
    if vj:
        name = await client.ask(message.chat.id, "<b>Now Send Me Your Business Name Which Show On Website\nEx :- <code>Tech VJ</code>\n\n/cancel - cancel the process</b>")
        if name.text == "/cancel":
            return await message.reply("Process Cancelled")
        if name.text:
            await db.set_name(message.from_user.id, name=name.text)
        else:
            return await message.reply("Wrong Input Start Your Process Again By Hitting /update")
        link = await client.ask(message.chat.id, "<b>Now Send Me Your Telegram Channel Link, Channel Link Will Show On Your Website.\n\nSend Like This <code>https://t.me/VJ_Bots</code> ✅\n\nDo not send like this @VJ_Bots ❌</b>")
        if link.text and link.text.startswith(('http://', 'https://')):
            await db.set_link(message.from_user.id, link=link.text)
        else:
            return await message.reply("Wrong Input Start Your Process Again By Hitting /update")
        return await message.reply("<b>Update Successfully.</b>")

# ----------------- REVISED universal_handler -----------------
@Client.on_message(filters.private & (filters.document | filters.video | filters.photo | filters.audio))
async def universal_handler(client, message):
    if not message.media:
        return await message.reply("Please send a file (video, document, audio, etc.).")

    # Get the file object based on its media type
    file = getattr(message, message.media.value)
    file_type = message.media.value
    fileid = file.file_id
    
    print(f"DEBUG: Processing file with ID: {fileid} and type: {file_type}")

    log_msg = None
    try:
        log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
        print(f"DEBUG: File cached in LOG_CHANNEL. Message ID: {log_msg.id}")
    except Exception as e:
        print(f"ERROR: Failed to send cached media to LOG_CHANNEL: {e}")
        return await message.reply("Sorry, I could not save the file to the log channel. Please check bot permissions and try again.")

    if not log_msg:
        print("ERROR: log_msg is None after send_cached_media.")
        return await message.reply("Failed to get log message details.")

    file_name = get_name(log_msg)
    if not file_name:
        print(f"ERROR: get_name returned None for log_msg ID: {log_msg.id}. Media type: {file_type}")
        return await message.reply("Sorry, I couldn't get the name of this file. Ensure it has a recognizable filename.")

    is_video = file_type == 'video' or (file_type == 'document' and file.mime_type and file.mime_type.startswith('video/'))
    
    response_message = ""
    rm = None

    if is_video:
        # Check if it's a .ts file or a general video
        is_ts_file = file_name.lower().endswith('.ts')
        
        if is_ts_file:
            # For .ts files, only provide a direct download link using your custom server
            direct_link = await get_stream_url(client, log_msg.id, use_telegram_cdn=False) # Use custom server
            if not direct_link:
                return await message.reply(f"Error generating direct link for TS file `{file_name}`.")
            
            response_message = (
                f"**🎥 Video:** `{file_name}`\n\n"
                f"**⬇️ Direct Download Link (TS):**\n`{direct_link}`"
            )
            rm = InlineKeyboardMarkup([[InlineKeyboardButton("⬇️ Download Now", url=direct_link)]])
            
        else:
            # For general videos, provide both website player and direct stream URL
            params = {'u': message.from_user.id, 'w': str(log_msg.id), 's': str(0), 't': str(0)}
            url_params_encoded = urlencode(params)
            link_encoded_base64 = await encode(url_params_encoded)
            website_url = f"{LINK_URL}?Tech_VJ={link_encoded_base64}"
            
            direct_stream_url = await get_stream_url(client, log_msg.id, use_telegram_cdn=False) # Use custom server
            if not direct_stream_url:
                direct_stream_url = "Could not generate direct stream URL."
            
            response_message = (
                f"**🎥 Video:** `{file_name}`\n\n"
                f"**🌐 Website Player URL:**\n`{website_url}`\n\n"
                f"**🔗 Direct Stream URL:**\n`{direct_stream_url}`"
            )
            rm = InlineKeyboardMarkup([[InlineKeyboardButton("🖥️ Open Link", url=website_url)]])

    else: # Handle photo, audio, other documents
        direct_link = await get_stream_url(client, log_msg.id, use_telegram_cdn=False) # Use custom server
        if not direct_link:
            return await message.reply(f"Error generating direct download link for `{file_name}`.")
            
        response_message = (
            f"**📄 File:** `{file_name}`\n\n"
            f"**⬇️ Direct Download Link:**\n`{direct_link}`"
        )
        rm = InlineKeyboardMarkup([[InlineKeyboardButton("⬇️ Download Now", url=direct_link)]])

    await message.reply_text(
        text=response_message,
        reply_markup=rm,
        parse_mode=enums.ParseMode.MARKDOWN,
        disable_web_page_preview=True # Prevent Telegram from trying to render previews
    )
# ----------------- REVISED END -----------------


@Client.on_message(filters.private & filters.command("quality"))
async def quality_link(client, message):
    first_id = str(0)
    second_id = str(0)
    third_id = str(0)
    
    # Helper to get file and store in log channel
    async def get_and_store_file(prompt_text):
        file_msg = await client.ask(message.from_user.id, prompt_text)
        if file_msg.video or file_msg.document:
            file = getattr(file_msg, file_msg.media.value)
            fileid = file.file_id
            log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            return str(log_msg.id)
        else:
            return None # Indicate failure
            
    # Ask for first quality
    first_q_text = await client.ask(message.from_user.id, "<b>Now Send Me Your Quality In Which You Upload File. Only Below These Qualities Are Available Only.\n\n1. If your file quality is less than or equal to 480p then send <code>480</code>\n2. If your file quality is greater than 480p and less than or equal to 720p then send <code>720</code>\n3. If your file quality is greater than 720p then send <code>1080</code></b>")
    
    current_qualities = [] # To keep track of chosen qualities

    if first_q_text.text in ["480", "720", "1080"]:
        current_qualities.append(first_q_text.text)
        prompt = f"Now Send Me Your {first_q_text.text}p Quality File."
        file_id_str = await get_and_store_file(prompt)
        if not file_id_str:
            return await message.reply("Wrong Input, Start Process Again By /quality")
        if first_q_text.text == "480": first_id = file_id_str
        elif first_q_text.text == "720": second_id = file_id_str
        elif first_q_text.text == "1080": third_id = file_id_str
    else:
        return await message.reply("Choose Quality From Above Three Quality Only. Send /quality command again to start creating link.")

    # Ask for second quality
    second_q_text = await client.ask(message.from_user.id, "<b>Now Send Me Your **Another** Quality In Which You Upload File. Only Below These Qualities Are Available Only.\n\n1. If your file quality is less than or equal to 480p then send <code>480</code>\n2. If your file quality is greater than 480p and less than or equal to 720p then send <code>720</code>\n3. If your file quality is greater than 720p then send <code>1080</code>\n\nNote Don not use one quality 2 or more time.</b>")

    if second_q_text.text in ["480", "720", "1080"] and second_q_text.text not in current_qualities:
        current_qualities.append(second_q_text.text)
        prompt = f"Now Send Me Your {second_q_text.text}p Quality File."
        file_id_str = await get_and_store_file(prompt)
        if not file_id_str:
            return await message.reply("Wrong Input, Start Process Again By /quality")
        if second_q_text.text == "480": first_id = file_id_str
        elif second_q_text.text == "720": second_id = file_id_str
        elif second_q_text.text == "1080": third_id = file_id_str
    else:
        return await message.reply("Choose Quality From Above Three Quality Only. Send /quality command again to start creating link.")
        
    # Ask for third quality or /getlink
    third_q_text = await client.ask(message.from_user.id, "<b>Now Send Me Your **Another** Quality In Which You Upload File. Only Below These Qualities Are Available Only.\n\n1. If your file quality is less than or equal to 480p then send <code>480</code>\n2. If your file quality is greater than 480p and less than or equal to 720p then send <code>720</code>\n3. If your file quality is greater than 720p then send <code>1080</code>\n\nNote Don not use one quality 2 or more time.\n\nIf you want only 2 quality option then use <code>/getlink</code> command for stream link.</b>")
    
    if third_q_text.text == "/getlink":
        # Process 2 qualities
        pass # Will fall through to link generation below
    elif third_q_text.text in ["480", "720", "1080"] and third_q_text.text not in current_qualities:
        current_qualities.append(third_q_text.text)
        prompt = f"Now Send Me Your {third_q_text.text}p Quality File."
        file_id_str = await get_and_store_file(prompt)
        if not file_id_str:
            return await message.reply("Wrong Input, Start Process Again By /quality")
        if third_q_text.text == "480": first_id = file_id_str
        elif third_q_text.text == "720": second_id = file_id_str
        elif third_q_text.text == "1080": third_id = file_id_str
    else:
        return await message.reply("Choose Quality From Above Three Quality Only or use /getlink. Send /quality command again to start creating link.")

    params = {'u': message.from_user.id, 'w': first_id, 's': second_id, 't': third_id}
    url_params_encoded = urlencode(params)
    link_encoded_base64 = await encode(url_params_encoded)
    
    encoded_url = f"{LINK_URL}?Tech_VJ={link_encoded_base64}"
    
    response_message_parts = [f"**🎥 Video Quality Links:**\n\n**🌐 Website Player URL:**\n`{encoded_url}`\n\n"]
    
    # Get file name for title from the first available quality
    video_title = "Unknown Video"
    try:
        if first_id != "0":
            video_title = get_name(await client.get_messages(LOG_CHANNEL, int(first_id)))
        elif second_id != "0":
            video_title = get_name(await client.get_messages(LOG_CHANNEL, int(second_id)))
        elif third_id != "0":
            video_title = get_name(await client.get_messages(LOG_CHANNEL, int(third_id)))
        if not video_title: # If get_name still returns None
             video_title = "Unknown Video"
    except Exception as e:
        print(f"ERROR: Could not get video title for quality links: {e}")
        video_title = "Unknown Video"
        
    response_message_parts.insert(0, f"**🎥 Video:** `{video_title}`\n\n")

    if first_id != "0":
        first_stream_url = await get_stream_url(client, int(first_id), use_telegram_cdn=False)
        if first_stream_url: response_message_parts.append(f"**🔗 480p Direct URL:**\n`{first_stream_url}`\n\n")
        else: response_message_parts.append(f"**🔗 480p Direct URL:** (Failed to generate)\n\n")

    if second_id != "0":
        second_stream_url = await get_stream_url(client, int(second_id), use_telegram_cdn=False)
        if second_stream_url: response_message_parts.append(f"**🔗 720p Direct URL:**\n`{second_stream_url}`\n\n")
        else: response_message_parts.append(f"**🔗 720p Direct URL:** (Failed to generate)\n\n")

    if third_id != "0":
        third_stream_url = await get_stream_url(client, int(third_id), use_telegram_cdn=False)
        if third_stream_url: response_message_parts.append(f"**🔗 1080p Direct URL:**\n`{third_stream_url}`\n\n")
        else: response_message_parts.append(f"**🔗 1080p Direct URL:** (Failed to generate)\n\n")
    
    response_message = "".join(response_message_parts)

    rm=InlineKeyboardMarkup([[InlineKeyboardButton("🖥️ Open Link", url=encoded_url)]])
    await message.reply_text(text=response_message, reply_markup=rm, parse_mode=enums.ParseMode.MARKDOWN, disable_web_page_preview=True)

@Client.on_message(filters.private & filters.text & ~filters.command(["account", "withdraw", "notify", "quality", "start", "update"]))
async def link_start(client, message):
    if not message.text.startswith(LINK_URL):
        return
    link_part = message.text[len(LINK_URL + "?Tech_VJ="):].strip()
    
    original = await decode(link_part)
    
    if original is None:
        return await message.reply("Link Invalid or Corrupted")

    try:
        # Example original: u=123&w=456&s=0&t=0
        parts = original.split("&")
        data = {p.split("=")[0]: p.split("=")[1] for p in parts}
        
        user_id_from_link = data.get('u')
        log_msg_id = data.get('w')
        s_id = data.get('s')
        t_id = data.get('t')

        if not all([user_id_from_link, log_msg_id, s_id, t_id]):
            raise ValueError("Missing parameters in link.")

    except (ValueError, IndexError) as e:
        print(f"DEBUG: Error parsing link parameters: {e}")
        return await message.reply("Link Invalid or Corrupted. Failed to parse parameters.")
        
    if user_id_from_link == str(message.from_user.id):
        # If the user is requesting their own link, just resend it
        rm=InlineKeyboardMarkup([[InlineKeyboardButton("🖥️ Open Link", url=message.text)]])
        return await message.reply_text(text=f"<code>{message.text}</code>", reply_markup=rm, disable_web_page_preview=True)
    
    # Generate a new website URL with the requesting user's ID for tracking
    new_params = {'u': message.from_user.id, 'w': log_msg_id, 's': s_id, 't': t_id}
    new_url_params_encoded = urlencode(new_params)
    new_link_encoded_base64 = await encode(new_url_params_encoded)
    encoded_url = f"{LINK_URL}?Tech_VJ={new_link_encoded_base64}"

    # Generate direct stream URLs for all available qualities
    response_message_parts = [f"**🎥 Video Links from Shared Link:**\n\n**🌐 Website Player URL:**\n`{encoded_url}`\n\n"]

    # Attempt to get file name for title
    video_title = "Unknown Video"
    try:
        if log_msg_id != "0":
            video_title = get_name(await client.get_messages(LOG_CHANNEL, int(log_msg_id)))
        elif s_id != "0":
            video_title = get_name(await client.get_messages(LOG_CHANNEL, int(s_id)))
        elif t_id != "0":
            video_title = get_name(await client.get_messages(LOG_CHANNEL, int(t_id)))
        if not video_title:
            video_title = "Unknown Video"
    except Exception as e:
        print(f"ERROR: Could not get video title for shared link: {e}")
    response_message_parts.insert(0, f"**🎥 Video:** `{video_title}`\n\n")

    if log_msg_id != "0": # Primary quality (usually 480p or default)
        direct_stream_url = await get_stream_url(client, int(log_msg_id), use_telegram_cdn=False)
        if direct_stream_url: response_message_parts.append(f"**🔗 Primary Direct URL:**\n`{direct_stream_url}`\n\n")
        else: response_message_parts.append(f"**🔗 Primary Direct URL:** (Failed to generate)\n\n")

    if s_id != "0": # Secondary quality (e.g., 720p)
        direct_stream_url = await get_stream_url(client, int(s_id), use_telegram_cdn=False)
        if direct_stream_url: response_message_parts.append(f"**🔗 Secondary Direct URL:**\n`{direct_stream_url}`\n\n")
        else: response_message_parts.append(f"**🔗 Secondary Direct URL:** (Failed to generate)\n\n")
        
    if t_id != "0": # Tertiary quality (e.g., 1080p)
        direct_stream_url = await get_stream_url(client, int(t_id), use_telegram_cdn=False)
        if direct_stream_url: response_message_parts.append(f"**🔗 Tertiary Direct URL:**\n`{direct_stream_url}`\n\n")
        else: response_message_parts.append(f"**🔗 Tertiary Direct URL:** (Failed to generate)\n\n")

    response_message = "".join(response_message_parts)

    rm=InlineKeyboardMarkup([[InlineKeyboardButton("🖥️ Open Link", url=encoded_url)]])
    await message.reply_text(text=response_message, reply_markup=rm, parse_mode=enums.ParseMode.MARKDOWN, disable_web_page_preview=True)


@Client.on_message(filters.private & filters.command("account"))
async def show_account(client, message):
    link_clicks = get_count(message.from_user.id)
    if link_clicks:
        balance = link_clicks / 1000.0
        formatted_balance = f"{balance:.2f}"
        response = f"<b>Your Api Key :- <code>{message.from_user.id}</code>\n\nVideo Plays :- {link_clicks} ( Delay To Show Data )\n\nBalance :- ${formatted_balance}</b>"
    else:
        response = f"<b>Your Api Key :- <code>{message.from_user.id}</code>\nVideo Plays :- 0 ( Delay To Show Data )\nBalance :- $0</b>"
    await message.reply(response)

@Client.on_message(filters.private & filters.command("withdraw"))
async def show_withdraw(client, message):
    w = get_withdraw(message.from_user.id)
    if w == True:
        return await message.reply("One Withdrawal Is In Process Wait For Complete It")
    link_clicks = get_count(message.from_user.id)
    if not link_clicks:
        return await message.reply("You Are Not Eligible For Withdrawal.\nMinimum Withraw Is 1000 Link Clicks or Video Plays.")
    if link_clicks >= 1000:
        confirm = await client.ask(message.from_user.id, "You Are Going To Withdraw All Your Link Clicks. Are You Sure You Want To Withdraw ?\nSend /yes or /no")
        if confirm.text == "/no":
            return await message.reply("Withdraw Cancelled by you ❌")
        else:
            pay = await client.ask(message.from_user.id, "Now Choose Your Payment Method, Click On In Which You Want Your Withdrawal.\n\n/upi - for upi, webmoney, airtm, capitalist\n\n/bank - for bank only")
            upi_string = "" # Initialize outside the if/elif blocks
            if pay.text == "/upi":
                upi_details = await client.ask(message.from_user.id, "Now Send Me Your Upi Or Upi Number With Your Name, Make Sure Name Matches With Your Upi Account")
                if not upi_details.text:
                    return await message.reply("Wrong Input ❌")
                upi_string = f"Upi - {upi_details.text}"
                try:
                    await upi_details.delete()
                except Exception:
                    pass
            elif pay.text == "/bank":
                name = await client.ask(message.from_user.id, "Now Send Me Your Account Holder Full Name")
                if not name.text:
                    return await message.reply("Wrong Input ❌")
                number_msg = await client.ask(message.from_user.id, "Now Send Me Your Account Number")
                try:
                    if not int(number_msg.text):
                        return await message.reply("Wrong Input ❌")
                except ValueError:
                     return await message.reply("Wrong Input ❌")
                ifsc = await client.ask(message.from_user.id, "Now Send Me Your IFSC Code.")
                if not ifsc.text:
                    return await message.reply("Wrong Input ❌")
                bank_name = await client.ask(message.from_user.id, "Now Send You Can Send Necessary Thing In One Message, Like Send Bank Name, Or Contact Details.")
                if not bank_name.text:
                    return await message.reply("Wrong Input ❌")
                upi_string = (
                    f"Account Holder Name - {name.text}\n\n"
                    f"Account Number - {number_msg.text}\n\n"
                    f"IFSC Code - {ifsc.text}\n\n"
                    f"Bank Name - {bank_name.text}\n\n"
                )
                try:
                    await name.delete()
                    await number_msg.delete()
                    await ifsc.delete()
                    await bank_name.delete()
                except Exception:
                    pass
            else:
                return await message.reply("Invalid payment method. Please use /upi or /bank.")
            
            traffic = await client.ask(message.from_user.id, "Now Send Me Your Traffic Source Link, If Your Link Click Are Fake Then You Will Not Receive Payment And Withdrawal Get Cancelled")
            if not traffic.text:
                return await message.reply("Wrong Traffic Source ❌")
            
            balance = link_clicks / 1000.0
            formatted_balance = f"{balance:.2f}"
            text = (
                f"Api Key - {message.from_user.id}\n\n"
                f"Video Plays - {link_clicks}\n\n"
                f"Balance - ${formatted_balance}\n\n"
                f"{upi_string}" # Use the consolidated string
                f"Traffic Link - {traffic.text}"
            )
            
            await client.send_message(ADMIN, text)
            record_withdraw(message.from_user.id, True)
            await message.reply(f"Your Withdrawal Balance - ${formatted_balance}\n\nNow Your Withdrawal Send To Owner, If Everything Fullfill The Criteria Then You Will Get Your Payment Within 3 Working Days.")
    else:
        await message.reply("Your Video Plays Smaller Than 1000 Plays, Minimum Payout Is 1000 Video Plays or Link Clicks.")

@Client.on_message(filters.private & filters.command("notify") & filters.chat(ADMIN))
async def show_notify(client, message):
    count = int(1)
    user_id_msg = await client.ask(message.from_user.id, "Now Send Me Api Key Of User")
    try:
        user_id = int(user_id_msg.text)
    except ValueError:
        return await message.reply("Invalid User ID. Please send a valid integer API Key.")

    sub = await client.ask(message.from_user.id, "Payment Is Cancelled Or Send Successfully. /send or /cancel")
    if sub.text == "/send":
        record_visits(user_id, count)
        record_withdraw(user_id, False)
        await client.send_message(user_id, "Your Withdrawal Is Successfully Completed And Sended To Your Bank Account.")
    else:
        reason = await client.ask(message.from_user.id, "Send Me The Reason For Cancellation of Payment")
        if reason.text:
            record_visits(user_id, count)
            record_withdraw(user_id, False)
            await client.send_message(user_id, f"Your Payment Cancelled - {reason.text}")
    await message.reply("Successfully Message Send.")
