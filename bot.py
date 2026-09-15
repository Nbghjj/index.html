from flask import Flask, jsonify, request

app = Flask(__name__)

# የጨዋታው ዳታዎች (Game State)
game_state = {
    "status": "waiting",  # waiting ወይም playing
    "current_called_number": None,
    "timer": 45,
    "winner": None,
    "winning_card": None,
    "taken_cards": {}  # { "1": "user_id_123", "2": "user_id_123", ... }
}

# የተጫዋቾች የኪስ ቦርሳ (Wallet) መዝገብ (ለሙከራ ያህል)
user_wallets = {}

# የአንድ ካርድ ዋጋ (ለምሳሌ 10 ብር ከሆነ 4 ካርድ ሲይዝ 40 ብር ይቀነሳል)
CARD_PRICE = 10 

@app.route('/api/get_state', methods=['GET'])
def get_state():
    return jsonify(game_state)

@app.route('/api/get_balance', methods=['POST'])
def get_balance():
    data = request.json
    user_id = str(data.get('user_id'))
    
    if user_id not in user_wallets:
        user_wallets[user_id] = 100  # አዲስ ተጫዋች ሲገባ 100 ብር ቦነስ
        
    return jsonify({"balance": user_wallets[user_id]})

@app.route('/api/lock_card', methods=['POST'])
def lock_card():
    data = request.json
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id'))
    
    if game_state["status"] != "waiting":
        return jsonify({"success": False, "message": "ጨዋታው ተጀምሯል፣ አሁን ካርድ መያዝ አይቻልም!"}), 400

    # ካርዱ አስቀድሞ በሌላ ተጫዋች ተይዞ ከሆነ
    if card_id in game_state["taken_cards"]:
        if game_state["taken_cards"][card_id] != user_id:
            return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400
        else:
            # ተጠቃሚው አስቀድሞ የያዘው ከሆነ
            return jsonify({"success": True, "new_balance": user_wallets.get(user_id, 100)})

    # ተጠቃሚው የያዛቸውን ካርዶች ብዛት እንቆጥራለን (እስከ 4 መሆኑን ለማረጋገጥ)
    user_current_cards = [cid for cid, uid in game_state["taken_cards"].items() if uid == user_id]
    if len(user_current_cards) >= 4:
        return jsonify({"success": False, "message": "እስከ 4 ካርዶች ብቻ መያዝ ይቻላል!"}), 400

    # የተጫዋቹንሂሳብ እናረጋግጥ
    if user_id not in user_wallets:
        user_wallets[user_id] = 100

    if user_wallets[user_id] < CARD_PRICE:
        return jsonify({"success": False, "message": "በቂ የኪስ ቦርሳ ሂሳብ የለዎትም!"}), 400

    # ገንዘብ መቀነስ እና ካርዱን መያዝ
    user_wallets[user_id] -= CARD_PRICE
    game_state["taken_cards"][card_id] = user_id

    return jsonify({
        "success": True, 
        "new_balance": user_wallets[user_id],
        "message": "ካርዱ በተሳካ ሁኔታ ተይዟል!"
    })

@app.route('/api/unlock_card', methods=['POST'])
def unlock_card():
    data = request.json
    card_id = str(data.get('card_id'))
    user_id = str(data.get('user_id'))

    # ጨዋታው እየተካሄደ ከሆነ ካርድ መልቀቅ አያስችለም (እስከ ጨዋታው ማጠናቀቂያ ይዞ ይቆያል)
    if game_state["status"] == "playing":
        return jsonify({"success": False, "message": "ጨዋታ በሂደት ላይ ስለሆነ ካርዱን መልቀቅ አይቻልም!"}), 400

    if card_id in game_state["taken_cards"] and game_state["taken_cards"][card_id] == user_id:
        del game_state["taken_cards"][card_id]
        # ያስያዘውን ገንዘብ መመለስ
        if user_id in user_wallets:
            user_wallets[user_id] += CARD_PRICE
        else:
            user_wallets[user_id] = 100 + CARD_PRICE

        return jsonify({
            "success": True, 
            "new_balance": user_wallets[user_id],
            "message": "ካርዱ ተለቆ ገንዘብዎ ተመልሷል!"
        })

    return jsonify({"success": False, "message": "ካርዱን ማግኘት አልተቻለም!"}), 400

@app.route('/api/bingo_win', methods=['POST'])
def bingo_win():
    data = request.json
    user_id = str(data.get('user_id'))
    card_id = str(data.get('card_id'))

    # ካርዱ በእርግጥ በዛው ተጫዋች የተያዘ መሆኑን ማረጋገጥ
    if game_state["taken_cards"].get(card_id) != user_id:
        return jsonify({"success": False, "message": "ይህ ካርድ የእርስዎ አይደለም!"}), 400

    if game_state["winner"] is not None:
        return jsonify({"success": False, "message": "ጨዋታው አልቋል፣ ሌላ አሸናፊ ተመዝግቧል!"}), 400

    # አሸናፊውን መመዝገብ
    game_state["winner"] = user_id
    game_state["winning_card"] = card_id
    game_state["status"] = "waiting" # ወደ መጠበቂያ ሁኔታ እንመልሰዋለን

    # ለምሳሌ አሸናፊውን የሽልማት ገንዘብ መስጠት (የተያዙትን አጠቃላይ ካርዶች ዋጋ አባዝቶ መስጠት ይቻላል)
    total_pot = len(game_state["taken_cards"]) * CARD_PRICE
    user_wallets[user_id] = user_wallets.get(user_id, 100) + total_pot

    # ለቀጣይ ጨዋታ የያዛቸውን ካርዶች ማጽዳት ይቻላል ወይም በድል ማጠናቀቂያ ላይ ይጸዳል
    game_state["taken_cards"] = {}

    return jsonify({
        "success": True, 
        "message": f"እንኳን ደስ አለዎት! በካርድ ቁጥር {card_id} አሸንፈዋል! ሽልማት: {total_pot} ብር"
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
