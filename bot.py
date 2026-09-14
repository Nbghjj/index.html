import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot import types

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------
BOT_TOKEN = "8909328591:AAEay418mvQF9dRBqjtSKgPDM_T-WpWWJ84"
ADMIN_CHAT_ID = "6496982318"

app = Flask(__name__)
CORS(app)  # Cross-Origin Resource Sharing ለ Mini App ይፈቅዳል

bot = telebot.TeleBot(BOT_TOKEN)

# የተመዘገቡ ተጠቃሚዎችን በሜሞሪ መያዣ (ምርት ላይ Database መጠቀም ይመረጣል)
registered_users = set()

# --------------------------------------------------
# TELEGRAM BOT HANDLERS
# --------------------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_btn = types.KeyboardButton(text="📱 Share Contact", request_contact=True)
    markup.add(contact_btn)
    
    msg_text = (
        "እንኳን ደህና መጡ ወደ Ayat Bingo!\n\n"
        "⚠️ Bot-ን እና Mini App-ን ለመጠቀም መጀመሪያ Register ማድረግ አለብዎት።\n"
        "እባክዎ ከታች ያለውን '📱 Share Contact' የሚለውን አዝራር ይጫኑ።"
    )
    bot.send_message(message.chat.id, msg_text, reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.contact is not None:
        user_id = str(message.from_user.id)
        phone_number = message.contact.phone_number
        first_name = message.from_user.first_name or ""
        
        # ተጠቃሚውን እንደተመዘገበ መመዝገብ
        registered_users.add(user_id)
        
        # ለአድሚን ማሳወቂያ መላክ
        admin_msg = (
            f"👤 *አዲስ ስልክ ቁጥር ተላከ*\n\n"
            f"• ስም: {first_name}\n"
            f"• ስልክ: `{phone_number}`\n"
            f"• Telegram ID: `{user_id}`"
        )
        bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode='Markdown')
        
        # ለተጠቃሚው ማረጋገጫ መላክ
        bot.send_message(
            message.chat.id, 
            "✅ ምዝገባዎ ተጠናቋል! አሁን ከታች ያለውን 'Play Bingo' በመጫን መጫወት ይችላሉ።",
            reply_markup=types.ReplyKeyboardRemove()
        )

# --------------------------------------------------
# API ENDPOINT FOR MINI APP VERIFICATION
# --------------------------------------------------
@app.route('/api/check-registration', methods=['POST'])
def check_registration():
    try:
        data = request.get_json()
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

if __name__ == '__main__':
    # Render PORT Environment Variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
