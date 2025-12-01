# info.py

import re
from os import environ

# Bot Session Name
SESSION = environ.get('SESSION', 'TechVJBot')

# Your Telegram Account Api Id And Api Hash
API_ID = int(environ.get('API_ID', '22177421'))
API_HASH = environ.get('API_HASH', 'e515bbf4a302d7c7335f689a52b196a5')

# Bot Token
BOT_TOKEN = environ.get('BOT_TOKEN', "")

# Admin ID (Single ID or List)
ADMIN_ENV = environ.get('ADMIN', '1865244712')
# String ko list me convert kar rahe hain taaki multiple admins bhi add ho sakein
ADMINS = [int(x) for x in ADMIN_ENV.split()]

# Back Up Bot Token
BACKUP_BOT_TOKEN = environ.get('BACKUP_BOT_TOKEN', "")

# Log Channel
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1002869695930'))

# Mongodb Database
MONGODB_URI = environ.get("MONGODB_URI", "")

# Stream Url (Render URL) - Trailing slash hata diya hai safety ke liye
STREAM_URL = environ.get("STREAM_URL", "https://skillneaststream.onrender.com").rstrip("/")

# Permanent Link
LINK_URL = environ.get("LINK_URL", "https://skillneast.blogspot.com/p/s_7.html")

# Others
PORT = environ.get("PORT", "8080")
MULTI_CLIENT = False
SLEEP_THRESHOLD = int(environ.get('SLEEP_THRESHOLD', '60'))
PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))

if 'DYNO' in environ:
    ON_HEROKU = True
else:
    ON_HEROKU = False
