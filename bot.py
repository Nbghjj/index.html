import time
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

user_balances = {}
taken_cards = {}
STAKE_PRICE = 10

# በሬንደር ላይ አስተማማኝ እንዲሆን በሰዓት ማመሳከሪያ (Timestamp) የተዋቀረ
game_state = {
    "status": "waiting",  # waiting, countdown, playing
    "countdown_end": 0,
    "playing_end": 0,
    "taken_cards": taken_cards
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get_state', methods=['GET'])
def get_state():
    global game_state
    now = time.time()
    
    # በየሰከንዱ የሚመጣውን ሪኩዌስት መሰረት በማድረግ ሰዓቱንና ሁኔታውን እናመሳስላለን
    if len(taken_cards) > 0:
        if game_state["status"] == "waiting":
            game_state["status"] = "countdown"
            game_state["countdown_end"] = now + 45
        elif game_state["status"] == "countdown":
            if now >= game_state["countdown_end"]:
                game_state["status"] = "playing"
                game_state["playing_end"] = now + 15
    else:
        game_state["status"] = "waiting"
        game_state["countdown_end"] = 0

    if game_state["status"] == "playing":
        if now >= game_state["playing_end"]:
            game_state["status"] = "waiting"
            game_state["countdown_end"] = 0
            taken_cards.clear()

    # የቀረውን ሰዓት በሂሳብ እናሰላዋለን
    timer_val = 45
    if game_state["status"] == "countdown":
        timer_val = max(0, int(game_state["countdown_end"] - now))
    elif game_state["status"] == "playing":
        timer_val = max(0, int(game_state["playing_end"] - now))

    response_data = {
        "status": game_state["status"],
        "timer": timer_val,
        "taken_cards": taken_cards
    }
    return jsonify(response_data)

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
    now = time.time()
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = data.get('user_id')
    
    if user_id not in user_balances:
        user_balances[user_id] = 100

    if game_state["status"] == "playing":
        return jsonify({"success": False, "message": "ጨዋታው ተጀምሯል!"}), 400

    if card_id in taken_cards and taken_cards[card_id] != user_id:
        return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400

    if user_balances[user_id] < STAKE_PRICE:
        return jsonify({"success": False, "message": "በቂሂሳብ የሎትም!"}), 400

    if card_id not in taken_cards:
        taken_cards[card_id] = user_id
        user_balances[user_id] -= STAKE_PRICE

    if game_state["status"] == "waiting":
        game_state["status"] = "countdown"
        game_state["countdown_end"] = now + 45

    return jsonify({"success": True, "new_balance": user_balances[user_id]})

@app.route('/api/unlock_card', methods=['POST'])
def unlock_card():
    global game_state
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = data.get('user_id')

    if card_id in taken_cards and taken_cards[card_id] == user_id:
        del taken_cards[card_id]
        user_balances[user_id] += STAKE_PRICE
        
        if len(taken_cards) == 0:
            game_state["status"] = "waiting"
            game_state["countdown_end"] = 0

        return jsonify({"success": True, "new_balance": user_balances[user_id]})

    return jsonify({"success": False, "message": "አልተያዘም"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
