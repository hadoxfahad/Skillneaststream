Ye Mera tg file to stream bot hai isme mujhe firebase add krdo  fr commands du toh wo mere website me jo categorys hai unka name de button kisi category pr tap kru toh course jo hai wo show kre courses pr tap kru toh sare module a gai set module command du wo module set ho gai fr me jo bhi videos du bot ko wo direct stream url de sath me name bhi de aur niche download button add kre add lecture add resource ksis pr tap kre toh wo firebase me lecture me link daal gai website me stream url add ho gai player me chlne lg gai aur ek button add kro select krne ka agar direct stream url select krke bhot sare add kru toh wo bhi ho gai

Firebase keys
// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
apiKey: "AIzaSyChwpbFb6M4HtG6zwjg0AXh7Lz9KjnrGZk",
authDomain: "adminneast.firebaseapp.com",
databaseURL: "https://adminneast-default-rtdb.firebaseio.com",
projectId: "adminneast",
storageBucket: "adminneast.firebasestorage.app",
messagingSenderId: "883877553418",
appId: "1:883877553418:web:84ce8200f4b471bfffc6f3",
measurementId: "G-PCH99BDF1S"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

Bot.py

Don't Remove Credit @VJ_Botz
Subscribe YouTube Channel For Amazing Bot @Tech_VJ
Ask Doubt on telegram @KingVJ01

import sys, glob, importlib, logging, logging.config, pytz, asyncio
from pathlib import Path

Get logging configurations

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)
logging.basicConfig(
level=logging.INFO,
format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

from pyrogram import Client, idle
from info import *
from typing import Union, Optional, AsyncGenerator
from Script import script
from datetime import date, datetime
from aiohttp import web
from plugins import web_server

from TechVJ.bot import TechVJBot, TechVJBackUpBot
from TechVJ.util.keepalive import ping_server
from TechVJ.bot.clients import initialize_clients

ppath = "plugins/*.py"
files = glob.glob(ppath)
TechVJBot.start()
TechVJBackUpBot.start()
loop = asyncio.get_event_loop()

async def start():
print('\n')
print('Initalizing Your Bot')
bot_info = await TechVJBot.get_me()
await initialize_clients()
for name in files:
with open(name) as a:
patt = Path(a.name)
plugin_name = patt.stem.replace(".py", "")
plugins_dir = Path(f"plugins/{plugin_name}.py")
import_path = "plugins.{}".format(plugin_name)
spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
load = importlib.util.module_from_spec(spec)
spec.loader.exec_module(load)
sys.modules["plugins." + plugin_name] = load
print("Tech VJ Imported => " + plugin_name)
if ON_HEROKU:
asyncio.create_task(ping_server())
me = await TechVJBot.get_me()
tz = pytz.timezone('Asia/Kolkata')
today = date.today()
now = datetime.now(tz)
time = now.strftime("%H:%M:%S %p")
await TechVJBot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time))
app = web.AppRunner(await web_server())
await app.setup()
bind_address = "0.0.0.0"
await web.TCPSite(app, bind_address, PORT).start()
await idle()

if name == 'main':
try:
loop.run_until_complete(start())
except KeyboardInterrupt:
logging.info('Service Stopped Bye 👋')
