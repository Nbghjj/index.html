import json
import queue
from flask import Flask, render_template, Response, request, jsonify

app = Flask(__name__)

q = queue.Queue()

# ዳታዎችን በ Memory መያዣ
user_balances = {}
taken_cards = {}
STAKE_PRICE = 10  # የአንዱ ካርድ ዋጋ

def broadcast_state():
    """ለሁሉም ተጫዋቾች የተያዙ ካርዶችን በ SSE ይልካል"""
    q.put(json.dumps({"taken_cards": taken_cards}))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def stream():
    def event_stream():
        # እንደገባ አሁን ያሉበትን የተያዙ ካርዶች ይላክለታል
        yield f"data: {json.dumps({'taken_cards': taken_cards})}\n\n"
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
    
    # አዲስ ተጫዋች ከሆነ 100 ብር የቦነስ ይሰጠዋል
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

    # ካርዱ በሌላ ሰው ከተያዘ
    if card_id in taken_cards and taken_cards[card_id] != user_id:
        return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400

    # በቂ ገንዘብ ከሌለው
    if user_balances[user_id] < STAKE_PRICE:
        return jsonify({"success": False, "message": "በቂ የኪስ ቦርሳ ሂሳብ የሎትም!"}), 400

    # ካርዱን መያዝ እና 10 ብር መቀነስ
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
        user_balances[user_id] += STAKE_PRICE  # ገንዘቡን መመለስ
        broadcast_state()
        return jsonify({"success": True, "new_balance": user_balances[user_id]})

    return jsonify({"success": False, "message": "ካርዱ አልተያዘም"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
