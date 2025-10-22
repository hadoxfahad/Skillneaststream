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

async def encode(string):
    try:
        string_bytes = string.encode("ascii")
        base64_bytes = base64.urlsafe_b64encode(string_bytes)
        base64_string = (base64_bytes.decode("ascii")).strip("=")
        return base64_string
    except:
        pass

async def decode(base64_string):
    try:
        base64_string = base64_string.strip("=")
        base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
        string_bytes = base64.urlsafe_b64decode(base64_bytes)
        string = string_bytes.decode("ascii")
        return string
    except:
        pass

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
        name = await client.ask(message.from_user.id, "<b>Now Send Me Your Business Name Which Show On Website\nEx :- <code>Tech VJ</code>\n\n/cancel - cancel the process</b>")
        if name.text == "/cancel":
            return await message.reply("Process Cancelled")
        if name.text:
            await db.set_name(message.from_user.id, name=name.text)
        else:
            return await message.reply("Wrong Input Start Your Process Again By Hitting /update")
        link = await client.ask(message.from_user.id, "<b>Now Send Me Your Telegram Channel Link, Channel Link Will Show On Your Website.\n\nSend Like This <code>https://t.me/VJ_Bots</code> ✅\n\nDo not send like this @VJ_Bots ❌</b>")
        if link.text and link.text.startswith(('http://', 'https://')):
            await db.set_link(message.from_user.id, link=link.text)
        else:
            return await message.reply("Wrong Input Start Your Process Again By Hitting /update")
        return await message.reply("<b>Update Successfully.</b>")

@Client.on_message(filters.private & (filters.document | filters.video))
async def stream_start(client, message):
    file = getattr(message, message.media.value)
    fileid = file.file_id
    user_id = message.from_user.id
    
    # Send cached media to LOG_CHANNEL
    log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
    
    # --- Generate Website URL ---
    params = {'u': user_id, 'w': str(log_msg.id), 's': str(0), 't': str(0)}
    url_params_encoded = urlencode(params)
    link_encoded_base64 = await encode(url_params_encoded)
    website_url = f"{LINK_URL}?Tech_VJ={link_encoded_base64}"
    
    # --- Generate Direct Stream URL ---
    # The direct stream URL from Telegram's CDN is usually available via get_file link
    # This URL is transient and might expire, but it's the closest to "direct"
    # For a more persistent direct stream, you'd need your own server/CDN.
    try:
        direct_file_link = await client.get_file_link(log_msg)
        direct_stream_url = str(direct_file_link)
    except Exception as e:
        print(f"Error getting direct file link: {e}")
        direct_stream_url = "Could not generate direct stream URL."

    # Send both URLs
    response_text = f"<b>Website URL:</b>\n<code>{website_url}</code>\n\n"
    response_text += f"<b>Direct Stream URL:</b>\n<code>{direct_stream_url}</code>"
    
    rm=InlineKeyboardMarkup([[InlineKeyboardButton("🖇️ Open Website Link", url=website_url)]])
    await message.reply_text(text=response_text, reply_markup=rm, disable_web_page_preview=True)

