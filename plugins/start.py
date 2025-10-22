import random
import requests
import humanize
import base64
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, CallbackQuery
from info import LOG_CHANNEL, LINK_URL, ADMIN
from plugins.database import checkdb, db, get_count, get_withdraw, record_withdraw, record_visit, record_visits
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

@Client.on_message(filters.private & (filters.document | filters.video))
async def stream_start(client, message):
    file = getattr(message, message.media.value)
    fileid = file.file_id
    user_id = message.from_user.id
    log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
    params = {'u': user_id, 'w': str(log_msg.id), 's': str(0), 't': str(0)}
    url1 = f"{urlencode(params)}"
    link = await encode(url1)
    encoded_website_url = f"{LINK_URL}?Tech_VJ={link}"
    direct_stream_url = f"https://your_direct_stream_domain.com/stream/{log_msg.id}" # Replace with your actual direct stream domain

    rm = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥️ Open Website Link", url=encoded_website_url)],
        [InlineKeyboardButton("🔗 Copy Direct Stream Link", callback_data=f"copy_direct_stream_{log_msg.id}")]
    ])
    await message.reply_text(
        text=f"**Website Link:**\n`{encoded_website_url}`\n\n"
             f"**Direct Stream Link:**\n`{direct_stream_url}`",
        reply_markup=rm,
        parse_mode=enums.ParseMode.MARKDOWN
    )

@Client.on_callback_query(filters.regex(r"copy_direct_stream_(\d+)"))
async def copy_direct_stream_callback(client, callback_query: CallbackQuery):
    log_msg_id = callback_query.data.split("_")[-1]
    direct_stream_url = f"https://your_direct_stream_domain.com/stream/{log_msg_id}" # Replace with your actual direct stream domain
    await callback_query.answer(f"Direct Stream Link copied:\n{direct_stream_url}", show_alert=True)
    # You could also edit the message to show the copied link, but for a simple "copy" action, an alert is usually sufficient.

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

    second = await client.ask(message.from_user.id, "<b>Now Send Me Your **Another** Quality In Which You Upload File. Only Below These Qualities Are Available Only.\n\n1. If your file quality is less than or equal to 480p then send <code>480</code>\n2. If your file quality is greater than 480p and less than or equal to 720p then send <code>720</code>\n3. If your file quality is greater than 720p then send <code>1080</code>\n\nNote Don not use one quality 2 or more time.</b>")
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
        
    third = await client.ask(message.from_user.id, "<b>Now Send Me Your **Another** Quality In Which You Upload File. Only Below These Qualities Are Available Only.\n\n1. If your file quality is less than or equal to 480p then send <code>480</code>\n2. If your file quality is greater than 480p and less than or equal to 720p then send <code>720</code>\n3. If your file quality is greater than 720p then send <code>1080</code>\n\nNote Don not use one quality 2 or more time.\n\nIf you want only 2 quality option then use <code>/getlink</code> command for stream link.</b>")
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
            first_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
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
        url1 = f"{urlencode(params)}"
        link = await encode(url1)
        encoded_website_url = f"{LINK_URL}?Tech_VJ={link}"
        
        # Determine direct stream URLs based on available quality IDs
        direct_stream_urls = []
        if first_id != "0":
            direct_stream_urls.append(f"480p: https://your_direct_stream_domain.com/stream/{first_id}")
        if second_id != "0":
            direct_stream_urls.append(f"720p: https://your_direct_stream_domain.com/stream/{second_id}")
        if third_id != "0":
            direct_stream_urls.append(f"1080p: https://your_direct_stream_domain.com/stream/{third_id}")

        direct_stream_text = "\n".join([f"`{url}`" for url in direct_stream_urls]) if direct_stream_urls else "No direct stream URLs available."

        rm = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖥️ Open Website Link", url=encoded_website_url)],
            [InlineKeyboardButton("🔗 Copy Direct Stream Links", callback_data=f"copy_multi_direct_stream_{first_id}_{second_id}_{third_id}")]
        ])
        return await message.reply_text(
            text=f"**Website Link:**\n`{encoded_website_url}`\n\n"
                 f"**Direct Stream Links (if available):**\n{direct_stream_text}",
            reply_markup=rm,
            parse_mode=enums.ParseMode.MARKDOWN
        )
    else:
        return await message.reply("Choose Quality From Above Three Quality Only. Send /quality commamd again to start creating link.")

    params = {'u': message.from_user.id, 'w': first_id, 's': second_id, 't': third_id}
    url1 = f"{urlencode(params)}"
    link = await encode(url1)
    encoded_website_url = f"{LINK_URL}?Tech_VJ={link}"

    # Determine direct stream URLs based on available quality IDs
    direct_stream_urls = []
    if first_id != "0":
        direct_stream_urls.append(f"480p: https://your_direct_stream_domain.com/stream/{first_id}")
    if second_id != "0":
        direct_stream_urls.append(f"720p: https://your_direct_stream_domain.com/stream/{second_id}")
    if third_id != "0":
        direct_stream_urls.append(f"1080p: https://your_direct_stream_domain.com/stream/{third_id}")

    direct_stream_text = "\n".join([f"`{url}`" for url in direct_stream_urls]) if direct_stream_urls else "No direct stream URLs available."

    rm = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥️ Open Website Link", url=encoded_website_url)],
        [InlineKeyboardButton("🔗 Copy Direct Stream Links", callback_data=f"copy_multi_direct_stream_{first_id}_{second_id}_{third_id}")]
    ])
    await message.reply_text(
        text=f"**Website Link:**\n`{encoded_website_url}`\n\n"
             f"**Direct Stream Links (if available):**\n{direct_stream_text}",
        reply_markup=rm,
        parse_mode=enums.ParseMode.MARKDOWN
    )

