import time
import random
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
    "winner": None,
    "winning_card": None,
    "current_called_number": None,
    "called_numbers_history": []
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
            game_state["countdown_end"] = now + 45  # 45 ሰከንድ ቆጠራ
            game_state["winner"] = None
            game_state["winning_card"] = None
        elif game_state["status"] == "countdown":
            if now >= game_state["countdown_end"]:
                game_state["status"] = "playing"
                game_state["playing_end"] = now + 180  # 3 ደቂቃ ጨዋታ
                game_state["called_numbers_history"] = []
                game_state["current_called_number"] = None
    else:
        game_state["status"] = "waiting"
        game_state["countdown_end"] = 0
        game_state["winner"] = None
        game_state["winning_card"] = None

    if game_state["status"] == "playing":
        if now >= game_state["playing_end"]:
            # ሰዓቱ ካለቀ ጨዋታው ሪሴት ይደረጋል
            game_state["status"] = "waiting"
            game_state["countdown_end"] = 0
            game_state["winner"] = None
            game_state["winning_card"] = None
            taken_cards.clear()
        else:
            # በየጥቂት ሰኮንድ ውስጥ አዲስ ቁጥር ከ 1 እስከ 75 ማመንጨት
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

    return jsonify({
        "status": game_state["status"],
        "timer": timer_val,
        "taken_cards": taken_cards,
        "winner": game_state.get("winner"),
        "winning_card": game_state.get("winning_card"),
        "current_called_number": game_state.get("current_called_number")
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

    # ጨዋታው በመጫወት ላይ (playing) ከሆነ አዲስ ካርድ መያዝ አይቻልም
    if game_state["status"] == "playing":
        return jsonify({"success": False, "message": "ጨዋታው ተጀምሯል! አሁን ካርድ መያዝ አይቻልም።"}), 400

    # ካርዱ በሌላ ተጫዋች የተያዘ መሆኑን ማረጋገጥ
    if card_id in taken_cards and taken_cards[card_id] != user_id:
        return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400

    # ተጠቃሚው አስቀድሞ ይህንን ካርድ የያዘው ከሆነ
    if card_id in taken_cards and taken_cards[card_id] == user_id:
        return jsonify({"success": True, "new_balance": user_balances[user_id]})

    # ተጠቃሚው የያዛቸውን ካርዶች ብዛት እንቆጥራለን (እስከ 4 ካርዶች ብቻ እንዲሆን)
    user_current_cards = [cid for cid, uid in taken_cards.items() if uid == user_id]
    if len(user_current_cards) >= 4:
        return jsonify({"success": False, "message": "እስከ 4 ካርዶች ብቻ መያዝ ይቻላል!"}), 400

    # በቂ ሂሳብ መኖሩን ማረጋገጥ
    if user_balances[user_id] < STAKE_PRICE:
        return jsonify({"success": False, "message": "በቂ ሂሳብ የሎትም!"}), 400

    # የካርድ ዋጋ መቀነስ እና ካርዱን መያዝ
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

    if game_state["status"] == "playing":
        return jsonify({"success": False, "message": "ጨዋታው በሂደት ላይ ስለሆነ ካርዱ ሊለቀቅ አይችልም፤ ነገር ግን ወደ መነሻ መመለስ ይችላሉ።"}), 400

    if card_id in taken_cards and taken_cards[card_id] == user_id:
        del taken_cards[card_id]
        # በቆጠራ ሰዓት (countdown) ላይ ከሆነ ገንዘቡ ተመላሽ ይደረጋል
        user_balances[user_id] += STAKE_PRICE
        
        if len(taken_cards) == 0:
            game_state["status"] = "waiting"
            game_state["countdown_end"] = 0

        return jsonify({"success": True, "new_balance": user_balances[user_id]})

    return jsonify({"success": False, "message": "አልተያዘም"}), 400

@app.route('/api/bingo_win', methods=['POST'])
def bingo_win():
    global game_state
    data = request.json or {}
    user_id = str(data.get('user_id') or "default_user")
    winning_card = str(data.get('card_id') or "1")
    
    # ካርዱ በእርግጥ በዛው ተጫዋች የተያዘ መሆኑን ማረጋገጥ
    if taken_cards.get(winning_card) != user_id:
        return jsonify({"success": False, "message": "ይህ ካርድ የእርስዎ አይደለም!"}), 400

    total_pool = len(taken_cards) * STAKE_PRICE
    prize = int(total_pool * 0.9)
    if prize < STAKE_PRICE:
        prize = STAKE_PRICE * 2
        
    if user_id not in user_balances:
        user_balances[user_id] = 100
    user_balances[user_id] += prize
    
    game_state["status"] = "waiting"
    game_state["countdown_end"] = 0
    game_state["winner"] = user_id
    game_state["winning_card"] = winning_card
    taken_cards.clear()
    
    return jsonify({
        "success": True, 
        "message": f"እንኳን ደስ አለዎት! በካርድ ቁጥር {winning_card} አሸንፈዋል! {prize} ብር ተሸልመዋል!",
        "new_balance": user_balances[user_id]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
