from flask import Flask, render_template, request, jsonify, Response
import json
import time
import queue

app = Flask(__name__)

GAME_CYCLE_SEC = 30
STAKE_AMOUNT = 10  # የአንዱ ካርድ ዋጋ 10 ብር

# በጋራ የሚያዙ መረጃዎች
taken_cards = {}   # { round_id: { card_id: user_id } }
user_wallets = {}  # { user_id: balance }
subscribers = []

def get_current_round():
    return int(time.time() // GAME_CYCLE_SEC)

def notify_all():
    """የተያዙ ካርዶችን መረጃ ለሁሉም ተጫዋቾች በ SSE መላክ"""
    round_id = get_current_round()
    cards = taken_cards.get(round_id, {})
    data = json.dumps({"round_id": round_id, "taken_cards": cards})
    
    for sub in subscribers[:]:
        try:
            sub.put(data)
        except:
            subscribers.remove(sub)

@app.route('/')
def index():
    return render_template('index.html')

# 1. SSE Endpoint (ቀጥታ የካርድ መረጃ ማሰራጫ)
@app.route('/events')
def events():
    def stream():
        q = queue.Queue()
        subscribers.append(q)
        
        round_id = get_current_round()
        initial_data = json.dumps({"round_id": round_id, "taken_cards": taken_cards.get(round_id, {})})
        yield f"data: {initial_data}\n\n"

        try:
            while True:
                data = q.get()
                yield f"data: {data}\n\n"
        except GeneratorExit:
            subscribers.remove(q)

    return Response(stream(), mimetype='text/event-stream')

# 2. የሂሳብ መጠን ማግኛ API
@app.route('/api/get_balance', methods=['POST'])
def get_balance():
    data = request.json or {}
    user_id = str(data.get('user_id', 'guest'))
    
    if user_id not in user_wallets:
        user_wallets[user_id] = 100.0  # 100 ብር ቦነስ

    return jsonify({"balance": user_wallets[user_id]})

# 3. ካርድ የመቆለፍና ሂሳብ የመቀነስ API
@app.route('/api/lock_card', methods=['POST'])
def lock_card():
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id', 'guest'))
    round_id = get_current_round()

    if user_id not in user_wallets:
        user_wallets[user_id] = 100.0

    if user_wallets[user_id] < STAKE_AMOUNT:
        return jsonify({"success": False, "message": "⚠️ በቂ ገንዘብ የለም! እባክዎ መጀመሪያ ሂሳብዎን ይሙሉ"}), 400

    if round_id not in taken_cards:
        taken_cards[round_id] = {}

    current_round_cards = taken_cards[round_id]

    if card_id in current_round_cards and current_round_cards[card_id] != user_id:
        return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400

    # ካርዱን መያዝ እና 10 ብር መቀነስ
    current_round_cards[card_id] = user_id
    user_wallets[user_id] -= STAKE_AMOUNT
    
    notify_all()
    return jsonify({"success": True, "new_balance": user_wallets[user_id]})

# 4. ካርድ የመልቀቅና ሂሳብ የመመለስ API
@app.route('/api/unlock_card', methods=['POST'])
def unlock_card():
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id', 'guest'))
    round_id = get_current_round()

    if round_id in taken_cards and card_id in taken_cards[round_id]:
        if taken_cards[round_id][card_id] == user_id:
            del taken_cards[round_id][card_id]
            user_wallets[user_id] += STAKE_AMOUNT  # 10 ብር መመለስ
            notify_all()

    return jsonify({"success": True, "new_balance": user_wallets.get(user_id, 0)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
