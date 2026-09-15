import json
import queue
import time
import threading
from flask import Flask, render_template, Response, request, jsonify

app = Flask(__name__)
q = queue.Queue()

user_balances = {}
taken_cards = {}
STAKE_PRICE = 10

# የጨዋታ ሁኔታዎች: 'waiting' (መምረጥ), 'countdown' (መቁጠር), 'playing' (መጫወት)
game_state = {
    "status": "waiting",
    "timer": 45,
    "taken_cards": taken_cards
}

def broadcast_state():
    q.put(json.dumps(game_state))

# 45 ሰከንድ የሚቆጥር Background Thread
def global_timer_worker():
    global game_state
    while True:
        # ቢያንስ 1 ካርድ ከተያዘ ቆጠራው ይጀምራል
        if len(taken_cards) > 0 and game_state["status"] == "waiting":
            game_state["status"] = "countdown"
            game_state["timer"] = 45
            broadcast_state()

            for i in range(45, 0, -1):
                time.sleep(1)
                # ተጫዋቾች ካርዳቸውን አጥፍተው ከወጡ ቆጠራው ይቆማል
                if len(taken_cards) == 0:
                    break
                game_state["timer"] = i - 1
                broadcast_state()

            # 45 ሰከንዱ ሲያልቅ ሁሉም ወደ ጨዋታ ይገባሉ
            if len(taken_cards) > 0:
                game_state["status"] = "playing"
                broadcast_state()
                time.sleep(10) # ጨዋታው ለአፍታ ቆይቶ ወደ መጀመሪያው ይመለሳል (ለማስተካከል)
                
            game_state["status"] = "waiting"
            taken_cards.clear()
            broadcast_state()
        else:
            time.sleep(1)

# ሰዓቱን የሚያንቀሳቅሰውን Thread ማስጀመር
threading.Thread(target=global_timer_worker, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def stream():
    def event_stream():
        yield f"data: {json.dumps(game_state)}\n\n"
        while True:
            try:
                data = q.get(timeout=20)
                yield f"data: {data}\n\n"
            except:
                yield ": keep-alive\n\n"

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

@app.route('/api/get_balance', methods=['POST'])
def get_balance():
    data = request.json or {}
    user_id = data.get('user_id')
    if user_id not in user_balances:
        user_balances[user_id] = 100
    return jsonify({"success": True, "balance": user_balances[user_id]})

@app.route('/api/lock_card', methods=['POST'])
def lock_card():
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
        return jsonify({"success": False, "message": "በቂ የኪስ ቦርሳ ሂሳብ የሎትም!"}), 400

    if card_id not in taken_cards:
        taken_cards[card_id] = user_id
        user_balances[user_id] -= STAKE_PRICE
        broadcast_state()

    return jsonify({"success": True, "new_balance": user_balances[user_id]})

@app.route('/api/unlock_card', methods=['POST'])
def unlock_card():
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = data.get('user_id')

    if card_id in taken_cards and taken_cards[card_id] == user_id:
        del taken_cards[card_id]
        user_balances[user_id] += STAKE_PRICE
        broadcast_state()
        return jsonify({"success": True, "new_balance": user_balances[user_id]})

    return jsonify({"success": False, "message": "ካርዱ አልተያዘም"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