@Client.on_message(filters.private & filters.command("quality"))
async def quality_link(client, message):
    first_id = str(0)
    second_id = str(0)
    third_id = str(0)
    first = await client.ask(message.from_user.id, "<b>Now Send Me Your Quality In Which You Upload File. Only Below These Qualities Are Available Only.\n\n1. If your file quality is less than or equal to 480p then send <code>480</code>\n2. If your file quality is greater than 480p and less than or equal to 720p then send <code>720</code>\n3. If your file quality is greater than 720p then send <code>1080</code></b>")
    if first.text == "480":
        f_id = await client.ask(message.from_user.id, "Now Send Me Your 480p Quality File.")
        if f_id.video or f_id.document:
            file = getattr(f_id, f_id.media.value)
            fileid = file.file_id
            first_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            first_id = str(first_msg.id)
        else:
            return await message.reply("Wrong Input, Start Process Again By /quality")
    elif first.text == "720":
        s_id = await client.ask(message.from_user.id, "Now Send Me Your 720p Quality File.")
        if s_id.video or s_id.document:
            file = getattr(s_id, s_id.media.value)
            fileid = file.file_id
            first_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            second_id = str(first_msg.id)
        else:
            return await message.reply("Wrong Input, Start Process Again By /quality")
    elif first.text == "1080":
        t_id = await client.ask(message.from_user.id, "Now Send Me Your 1080p Quality File.")
        if t_id.video or t_id.document:
            file = getattr(t_id, t_id.media.value)
            fileid = file.file_id
            first_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            third_id = str(first_msg.id)
        else:
            return await message.reply("Wrong Input, Start Process Again By /quality")
    else:
        return await message.reply("Choose Quality From Above Three Quality Only. Send /quality commamd again to start creating link.")

    second = await client.ask(message.from_user.id, "<b>Now Send Me Your Another Quality In Which You Upload File. Only Below These Qualities Are Available Only.\n\n1. If your file quality is less than or equal to 480p then send <code>480</code>\n2. If your file quality is greater than 480p and less than or equal to 720p then send <code>720</code>\n3. If your file quality is greater than 720p then send <code>1080</code>\n\nNote Don not use one quality 2 or more time.</b>")
    if second.text != first.text and second.text == "480":
        f_id = await client.ask(message.from_user.id, "Now Send Me Your 480p Quality File.")
        if f_id.video or f_id.document:
            file = getattr(f_id, f_id.media.value)
            fileid = file.file_id
            first_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            first_id = str(first_msg.id)
        else:
            return await message.reply("Wrong Input, Start Process Again By /quality")
    elif second.text != first.text and second.text == "720":
        s_id = await client.ask(message.from_user.id, "Now Send Me Your 720p Quality File.")
        if s_id.video or s_id.document:
            file = getattr(s_id, s_id.media.value)
            fileid = file.file_id
            first_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            second_id = str(first_msg.id)
        else:
            return await message.reply("Wrong Input, Start Process Again By /quality")
    elif second.text != first.text and second.text == "1080":
        t_id = await client.ask(message.from_user.id, "Now Send Me Your 1080p Quality File.")
        if t_id.video or t_id.document:
            file = getattr(t_id, t_id.media.value)
            fileid = file.file_id
            first_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            third_id = str(first_msg.id)
        else:
            return await message.reply("Wrong Input, Start Process Again By /quality")
    else:
        return await message.reply("Choose Quality From Above Three Quality Only. Send /quality commamd again to start creating link.")

    third = await client.ask(message.from_user.id, "<b>Now Send Me Your Another Quality In Which You Upload File. Only Below These Qualities Are Available Only.\n\n1. If your file quality is less than or equal to 480p then send <code>480</code>\n2. If your file quality is greater than 480p and less than or equal to 720p then send <code>720</code>\n3. If your file quality is greater than 720p then send <code>1080</code>\n\nNote Don not use one quality 2 or more time.\n\nIf you want only 2 quality option then use <code>/getlink</code> command for stream link.</b>")
    if third.text != second.text and third.text != first.text and third.text == "480":
        f_id = await client.ask(message.from_user.id, "Now Send Me Your 480p Quality File.")
        if f_id.video or f_id.document:
            file = getattr(f_id, f_id.media.value)
            fileid = file.file_id
            first_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            first_id = str(first_msg.id)
        else:
            return await message.reply("Wrong Input, Start Process Again By /quality")
    elif third.text != second.text and third.text != first.text and third.text == "720":
        s_id = await client.ask(message.from_user.id, "Now Send Me Your 720p Quality File.")
        if s_id.video or s_id.document:
            file = getattr(s_id, s_id.media.value)
            fileid = file.file_id
            first_msg = await client.send_cached_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            second_id = str(first_msg.id)
        else:
            return await message.reply("Wrong Input, Start Process Again By /quality")
    elif third.text != second.text and third.text != first.text and third.text == "1080":
        t_id = await client.ask(message.from_user.id, "Now Send Me Your 1080p Quality File.")
        if t_id.video or t_id.document:
            file = getattr(t_id, t_id.media.value)
            fileid = file.file_id
            first_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
            third_id = str(first_msg.id)
        else:
            return await message.reply("Wrong Input, Start Process Again By /quality")
    elif third.text == "/getlink":
        params = {'u': message.from_user.id, 'w': first_id, 's': second_id, 't': third_id}
        url_params_encoded = urlencode(params)
        link_encoded_base64 = await encode(url_params_encoded)
        website_url = f"{LINK_URL}?Tech_VJ={link_encoded_base64}"
        
        # Get direct stream URL for the primary quality (first_id if available, otherwise second_id or third_id)
        # This part assumes you'd want the direct stream of *one* of the qualities.
        # You might need to refine which quality's direct link you want to provide here.
        direct_stream_url_for_quality = "Could not generate direct stream URL for qualities."
        try:
            if first_id != "0":
                temp_msg = await client.get_messages(LOG_CHANNEL, int(first_id))
                direct_stream_url_for_quality = str(await client.get_file_link(temp_msg))
            elif second_id != "0":
                temp_msg = await client.get_messages(LOG_CHANNEL, int(second_id))
                direct_stream_url_for_quality = str(await client.get_file_link(temp_msg))
            elif third_id != "0":
                temp_msg = await client.get_messages(LOG_CHANNEL, int(third_id))
                direct_stream_url_for_quality = str(await client.get_file_link(temp_msg))
        except Exception as e:
            print(f"Error getting direct file link for quality: {e}")

        response_text = f"<b>Website URL:</b>\n<code>{website_url}</code>\n\n"
        response_text += f"<b>Direct Stream URL (Quality):</b>\n<code>{direct_stream_url_for_quality}</code>"

        rm=InlineKeyboardMarkup([[InlineKeyboardButton("🖇️ Open Website Link", url=website_url)]])
        return await message.reply_text(text=response_text, reply_markup=rm, disable_web_page_preview=True)
    else:
        return await message.reply("Choose Quality From Above Three Quality Only. Send /quality commamd again to start creating link.")

    params = {'u': message.from_user.id, 'w': first_id, 's': second_id, 't': third_id}
    url_params_encoded = urlencode(params)
    link_encoded_base64 = await encode(url_params_encoded)
    website_url = f"{LINK_URL}?Tech_VJ={link_encoded_base64}"

    # Get direct stream URL for the primary quality (first_id if available, otherwise second_id or third_id)
    # This part assumes you'd want the direct stream of *one* of the qualities.
    # You might need to refine which quality's direct link you want to provide here.
    direct_stream_url_for_quality = "Could not generate direct stream URL for qualities."
    try:
        if first_id != "0":
            temp_msg = await client.get_messages(LOG_CHANNEL, int(first_id))
            direct_stream_url_for_quality = str(await client.get_file_link(temp_msg))
        elif second_id != "0":
            temp_msg = await client.get_messages(LOG_CHANNEL, int(second_id))
            direct_stream_url_for_quality = str(await client.get_file_link(temp_msg))
        elif third_id != "0":
            temp_msg = await client.get_messages(LOG_CHANNEL, int(third_id))
            direct_stream_url_for_quality = str(await client.get_file_link(temp_msg))
    except Exception as e:
        print(f"Error getting direct file link for quality: {e}")
    
    response_text = f"<b>Website URL:</b>\n<code>{website_url}</code>\n\n"
    response_text += f"<b>Direct Stream URL (Quality):</b>\n<code>{direct_stream_url_for_quality}</code>"

    rm=InlineKeyboardMarkup([[InlineKeyboardButton("🖇️ Open Website Link", url=website_url)]])
    await message.reply_text(text=response_text, reply_markup=rm, disable_web_page_preview=True)