@Client.on_callback_query(filters.regex(r"copy_multi_direct_stream_(\d+)_(\d+)_(\d+)"))
async def copy_multi_direct_stream_callback(client, callback_query: CallbackQuery):
    parts = callback_query.data.split("_")
    first_id = parts[-3]
    second_id = parts[-2]
    third_id = parts[-1]

    direct_stream_urls = []
    if first_id != "0":
        direct_stream_urls.append(f"480p: https://your_direct_stream_domain.com/stream/{first_id}")
    if second_id != "0":
        direct_stream_urls.append(f"720p: https://your_direct_stream_domain.com/stream/{second_id}")
    if third_id != "0":
        direct_stream_urls.append(f"1080p: https://your_direct_stream_domain.com/stream/{third_id}")

    if direct_stream_urls:
        stream_links_text = "\n".join(direct_stream_urls)
        await callback_query.answer(f"Direct Stream Links copied:\n{stream_links_text}", show_alert=True)
    else:
        await callback_query.answer("No direct stream links available to copy.", show_alert=True)


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
        u_prefix, user_id_part, w_prefix, id_val, s_prefix, sec_val, t_prefix, th_val = original.split("=")
        user_id = user_id_part.replace("&w", "")
        id_val = id_val.replace("&s", "")
        sec_val = sec_val.replace("&t", "")
        th_val = th_val
    except ValueError:
        return await message.reply("Link Invalid or malformed parameters.")

    if int(user_id) == message.from_user.id:
        encoded_website_url = message.text
        
        direct_stream_urls = []
        if id_val != "0":
            direct_stream_urls.append(f"480p: https://your_direct_stream_domain.com/stream/{id_val}")
        if sec_val != "0":
            direct_stream_urls.append(f"720p: https://your_direct_stream_domain.com/stream/{sec_val}")
        if th_val != "0":
            direct_stream_urls.append(f"1080p: https://your_direct_stream_domain.com/stream/{th_val}")
        
        direct_stream_text = "\n".join([f"`{url}`" for url in direct_stream_urls]) if direct_stream_urls else "No direct stream URLs available."
        
        rm = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖥️ Open Website Link", url=encoded_website_url)],
            [InlineKeyboardButton("🔗 Copy Direct Stream Links", callback_data=f"copy_multi_direct_stream_{id_val}_{sec_val}_{th_val}")]
        ])
        return await message.reply_text(
            text=f"**Website Link:**\n`{encoded_website_url}`\n\n"
                 f"**Direct Stream Links (if available):**\n{direct_stream_text}",
            reply_markup=rm,
            parse_mode=enums.ParseMode.MARKDOWN
        )

    params = {'u': message.from_user.id, 'w': str(id_val), 's': str(sec_val), 't': str(th_val)}
    url1 = f"{urlencode(params)}"
    link = await encode(url1)
    encoded_website_url = f"{LINK_URL}?Tech_VJ={link}"

    direct_stream_urls = []
    if id_val != "0":
        direct_stream_urls.append(f"480p: https://your_direct_stream_domain.com/stream/{id_val}")
    if sec_val != "0":
        direct_stream_urls.append(f"720p: https://your_direct_stream_domain.com/stream/{sec_val}")
    if th_val != "0":
        direct_stream_urls.append(f"1080p: https://your_direct_stream_domain.com/stream/{th_val}")
    
    direct_stream_text = "\n".join([f"`{url}`" for url in direct_stream_urls]) if direct_stream_urls else "No direct stream URLs available."

    rm = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥️ Open Website Link", url=encoded_website_url)],
        [InlineKeyboardButton("🔗 Copy Direct Stream Links", callback_data=f"copy_multi_direct_stream_{id_val}_{sec_val}_{th_val}")]
    ])
    await message.reply_text(
        text=f"**Website Link:**\n`{encoded_website_url}`\n\n"
             f"**Direct Stream Links (if available):**\n{direct_stream_text}",
        reply_markup=rm,
        parse_mode=enums.ParseMode.MARKDOWN
    )

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
    if not link_clicks or link_clicks < 1000:
        return await message.reply("You Are Not Eligible For Withdrawal.\nMinimum Withraw Is 1000 Link Clicks or Video Plays.")
    
    confirm = await client.ask(message.from_user.id, "You Are Going To Withdraw All Your Link Clicks. Are You Sure You Want To Withdraw ?\nSend /yes or /no")
    if confirm.text == "/no":
        return await message.reply("Withdraw Cancelled By You ❌")
    elif confirm.text == "/yes":
        pay_method_msg = await client.ask(message.from_user.id, "Now Choose Your Payment Method, Click On In Which You Want Your Withdrawal.\n\n/upi - for upi, webmoney, airtm, capitalist\n\n/bank - for bank only")
        payment_details = ""
        
        if pay_method_msg.text == "/upi":
            upi_details = await client.ask(message.from_user.id, "Now Send Me Your Upi Or Upi Number With Your Name, Make Sure Name Matches With Your Upi Account")
            if not upi_details.text:
                return await message.reply("Wrong Input ❌")
            payment_details = f"Upi - {upi_details.text}"
            try:
                await upi_details.delete()
            except Exception:
                pass # Ignore if message already deleted
        elif pay_method_msg.text == "/bank":
            name = await client.ask(message.from_user.id, "Now Send Me Your Account Holder Full Name")
            if not name.text:
                return await message.reply("Wrong Input ❌")
            number = await client.ask(message.from_user.id, "Now Send Me Your Account Number")
            if not number.text.isdigit():
                return await message.reply("Wrong Input ❌")
            ifsc = await client.ask(message.from_user.id, "Now Send Me Your IFSC Code.")
            if not ifsc.text:
                return await message.reply("Wrong Input ❌")
            bank_name = await client.ask(message.from_user.id, "Now Send You Can Send Necessary Thing In One Message, Like Send Bank Name, Or Contact Details.")
            if not bank_name.text:
                return await message.reply("Wrong Input ❌")
            payment_details = (f"Account Holder Name - {name.text}\n\n"
                               f"Account Number - {number.text}\n\n"
                               f"IFSC Code - {ifsc.text}\n\n"
                               f"Bank Name - {bank_name.text}\n\n")
            try:
                await name.delete()
                await number.delete()
                await ifsc.delete()
                await bank_name.delete()
            except Exception:
                pass # Ignore if message already deleted
        else:
            return await message.reply("Invalid payment method. Please send /upi or /bank.")
            
        traffic = await client.ask(message.from_user.id, "Now Send Me Your Traffic Source Link, If Your Link Click Are Fake Then You Will Not Receive Payment And Withdrawal Get Cancelled")
        if not traffic.text:
            return await message.reply("Wrong Traffic Source ❌")
        
        balance = link_clicks / 1000.0
        formatted_balance = f"{balance:.2f}"
        text = f"Api Key - {message.from_user.id}\n\n"
        text += f"Video Plays - {link_clicks}\n\n"
        text += f"Balance - ${formatted_balance}\n\n"
        text += payment_details
        text += f"Traffic Link - {traffic.text}"
        
        await client.send_message(ADMIN, text)
        record_withdraw(message.from_user.id, True)
        await message.reply(f"Your Withdrawal Balance - ${formatted_balance}\n\nNow Your Withdrawal Send To Owner, If Everything Fulfills The Criteria Then You Will Get Your Payment Within 3 Working Days.")
    else:
        return await message.reply("Invalid input for withdrawal confirmation. Please send /yes or /no.")

