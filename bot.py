import os
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot import types

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8909328591:AAEay418mvQF9dRBqjtSKgPDM_T-WpWWJ84")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6496982318")

app = Flask(__name__)
CORS(app)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# --------------------------------------------------
# PERSISTENT STORAGE
# --------------------------------------------------
DATA_FILE = "registered_users.txt"

def load_registered_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_registered_user(user_id):
    registered_users.add(str(user_id))
    with open(DATA_FILE, "a") as f:
        f.write(f"{user_id}\n")

registered_users = load_registered_users()

# --------------------------------------------------
# TELEGRAM BOT HANDLERS
# --------------------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        contact_btn = types.KeyboardButton(text="📱 Share Contact", request_contact=True)
        markup.add(contact_btn)
        
        msg_text = (
            "እንኳን ደህና መጡ ወደ Ayat Bingo!\n\n"
            "⚠️ Bot-ን እና Mini App-ን ለመጠቀም መጀመሪያ Register ማድረግ አለብዎት።\n"
            "እባክዎ ከታች ያለውን '📱 Share Contact' የሚለውን አዝራር ይጫኑ።"
        )
        bot.send_message(message.chat.id, msg_text, reply_markup=markup)
        print(f"Start command processed for chat: {message.chat.id}")
    except Exception as e:
        print(f"Error in start command: {e}")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    try:
        if message.contact is not None:
            user_id = str(message.from_user.id)
            phone_number = message.contact.phone_number
            first_name = message.from_user.first_name or ""
            
            save_registered_user(user_id)
            
            admin_msg = (
                f"👤 *አዲስ ስልክ ቁጥር ተላከ*\n\n"
                f"• ስም: {first_name}\n"
                f"• ስልክ: `{phone_number}`\n"
                f"• Telegram ID: `{user_id}`"
            )
            bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode='Markdown')
            
            bot.send_message(
                message.chat.id, 
                "✅ ምዝገባዎ ተጠናቋል! አሁን ከታች ያለውን 'Play Bingo' በመጫን መጫወት ይችላሉ።",
                reply_markup=types.ReplyKeyboardRemove()
            )
            print(f"Registered user: {user_id}")
    except Exception as e:
        print(f"Error in contact handler: {e}")

# --------------------------------------------------
# API ENDPOINT FOR MINI APP
# --------------------------------------------------
@app.route('/api/check-registration', methods=['POST'])
def check_registration():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"registered": False, "error": "No JSON data"}), 400
            
        user_id = str(data.get('user_id', ''))
        
        if user_id in registered_users:
            return jsonify({"registered": True}), 200
        else:
            return jsonify({"registered": False}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Ayat Bingo Bot Server is Running Live!"

# --------------------------------------------------
# START BOT IN BACKGROUND THREAD (Gunicorn-safe)
# --------------------------------------------------
def start_bot_polling():
    try:
        print("Removing Webhook & Starting Polling...")
        bot.remove_webhook()
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Polling error: {e}")

# Python process ሲነሳ Thread ጀምር
bot_thread = threading.Thread(target=start_bot_polling, daemon=True)
bot_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
