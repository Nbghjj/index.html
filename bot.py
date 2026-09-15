import queue
from flask import Flask, render_template, Response, request, jsonify

# 1. መጀመሪያ Flask app ይፈጠራል
app = Flask(__name__)

# 2. ለ SSE ዝመናዎች የሚሆን Queue መግለጫ
q = queue.Queue()

# ለካርድ መቆለፍ/ማስመር መረጃ መያዣ
locked_cards = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def stream():
    def event_stream():
        while True:
            try:
                # ለ 20 ሰከንድ ዳታ ካላገኘ እራሱን ያድሳል (Timeout እንዳይሆን)
                data = q.get(timeout=20)
                yield f"data: {data}\n\n"
            except:
                # በየ 20 ሰከንዱ Ping ይልካል (ለእረፍት እንዳይዘጋ)
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

@app.route('/api/lock_card', methods=['POST'])
def lock_card():
    data = request.json or {}
    card_id = data.get('card_id')
    user_id = data.get('user_id')
    
    if card_id:
        locked_cards[card_id] = user_id
        # ለሁሉም ተጫዋቾች ካርዱ መቆለፉን በ SSE ይልካል
        q.put(f'{{"action": "lock", "card_id": "{card_id}", "user_id": "{user_id}"}}')
        return jsonify({"status": "success", "locked_cards": locked_cards})
    
    return jsonify({"status": "error", "message": "Invalid card_id"}), 400

@app.route('/api/unlock_card', methods=['POST'])
def unlock_card():
    data = request.json or {}
    card_id = data.get('card_id')
    
    if card_id in locked_cards:
        del locked_cards[card_id]
        # ካርዱ መከፈቱን ለሁሉም ተጫዋቾች ይልካል
        q.put(f'{{"action": "unlock", "card_id": "{card_id}"}}')
        return jsonify({"status": "success", "locked_cards": locked_cards})
    
    return jsonify({"status": "error", "message": "Card not locked"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