@Client.on_message(filters.private & filters.text & ~filters.command(["account", "withdraw", "notify", "quality", "start", "update"]))
async def link_start(client, message):
    if not message.text.startswith(LINK_URL):
        return
    link_part = message.text[len(LINK_URL + "?Tech_VJ="):].strip()
    try:
        original = await decode(link_part)
    except:
        return await message.reply("Link Invalid")
    try:
        u, user_id, id, sec, th = original.split("=")
    except:
        return await message.reply("Link Invalid")
    
    user_id = user_id.replace("&w", "")
    if int(user_id) == message.from_user.id: # Ensure user_id is integer for comparison
        rm=InlineKeyboardMarkup([[InlineKeyboardButton("🖇️ Open Link", url=message.text)]])
        return await message.reply_text(text=f"<code>{message.text}</code>", reply_markup=rm)
    
    id = id.replace("&s", "")
    sec = sec.replace("&t", "")

    # For existing links being re-sent, also provide direct stream URL
    website_url = message.text
    direct_stream_url_for_existing_link = "Could not retrieve direct stream URL."
    try:
        # Assuming 'id' is the log_msg.id for the primary file
        if id != "0":
            temp_msg = await client.get_messages(LOG_CHANNEL, int(id))
            direct_stream_url_for_existing_link = str(await client.get_file_link(temp_msg))
        elif sec != "0": # Fallback to secondary if primary is missing
            temp_msg = await client.get_messages(LOG_CHANNEL, int(sec))
            direct_stream_url_for_existing_link = str(await client.get_file_link(temp_msg))
        elif th != "0": # Fallback to tertiary
            temp_msg = await client.get_messages(LOG_CHANNEL, int(th))
            direct_stream_url_for_existing_link = str(await client.get_file_link(temp_msg))
    except Exception as e:
        print(f"Error getting direct file link for existing link: {e}")

    response_text = f"<b>Website URL:</b>\n<code>{website_url}</code>\n\n"
    response_text += f"<b>Direct Stream URL:</b>\n<code>{direct_stream_url_for_existing_link}</code>"

    rm=InlineKeyboardMarkup([[InlineKeyboardButton("🖇️ Open Website Link", url=website_url)]])
    await message.reply_text(text=response_text, reply_markup=rm, disable_web_page_preview=True)


