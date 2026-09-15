import time
import threading
import random
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

# Game Configuration & State
CARD_PRICE = 10 
game_status = "waiting"  # waiting, countdown, playing, ended
timer_countdown = 45     # countdown seconds
current_called_number = None
current_winner = None
winning_card_id = None

# Mappings & Storage
taken_cards_map = {}  # {card_id: user_id}
user_balances = {}    # {user_id: balance}
called_numbers_pool = []

# Lock for thread safety
game_lock = threading.Lock()

def reset_game():
    global game_status, timer_countdown, current_called_number, current_winner, winning_card_id, taken_cards_map, called_numbers_pool
    with game_lock:
        game_status = "waiting"
        timer_countdown = 45
        current_called_number = None
        current_winner = None
        winning_card_id = None
        taken_cards_map.clear()
        called_numbers_pool = list(range(1, 76))
        random.shuffle(called_numbers_pool)

# Initialize game pool on startup
called_numbers_pool = list(range(1, 76))
random.shuffle(called_numbers_pool)

def background_game_loop():
    global game_status, timer_countdown, current_called_number, current_winner, called_numbers_pool
    
    while True:
        time.sleep(1)
        with game_lock:
            if game_status == "waiting":
                if len(taken_cards_map) > 0:
                    game_status = "countdown"
                    timer_countdown = 15
            elif game_status == "countdown":
                timer_countdown -= 1
                if timer_countdown <= 0 or len(taken_cards_map) == 0:
                    if len(taken_cards_map) > 0:
                        game_status = "playing"
                        timer_countdown = 0
                    else:
                        game_status = "waiting"
                        timer_countdown = 45
            elif game_status == "playing":
                # Numbers calling simulation during gameplay
                if called_numbers_pool and not current_winner:
                    if timer_countdown <= 0:
                        current_called_number = called_numbers_pool.pop(0)
                        timer_countdown = 5 # Call every 5 seconds
                    else:
                        timer_countdown -= 1

# Start background loop thread
threading.Thread(target=background_game_loop, daemon=True).start()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/get_balance', methods=['POST'])
def get_balance():
    data = request.json or {}
    user_id = str(data.get('user_id', 'default_user'))
    if user_id not in user_balances:
        user_balances[user_id] = 500.0  # ለፈተና የሚሆን የመጀመሪያ ቀሪ ሂሳብ (Bonus Balance)
    return jsonify({"balance": user_balances[user_id]})

@app.route('/api/lock_card', methods=['POST'])
def lock_card():
    global taken_cards_map, user_balances
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id'))

    with game_lock:
        if card_id in taken_cards_map:
            return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400

        if user_id not in user_balances:
            user_balances[user_id] = 500.0

        if user_balances[user_id] < CARD_PRICE:
            return jsonify({"success": False, "message": "የኪስ ቦርሳዎ በቂ ሂሳብ የለውም!"}), 400

        # Deduct price and lock card
        user_balances[user_id] -= CARD_PRICE
        taken_cards_map[card_id] = user_id

        return jsonify({"success": True, "new_balance": user_balances[user_id]})

@app.route('/api/unlock_card', methods=['POST'])
def unlock_card():
    global taken_cards_map, user_balances
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id'))

    with game_lock:
        if card_id in taken_cards_map and str(taken_cards_map[card_id]) == str(user_id):
            del taken_cards_map[card_id]
            # Refund card price
            if user_id in user_balances:
                user_balances[user_id] += CARD_PRICE
            else:
                user_balances[user_id] = CARD_PRICE + 500.0

        return jsonify({"success": True, "new_balance": user_balances.get(user_id, 500.0)})

@app.route('/api/get_state', methods=['GET'])
def get_state():
    global taken_cards_map, game_status, timer_countdown, current_called_number, current_winner, winning_card_id
    
    # 1. ንቁ ተጫዋቾች ብዛት (Active Players Count)
    active_players = len(set(taken_cards_map.values()))
    
    # 2. አጠቃላይ የተያዙ ካርዶች ብዛት (Total Cards)
    total_cards_count = len(taken_cards_map)
    
    # 3. የሽልማት መጠን (Prize Pool)
    prize_pool = total_cards_count * CARD_PRICE

    return jsonify({
        "status": game_status,
        "timer": timer_countdown,
        "taken_cards": taken_cards_map,
        "current_called_number": current_called_number,
        "winner": current_winner,
        "winning_card": winning_card_id,
        "active_players_count": active_players,
        "total_cards_count": total_cards_count,
        "prize_pool": prize_pool
    })

@app.route('/api/bingo_win', methods=['POST'])
def bingo_win():
    global current_winner, winning_card_id, game_status, user_balances, taken_cards_map
    data = request.json or {}
    user_id = str(data.get('user_id'))
    card_id = str(data.get('card_id'))

    with game_lock:
        if current_winner:
            return jsonify({"success": False, "message": "ጨዋታው አልቋል አሸናፊ ተገኝቷል!"}), 400

        total_cards_count = len(taken_cards_map)
        prize_pool = total_cards_count * CARD_PRICE

        current_winner = user_id
        winning_card_id = card_id
        game_status = "ended"

        # Award prize pool to winner's balance
        if user_id not in user_balances:
            user_balances[user_id] = 500.0
        user_balances[user_id] += prize_pool

        return jsonify({
            "success": True,
            "message": f"እንኳን ደስ አለዎት! 🏆 {prize_pool} ብር አሸንፈዋል!"
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
