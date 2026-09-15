# ሰዓቱን በየሰከንዱ የሚያስኬደው እና ቆጠራውን የሚያስተካክለው ሉፕ
def game_timer_loop():
    while True:
        time.sleep(1)
        
        if game_state["status"] == "countdown":
            if len(taken_cards) == 0:
                game_state["status"] = "waiting"
                game_state["timer"] = 45
            elif game_state["timer"] > 1:
                game_state["timer"] -= 1
            else:
                game_state["timer"] = 0
                game_state["status"] = "playing"

        elif game_state["status"] == "playing":
            time.sleep(15)
            game_state["status"] = "waiting"
            game_state["timer"] = 45
            taken_cards.clear()

@app.route('/api/lock_card', methods=['POST'])
def lock_card():
    global game_state
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

    # 💡 ዋናው ማስተካከያ: ማንኛውም ካርድ ሲያዝ (ቁጥሩ ከ 0 በላይ ሲሆን) 
    # ጨዋታው waiting ላይ ከሆነ ወዲያውኑ ወደ countdown እንዲቀየር ይደረጋል
    if len(taken_cards) > 0 and game_state["status"] != "playing":
        game_state["status"] = "countdown"
        # የመጀመሪያው ካርድ ሲያዝ ሰዓቱ ከ 45 እንዲጀምር (አልፎ አልፎ ካልተቀየረ)
        if game_state["timer"] <= 0 or game_state["timer"] > 45:
            game_state["timer"] = 45

    return jsonify({"success": True, "new_balance": user_balances[user_id]})
