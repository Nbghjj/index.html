@app.route('/api/lock_card', methods=['POST'])
def lock_card():
    global game_state
    now = time.time()
    data = request.json or {}
    card_id = str(data.get('card_id'))
    user_id = data.get('user_id')
    
    if not user_id or user_id.startswith("user_"):
        user_id = "default_user"

    if user_id not in user_balances:
        user_balances[user_id] = 100

    if game_state["status"] == "playing":
        return jsonify({"success": False, "message": "ጨዋታው ተጀምሯል!"}), 400

    if card_id in taken_cards and taken_cards[card_id] != user_id:
        return jsonify({"success": False, "message": "ይህ ካርድ በሌላ ተጫዋች ተይዟል!"}), 400

    # ተጠቃሚው ከዚህ በፊት የያዘው ሌላ ካርድ ካለ እንፈልጋለን
    existing_card = None
    for cid, uid in list(taken_cards.items()):
        if uid == user_id:
            existing_card = cid
            break
    
    # አስቀድሞ የያዘውን ካርድ ዳግም ከነካው ምንም አናደርግም
    if existing_card == card_id:
        return jsonify({"success": True, "new_balance": user_balances[user_id]})

    # ሌላ ካርድ ከያዘ, የድሮውን እንለቅዋለን (ለማቀያየር ተጨማሪ ብር እንዳይቀንስ)
    if existing_card:
        del taken_cards[existing_card]
    else:
        # አዲስ ካርድ ሲይዝ ብቻ ሂሳብ እናስከፍላለን
        if user_balances[user_id] < STAKE_PRICE:
            return jsonify({"success": False, "message": "በቂ ሂሳብ የሎትም!"}), 400
        user_balances[user_id] -= STAKE_PRICE

    # አዲሱን ካርድ ለዚህ ዩዘር እንይዛለን
    taken_cards[card_id] = user_id

    if game_state["status"] == "waiting":
        game_state["status"] = "countdown"
        game_state["countdown_end"] = now + 45

    return jsonify({"success": True, "new_balance": user_balances[user_id]})
