# plugins/start.py (केवल प्रासंगिक भाग दिखाए गए हैं)

import random
import requests
import humanize
import base64
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, CallbackQuery
from info import LOG_CHANNEL, LINK_URL, ADMIN
# यहाँ बदलाव है: 'record_visit' को 'add_or_update_visit' से बदलें
from plugins.database import checkdb, db, get_count, get_withdraw, record_withdraw, add_or_update_visit, record_visits # <- यह लाइन बदल गई है
from urllib.parse import quote_plus, urlencode
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size
from TechVJ.util.human_readable import humanbytes

# (decode and encode functions remain the same)

@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if not await checkdb.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        # ... (rest of the start command logic)
    else:
        # ... (rest of the start command logic)
        return


@Client.on_message(filters.command("update") & filters.private)
async def update(client, message):
    # ... (update command logic)
    return

@Client.on_message(filters.private & (filters.document | filters.video))
async def stream_start(client, message):
    file = getattr(message, message.media.value)
    fileid = file.file_id
    user_id = message.from_user.id
    log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
    
    # जब कोई वीडियो अपलोड करता है, तो उसके प्ले काउंट को बढ़ाएं
    add_or_update_visit(user_id, 1) # <- यहाँ 'record_visit' की जगह 'add_or_update_visit' का इस्तेमाल करें, 1 से बढ़ाना है
    
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

@Client.on_message(filters.private & filters.command("quality"))
async def quality_link(client, message):
    # ... (rest of quality_link logic) ...
    # क्वालिटी लिंक्स जनरेट होने के बाद भी, आप इसे एक 'विजिट' मान सकते हैं
    # या आप इसे तभी गिन सकते हैं जब उपयोगकर्ता वास्तव में लिंक पर क्लिक करे।
    # यहाँ मैं इसे नहीं गिन रहा हूँ, क्योंकि add_or_update_visit को stream_start और link_start में किया गया है
    # यदि आप यहाँ भी गिनना चाहते हैं, तो आपको user_id और count_increment को पास करना होगा।
    pass


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

    # जब उपयोगकर्ता किसी लिंक पर क्लिक करता है, तो उसके प्ले काउंट को बढ़ाएं
    add_or_update_visit(int(user_id), 1) # <- यहाँ भी 'record_visit' की जगह 'add_or_update_visit' का इस्तेमाल करें
    
    # ... (rest of link_start logic) ...
    return

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
        # ... (payment method selection logic) ...
            
        traffic = await client.ask(message.from_user.id, "Now Send Me Your Traffic Source Link, If Your Link Click Are Fake Then You Will Not Receive Payment And Withdrawal Get Cancelled")
        if not traffic.text:
            return await message.reply("Wrong Traffic Source ❌")
        
        balance = link_clicks / 1000.0
        formatted_balance = f"{balance:.2f}"
        text = f"Api Key - {message.from_user.id}\n\n"
        text += f"Video Plays - {link_clicks}\n\n"
        text += f"Balance - ${formatted_balance}\n\n"
        # text += payment_details # Make sure payment_details is correctly defined here
        text += f"Traffic Link - {traffic.text}"
        
        await client.send_message(ADMIN, text)
        record_withdraw(message.from_user.id, True)
        await message.reply(f"Your Withdrawal Balance - ${formatted_balance}\n\nNow Your Withdrawal Send To Owner, If Everything Fulfills The Criteria Then You Will Get Your Payment Within 3 Working Days.")
    else:
        return await message.reply("Invalid input for withdrawal confirmation. Please send /yes or /no.")

@Client.on_message(filters.private & filters.command("notify") & filters.chat(ADMIN))
async def show_notify(client, message):
    user_id_msg = await client.ask(message.from_user.id, "Now Send Me Api Key Of User")
    if user_id_msg.text and user_id_msg.text.isdigit():
        user_api_key = int(user_id_msg.text)
        sub_msg = await client.ask(message.from_user.id, "Payment Is Cancelled Or Send Successfully. /send or /cancel")
        if sub_msg.text == "/send":
            record_visits(user_api_key) # <- यहाँ 'record_visits' (जो अब reset_user_plays_and_withdraw_status है) का उपयोग करें
            await client.send_message(user_api_key, "Your Withdrawal Is Successfully Completed And Sended To Your Bank Account.")
            await message.reply("Successfully Message Send.")
        elif sub_msg.text == "/cancel":
            reason_msg = await client.ask(message.from_user.id, "Send Me The Reason For Cancellation Of Payment")
            if reason_msg.text:
                record_visits(user_api_key) # <- यहाँ भी 'record_visits' का उपयोग करें
                await client.send_message(user_api_key, f"Your Payment Cancelled - {reason_msg.text}")
                await message.reply("Successfully Message Send.")
            else:
                await message.reply("Reason cannot be empty. Process cancelled.")
        else:
            await message.reply("Invalid option. Please send /send or /cancel.")
    else:
        await message.reply("Invalid User API Key. Please send a valid number.")
