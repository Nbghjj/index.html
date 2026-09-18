import time
import random
import threading
import os
import asyncio
import sqlite3
from flask import Flask, render_template, request, jsonify
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)

STAKE_PRICE = 10
MAX_CARDS_PER_USER = 4   # አንዱ ተጫዋች መያዝ የሚችለው ከፍተኛ የካርድ ብዛት

# ያስገቡት ትክክለኛ የቦት ቶከን
BOT_TOKEN = "8909328591:AAEay418mvQF9dRBqjtSKgPDM_T-WpWWJ84" 
WEB_APP_URL = "https://ayat-bingo-bot.onrender.com/" # የ Render ሊንክዎ

# ዳታቤዝ ማዋቀሪያ (ቦቱ እና ሚኒ አፑ አንድ አይነት ዳታቤዝ እንዲጠቀሙ)
def init_db():
    conn = sqlite3.connect('bot_users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            phone TEXT,
            balance REAL DEFAULT 100.0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

taken_cards = {}   # {card_id: user_id}
game_state = {
    "status": "waiting",  # waiting, countdown, playing
    "countdown_end": 0,
    "playing_end": 0,
    "taken_cards": taken_cards,
    "winner": None,
    "winning_card": None,
    "current_called_number": None,
    "called_numbers_history": []
}

def generate_unique_bingo_cards(total_cards=300):
    """300 ፍጹም የተለያዩ እና የማይመሳሰሉ የቢንጎ ካርዶችን የሚያመነጭ ሎጂክ"""
    all_cards = {}
    seen_cards = set()
    
    card_id = 1
    while card_id <= total_cards:
        b_col = tuple(sorted(random.sample(range(1, 16), 5)))
        i_col = tuple(sorted(random.sample(range(16, 31), 5)))
        n_col = tuple(sorted(random.sample(range(31, 46), 4)))  # መሀል ላይ Free
        g_col = tuple(sorted(random.sample(range(46, 61), 5)))
        o_col = tuple(sorted(random.sample(range(61, 76), 5)))
        
        card_matrix = (b_col, i_col, n_col, g_col, o_col)
        
        if card_matrix not in seen_cards:
            seen_cards.add(card_matrix)
            all_cards[str(card_id)] = {
                "B": list(b_col),
                "I": list(i_col),
                "N": list(n_col),
                "G": list(g_col),
                "O": list(o_col)
            }
            card_id += 1
            
    return all_cards

BINGO_CARDS = generate_unique_bingo_cards(300)

# ================= ቴሌግራም ቦት ክፍሎች (Telegram Bot Handlers) =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    
    # 1. /start ሲሉ ዩዘሩን በዳታቤዝ መመዝገብ
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT telegram_id FROM users WHERE telegram_id = ?', (user_id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (telegram_id, username, balance) VALUES (?, ?, ?)',
                       (user_id, username, 100.0))
        conn.commit()
    conn.close()
    
    # 2. ስልክ ቁጥር ማጋሪያ ቁልፍ ማምጣት
    contact_button = KeyboardButton("📱 ቁጥሬን አጋራ (Share Contact)", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"ሰላም <b>{user.first_name}</b>! እንኳን ወደ 'Ayat Bingo' በደህና መጡ።\n\n"
        "ጨዋታውን ለመጀመር እና ለመመዝገብ እባክዎ ከታች ያለውን በመንካት ስልክ ቁጥርዎን ያጋሩ።",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    phone = update.message.contact.phone_number
    
    # 3. ስልክ ቁጥር ሲያጋራ ዳታቤዝ ማዘመን
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET phone = ? WHERE telegram_id = ?', (phone, user_id))
    conn.commit()
    conn.close()
    
    # 4. ሚኒ አፕ መክፈቻ ቁልፍ ማሳየት
    keyboard = [[InlineKeyboardButton("🎮 Play Ayat Bingo Mini App", web_app=WebAppInfo(url=WEB_APP_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ ምዝገባዎ እና ስልክ ቁጥርዎ በተሳካ ሁኔታ ተመዝግቧል!\n\n"
        "አሁን ጨዋታውን ለመጀመር ከታች ያለውን ቁልፍ ይጫኑ:",
        reply_markup=reply_markup
    )

# ================= FLASK API ROUTES =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/auth_user', methods=['POST'])
def auth_user():
    data = request.json or {}
    user_id = str(data.get('user_id') or "123456")
    
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row:
        balance = row[0]
    else:
        balance = 100.0
        cursor.execute('INSERT OR IGNORE INTO users (telegram_id, balance) VALUES (?, ?)', (user_id, balance))
        conn.commit()
    conn.close()
    
    return jsonify({"success": True, "balance": balance})

@app.route('/api/get_cards', methods=['GET'])
def get_cards():
    return jsonify({"success": True, "cards": BINGO_CARDS})

@app.route('/api/get_state', methods=['GET'])
def get_state():
    global game_state
    now = time.time()
    
    if len(taken_cards) > 0:
        if game_state["status"] == "waiting":
            game_state["status"] = "countdown"
            game_state["countdown_end"] = now + 45
            game_state["winner"] = None
            game_state["winning_card"] = None
        elif game_state["status"] == "countdown":
            if now >= game_state["countdown_end"]:
                game_state["status"] = "playing"
                game_state["playing_end"] = now + 180
                game_state["called_numbers_history"] = []
                game_state["current_called_number"] = None
    else:
        game_state["status"] = "waiting"
        game_state["countdown_end"] = 0
        game_state["winner"] = None
        game_state["winning_card"] = None

    if game_state["status"] == "playing":
        if now >= game_state["playing_end"]:
            game_state["status"] = "waiting"
            game_state["countdown_end"] = 0
            game_state["winner"] = None
            game_state["winning_card"] = None
            taken_cards.clear()
        else:
            if not hasattr(app, 'last_call_time') or now - app.last_call_time >= 3:
                app.last_call_time = now
                all_nums = list(range(1, 76))
                remaining = [n for n in all_nums if n not in game_state["called_numbers_history"]]
                if remaining:
                    called = random.choice(remaining)
                    game_state["called_numbers_history"].append(called)
                    game_state["current_called_number"] = called

    timer_val = 45
    if game_state["status"] == "countdown":
        timer_val = max(0, int(game_state["countdown_end"] - now))
    elif game_state["status"] == "playing":
        timer_val = max(0, int(game_state["playing_end"] - now))

    active_players = len(set(taken_cards.values()))
    total_cards_count = len(taken_cards)
    prize_pool = total_cards_count * STAKE_PRICE

    return jsonify({
        "status": game_state["status"],
        "timer": timer_val,
        "taken_cards": taken_cards,
        "winner": game_state.get("winner"),
        "winning_card": game_state.get("winning_card"),
        "current_called_number": game_state.get("current_called_number"),
        "active_players_count": active_players,
        "total_cards_count": total_cards_count,
        "prize_pool": prize_pool
    })

@app.route('/api/get_balance', methods=['POST'])
def get_balance():
    data = request.json or {}
    user_id = str(data.get('user_id') or "123456")
    
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    balance = row[0] if row else 100.0
    return jsonify({"success": True, "balance": balance})

@app.route('/api/lock_card', methods=['POST'])
def lock_card():
    global game_state
    now = time.time()
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id') or "123456")

    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 100.0

    if game_state["status"] == "playing":
        conn.close()
        return jsonify({"success": False, "message": "ጨዋታው ተጀምሯል! አሁን ካርድ መያዝ አይቻልም።"}), 400

    if card_id in taken_cards and taken_cards[card_id] != user_id:
        conn.close()
        return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400

    if card_id in taken_cards and taken_cards[card_id] == user_id:
        conn.close()
        return jsonify({"success": True, "new_balance": balance})

    user_cards_count = sum(1 for uid in taken_cards.values() if uid == user_id)
    if user_cards_count >= MAX_CARDS_PER_USER:
        conn.close()
        return jsonify({"success": False, "message": f"ከፍተኛው የካርድ ገደብ ደርሰዋል!"}), 400

    if balance < STAKE_PRICE:
        conn.close()
        return jsonify({"success": False, "message": "በቂ ሂሳብ የሎትም!"}), 400

    balance -= STAKE_PRICE
    cursor.execute('UPDATE users SET balance = ? WHERE telegram_id = ?', (balance, user_id))
    conn.commit()
    conn.close()

    taken_cards[card_id] = user_id

    if game_state["status"] == "waiting":
        game_state["status"] = "countdown"
        game_state["countdown_end"] = now + 45

    return jsonify({"success": True, "new_balance": balance})

@app.route('/api/unlock_card', methods=['POST'])
def unlock_card():
    global game_state
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id') or "123456")

    if game_state["status"] == "playing":
        return jsonify({"success": False, "message": "ጨዋታው በሂደት ላይ ስለሆነ ካርዱ ሊለቀቅ አይችልም።"}), 400

    if card_id in taken_cards and taken_cards[card_id] == user_id:
        del taken_cards[card_id]
        
        conn = sqlite3.connect('bot_users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (user_id,))
        row = cursor.fetchone()
        balance = (row[0] if row else 100.0) + STAKE_PRICE
        cursor.execute('UPDATE users SET balance = ? WHERE telegram_id = ?', (balance, user_id))
        conn.commit()
        conn.close()
        
        if len(taken_cards) == 0:
            game_state["status"] = "waiting"
            game_state["countdown_end"] = 0

        return jsonify({"success": True, "new_balance": balance})

    return jsonify({"success": False, "message": "አልተያዘም"}), 400

@app.route('/api/bingo_win', methods=['POST'])
def bingo_win():
    global game_state
    data = request.json or {}
    user_id = str(data.get('user_id') or "123456")
    winning_card = str(data.get('card_id') or "1")
    
    total_pool = len(taken_cards) * STAKE_PRICE
    prize = int(total_pool * 0.9)
    if prize < STAKE_PRICE:
        prize = STAKE_PRICE * 2
        
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (user_id,))
    row = cursor.fetchone()
    balance = (row[0] if row else 100.0) + prize
    cursor.execute('UPDATE users SET balance = ? WHERE telegram_id = ?', (balance, user_id))
    conn.commit()
    conn.close()
    
    game_state["status"] = "waiting"
    game_state["countdown_end"] = 0
    game_state["winner"] = user_id
    game_state["winning_card"] = winning_card
    taken_cards.clear()
    
    return jsonify({
        "success": True, 
        "message": f"እንኳን ደስ አለዎት! አሸንፈዋል!",
        "new_balance": balance
    })

def run_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    
    print("Telegram Bot polling started successfully...")
    app_bot.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)
            threaded=True, debug=False)
