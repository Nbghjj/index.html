import json
import time
import threading
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

user_balances = {}
taken_cards = {}
STAKE_PRICE = 10

game_state = {
    "status": "waiting",  # waiting, countdown, playing
    "timer": 45,
    "taken_cards": taken_cards
}

timer_lock = threading.Lock()

# ቆጠራውን እና የጨዋታ ሁኔታዎችን በአስተማማኝ ሁኔታ የሚያስተዳድረው ዋና ሉፕ
def game_timer_loop():
    global game_state
    while True:
        time.sleep(1)
        with timer_lock:
            # 1. waiting ስቴት ላይ ሆኖ ካርድ ከተያዘ ቆጠራ ይጀምራል
            if game_state["status"] == "waiting" and len(taken_cards) > 0:
                game_state["status"] = "countdown"
                game_state["timer"] = 45

            # 2. countdown ስቴት ላይ ሰዓቱ ይቀንሳል
            elif game_state["status"] == "countdown":
                if len(taken_cards) == 0:
                    # ካርዶቹ ከተለቀቁ ወደ waiting ይመለሳል
                    game_state["status"] = "waiting"
                    game_state["timer"] = 45
                elif game_state["timer"] > 1:
                    game_state["timer"] -= 1
                else:
                    # ሰዓቱ 0 ሲደርስ ጨዋታው ይጀመራል
                    game_state["timer"] = 0
                    game_state["status"] = "playing"

            # 3. playing ስቴት (ለ 15 ሰከንድ ቁጥሮች ይጠራሉ)
            elif game_state["status"] == "playing":
                # ሰርቨሩ ላይ ለ 15 ሰከንድ ጨዋታውን ጠብቆ ወደ መጀመሪያው ይመለሳል
                for _ in range(15):
                    time.sleep(1)
                
                game_state["status"] = "waiting"
                game_state["timer"] = 45
                taken_cards.clear()

threading.Thread(target=game_timer_loop, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_state', methods=['GET'])
def get_state():
    with timer_lock:
        return jsonify(game_state)

@app.route('/api/get_balance', methods=['POST'])
def get_balance():
    data = request.json or {}
    user_id = data.get('user_id')
    if user_id not in user_balances:
        user_balances[user_id] = 100
    return jsonify({"success": True, "balance": user_balances[user_id]})

@app.route('/api/lock_card', methods=['POST'])
def lock_card():
    global game_state
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = data.get('user_id')
    
    if user_id not in user_balances:
        user_balances[user_id] = 100

    if game_state["status"] == "playing":
        return jsonify({"success": False, "message": "ጨዋታው ተጀምሯል! እባክዎ ቀጣዩን ዙር ይጠብቁ።"}), 400

    if card_id in taken_cards and taken_cards[card_id] != user_id:
        return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400

    if user_balances[user_id] < STAKE_PRICE:
        return jsonify({"success": False, "message": "በቂ የኪስ ቦርሳ ሂሳብ የሎትም!"}), 400

    with timer_lock:
        if card_id not in taken_cards:
            taken_cards[card_id] = user_id
            user_balances[user_id] -= STAKE_PRICE
            
            # ካርዱ ሲያዝ ቆጠራው waiting ከሆነ ወዲያውኑ ወደ countdown ይለውጠዋል
            if game_state["status"] == "waiting":
                game_state["status"] = "countdown"
                game_state["timer"] = 45

    return jsonify({"success": True, "new_balance": user_balances[user_id]})

@app.route('/api/unlock_card', methods=['POST'])
def unlock_card():
    global game_state
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = data.get('user_id')

    with timer_lock:
        if card_id in taken_cards and taken_cards[card_id] == user_id:
            del taken_cards[card_id]
            user_balances[user_id] += STAKE_PRICE
            
            if len(taken_cards) == 0 and game_state["status"] == "countdown":
                game_state["status"] = "waiting"
                game_state["timer"] = 45

            return jsonify({"success": True, "new_balance": user_balances[user_id]})

    return jsonify({"success": False, "message": "ካርዱ አልተያዘም"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
