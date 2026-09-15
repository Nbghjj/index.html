import json
import time
import threading
from flask import Flask, render_template, Response, request, jsonify

app = Flask(__name__)

user_balances = {}
taken_cards = {}
STAKE_PRICE = 10

game_state = {
    "status": "waiting",
    "taken_cards": taken_cards,
    "start_countdown": False
}

clients = []

def broadcast_state():
    data = f"data: {json.dumps(game_state)}\n\n"
    for client_queue in clients[:]:
        try:
            client_queue.put(data)
        except:
            clients.remove(client_queue)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def stream():
    import queue
    q = queue.Queue()
    clients.append(q)

    def event_stream():
        yield f"data: {json.dumps(game_state)}\n\n"
        try:
            while True:
                data = q.get(timeout=20)
                yield data
        except:
            pass
        finally:
            if q in clients:
                clients.remove(q)

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
        
        # ቢያንስ 1 ካርድ ሲያዝ ቆጠራ እንዲጀምር ምልክት እናሳልፋለን
        game_state["start_countdown"] = True
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
        
        # ካርዶች ሙሉ በሙሉ ከጠፉ ቆጠራውን እናቆማለን
        if len(taken_cards) == 0:
            game_state["start_countdown"] = False
            game_state["status"] = "waiting"

        broadcast_state()
        return jsonify({"success": True, "new_balance": user_balances[user_id]})

    return jsonify({"success": False, "message": "ካርዱ አልተያዘም"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
