import time
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

user_balances = {}
taken_cards = {}
STAKE_PRICE = 10

game_state = {
    "status": "waiting",  # waiting, countdown, playing
    "countdown_end": 0,
    "playing_end": 0,
    "taken_cards": taken_cards,
    "winner": None
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_state', methods=['GET'])
def get_state():
    global game_state
    now = time.time()
    
    if len(taken_cards) > 0:
        if game_state["status"] == "waiting":
            game_state["status"] = "countdown"
            game_state["countdown_end"] = now + 45  # የቆጠራ ሰዓት (45 ሰከንድ)
        elif game_state["status"] == "countdown":
            if now >= game_state["countdown_end"]:
                game_state["status"] = "playing"
                game_state["playing_end"] = now + 180  # የጨዋታ ሰዓት (3 ደቂቃ)
    else:
        game_state["status"] = "waiting"
        game_state["countdown_end"] = 0
        game_state["winner"] = None

    if game_state["status"] == "playing":
        if now >= game_state["playing_end"]:
            # ሰዓቱ ካለቀ ጨዋታው ራሱ ሪሴት ይደረጋል
            game_state["status"] = "waiting"
            game_state["countdown_end"] = 0
            game_state["winner"] = None
            taken_cards.clear()

    timer_val = 45
    if game_state["status"] == "countdown":
        timer_val = max(0, int(game_state["countdown_end"] - now))
    elif game_state["status"] == "playing":
        timer_val = max(0, int(game_state["playing_end"] - now))

    return jsonify({
        "status": game_state["status"],
        "timer": timer_val,
        "taken_cards": taken_cards,
        "winner": game_state.get("winner")
    })

@app.route('/api/get_balance', methods=['POST'])
def get_balance():
    data = request.json or {}
    user_id = str(data.get('user_id') or "default_user")
    
    if user_id not in user_balances:
        user_balances[user_id] = 100
    return jsonify({"success": True, "balance": user_balances[user_id]})

@app.route('/api/lock_card', methods=['POST'])
def lock_card():
    global game_state
    now = time.time()
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id') or "default_user")

    if user_id not in user_balances:
        user_balances[user_id] = 100

    if game_state["status"] == "playing":
        return jsonify({"success": False, "message": "ጨዋታው ተጀምሯል!"}), 400

    if card_id in taken_cards and taken_cards[card_id] != user_id:
        return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400

    existing_card = None
    for cid, uid in list(taken_cards.items()):
        if uid == user_id:
            existing_card = cid
            break
    
    if existing_card == card_id:
        return jsonify({"success": True, "new_balance": user_balances[user_id]})

    if existing_card:
        del taken_cards[existing_card]
    else:
        if user_balances[user_id] < STAKE_PRICE:
            return jsonify({"success": False, "message": "በቂ ሂሳብ የሎትም!"}), 400
        user_balances[user_id] -= STAKE_PRICE

    taken_cards[card_id] = user_id

    if game_state["status"] == "waiting":
        game_state["status"] = "countdown"
        game_state["countdown_end"] = now + 45

    return jsonify({"success": True, "new_balance": user_balances[user_id]})

@app.route('/api/unlock_card', methods=['POST'])
def unlock_card():
    global game_state
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id') or "default_user")

    if card_id in taken_cards and taken_cards[card_id] == user_id:
        del taken_cards[card_id]
        user_balances[user_id] += STAKE_PRICE
        
        if len(taken_cards) == 0:
            game_state["status"] = "waiting"
            game_state["countdown_end"] = 0

        return jsonify({"success": True, "new_balance": user_balances[user_id]})

    return jsonify({"success": False, "message": "አልተያዘም"}), 400

# ተጫዋቹ ቢንጎ ብሎ ሲያሸንፍ የሚጠራ API
@app.route('/api/bingo_win', methods=['POST'])
def bingo_win():
    global game_state
    data = request.json or {}
    user_id = str(data.get('user_id') or "default_user")
    
    # አሸናፊውን ሽልማት እንሰላለን (ለምሳሌ የጠቅላላ stake ድምር ወይም ቋሚ ሽልማት)
    total_pool = len(taken_cards) * STAKE_PRICE
    prize = int(total_pool * 0.9)  # 10% ለሰርቨሩ ትቶ 90% ለድል አድራጊው
    if prize < STAKE_PRICE:
        prize = STAKE_PRICE * 2  # አነስተኛ ሽልማት ዋስትና
        
    if user_id not in user_balances:
        user_balances[user_id] = 100
    user_balances[user_id] += prize
    
    # ጨዋታውን ሙሉ በሙሉ እናቆማለን (Reset to Waiting)
    game_state["status"] = "waiting"
    game_state["countdown_end"] = 0
    game_state["winner"] = user_id
    taken_cards.clear()  # የነበሩትን ካርዶች በሙሉ እናጸዳለን (ሁሉም አዲስ ካርድ እንዲመርጡ)
    
    return jsonify({
        "success": True, 
        "message": f"እንኳን ደስ አለዎት! አሸንፈዋል {prize} ብር ተሸልመዋል!",
        "new_balance": user_balances[user_id]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