@Client.on_message(filters.private & filters.command("notify") & filters.chat(ADMIN))
async def show_notify(client, message):
    count = int(1)
    user_id_msg = await client.ask(message.from_user.id, "Now Send Me Api Key Of User")
    if user_id_msg.text and user_id_msg.text.isdigit():
        user_api_key = int(user_id_msg.text)
        sub_msg = await client.ask(message.from_user.id, "Payment Is Cancelled Or Send Successfully. /send or /cancel")
        if sub_msg.text == "/send":
            record_visits(user_api_key, count) # This seems to add visits, which might be incorrect for a payout notification. Recheck desired behavior.
            record_withdraw(user_api_key, False)
            await client.send_message(user_api_key, "Your Withdrawal Is Successfully Completed And Sended To Your Bank Account.")
            await message.reply("Successfully Message Send.")
        elif sub_msg.text == "/cancel":
            reason_msg = await client.ask(message.from_user.id, "Send Me The Reason For Cancellation Of Payment")
            if reason_msg.text:
                record_visits(user_api_key, count) # Same as above, reconsider this logic for cancellation.
                record_withdraw(user_api_key, False)
                await client.send_message(user_api_key, f"Your Payment Cancelled - {reason_msg.text}")
                await message.reply("Successfully Message Send.")
            else:
                await message.reply("Reason cannot be empty. Process cancelled.")
        else:
            await message.reply("Invalid option. Please send /send or /cancel.")
    else:
        await message.reply("Invalid User API Key. Please send a valid number.")
