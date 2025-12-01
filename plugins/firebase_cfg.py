import pyrebase

# Aapka diya hua config
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

# Session store karne ke liye (Taaki bot ko yaad rahe kis user ne konsa module select kiya hai)
user_sessions = {}