@Client.on_message(filters.private & filters.command("account"))
async def show_account(client, message):
    link_clicks = get_count(message.from_user.id)
    if link_clicks:
        balance = link_clicks / 1000.0  # Use floating-point division
        formatted_balance = f"{balance:.2f}"  # Format to 2 decimal places
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
            return await message.reply("Withdraw Cancelled By You ❌")
        else:
            pay = await client.ask(message.from_user.id, "Now Choose Your Payment Method, Click On In Which You Want Your Withdrawal.\n\n/upi - for upi, webmoney, airtm, capitalist\n\n/bank - for bank only")
            if pay.text == "/upi":
                upi_details = await client.ask(message.from_user.id, "Now Send Me Your Upi Or Upi Number With Your Name, Make Sure Name Matches With Your Upi Account")
                if not upi_details.text:
                    return await message.reply("Wrong Input ❌")
                upi_string = f"Upi - {upi_details.text}"
                try:
                    upi_details.delete()
                except:
                    pass
            elif pay.text == "/bank":
                name = await client.ask(message.from_user.id, "Now Send Me Your Account Holder Full Name")
                if not name.text:
                    return await message.reply("Wrong Input ❌")
                number = await client.ask(message.from_user.id, "Now Send Me Your Account Number")
                try:
                    if not int(number.text): # Check if it's a valid integer
                        return await message.reply("Wrong Input ❌")
                except ValueError: # Catch error if conversion to int fails
                     return await message.reply("Wrong Input ❌")
                ifsc = await client.ask(message.from_user.id, "Now Send Me Your IFSC Code.")
                if not ifsc.text:
                    return await message.reply("Wrong Input ❌")
                bank_name = await client.ask(message.from_user.id, "Now Send You Can Send Necessary Thing In One Message, Like Send Bank Name, Or Contact Details.")
                if not bank_name.text:
                    return await message.reply("Wrong Input ❌")
                upi_string = f"Account Holder Name - {name.text}\n\nAccount Number - {number.text}\n\nIFSC Code - {ifsc.text}\n\nBank Name - {bank_name.text}\n\n"
                try:
                    await name.delete()
                    await number.delete()
                    await ifsc.delete()
                    await bank_name.delete()
                except:
                    pass
            else:
                return await message.reply("Invalid payment method. Please use /upi or /bank.")
            
            traffic = await client.ask(message.from_user.id, "Now Send Me Your Traffic Source Link, If Your Link Click Are Fake Then You Will Not Receive Payment And Withdrawal Get Cancelled")
            if not traffic.text:
                return await message.reply("Wrong Traffic Source ❌")
            
            balance = link_clicks / 1000.0
            formatted_balance = f"{balance:.2f}"
            text = f"Api Key - {message.from_user.id}\n\n"
            text += f"Video Plays - {link_clicks}\n\n"
            text += f"Balance - ${formatted_balance}\n\n"
            text += upi_string
            text += f"Traffic Link - {traffic.text}"
            
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
        record_visits(user_id, count) # Assuming record_visits logs an event, might need adjustment based on its actual use for 'count'
        record_withdraw(user_id, False) # Mark withdrawal as completed/processed
        await client.send_message(user_id, "Your Withdrawal Is Successfully Completed And Sended To Your Bank Account.")
    else:
        reason = await client.ask(message.from_user.id, "Send Me The Reason For Cancellation Of Payment")
        if reason.text:
            record_visits(user_id, count) # Still record a visit or activity, but the withdrawal status is reset
            record_withdraw(user_id, False) # Mark withdrawal as cancelled, so user can try again
            await client.send_message(user_id, f"Your Payment Cancelled - {reason.text}")
    await message.reply("Successfully Message Send.")
