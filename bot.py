import os
import random
import re
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, 
    CallbackQueryHandler, filters
)

# =========================
# SETTINGS & CONFIGURATION
# =========================
TOKEN = os.getenv("BOT_TOKEN", "8909328591:AAEay418mvQF9dRBqjtSKgPDM_T-WpWWJ84")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6496982318"))

# 🔗 የ Web App URL
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://nbghjj.github.io/")

# 🏦 የእርስዎ (የአድሚን) መቀበያ አካውንቶች (ለቴሌብር እና ሲቢኢ ብቻ)
ADMIN_ACCOUNTS = {
    "Telebirr": "0940483108 (kirubel melkamu)",
    "CBE": "0940483108 (kirubel melkamu)"
}

# =========================
# IN-MEMORY DATA STORE
# =========================
users = {}
pending_withdrawals = {}
pending_deposits = {}
user_states = {}  
used_transactions = set()  # 🔒 የተጠቀሙባቸውን የትራንዛክሽን 🆔ዎች ለመያዝ (Double spending መከላከያ)

# =========================
# KEYBOARDS
# =========================
def register_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Share Contact", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🎮 Play Bingo", web_app=WebAppInfo(url=WEB_APP_URL))],
            ["💰 Balance", "💵 Deposit"],
            ["💸 Withdraw", "❓ Help"]
        ],
        resize_keyboard=True,
    )

def registered(user_id):
    return user_id in users and bool(users[user_id].get("phone"))

# =========================
# USER COMMAND HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not registered(update.effective_user.id):
        await update.message.reply_text(
            "🎯 *BINGO BOT*\n\n"
            "እንኳን ደህና መጡ!\n\n"
            "Bot-ን ለመጠቀም መጀመሪያ Register ያድርጉ።\n"
            "📱 ከታች ያለውን *Share Contact* ይጫኑ።",
            parse_mode="Markdown",
            reply_markup=register_keyboard(),
        )
        return

    await update.message.reply_text(
        "✅ እንኳን ደህና መጡ!\nከታች ያለውን *🎮 Play Bingo* ተጫነው ጨዋታውን ይጀምሩ።",
        reply_markup=main_keyboard(),
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if registered(update.effective_user.id):
        await update.message.reply_text("✅ ቀድሞውኑ Registered ነዎት።", reply_markup=main_keyboard())
        return

    await update.message.reply_text(
        "📱 Registration ለመጨረስ *Share Contact* ይጫኑ።",
        parse_mode="Markdown",
        reply_markup=register_keyboard(),
    )

async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact

    if contact.user_id != user.id:
        await update.message.reply_text(
            "❌ እባክዎ የራስዎን Telegram contact ብቻ Share ያድርጉ።",
            reply_markup=register_keyboard(),
        )
        return

    users[user.id] = {
        "name": user.full_name,
        "phone": contact.phone_number,
        "balance": 0.0,
    }

    await update.message.reply_text(
        "✅ *Registration successful!*\n\n"
        f"👤 Name: {user.full_name}\n"
        f"🆔 ID: {user.id}\n"
        "📱 Contact: Verified\n\n"
        "አሁን Bot-ን መጠቀም ይችላሉ።",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not registered(uid):
        await update.message.reply_text("❌ መጀመሪያ /register ያድርጉ።", reply_markup=register_keyboard())
        return

    await update.message.reply_text(
        f"💰 Your Balance: {users[uid]['balance']:.2f} Birr",
        reply_markup=main_keyboard(),
    )

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not registered(uid):
        await update.message.reply_text("❌ መጀመሪያ /register ያድርጉ።", reply_markup=register_keyboard())
        return

    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ Open Bingo WebApp", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])

    await update.message.reply_text(
        "🎯 *BINGO CARTELLA*\n\n"
        "ካርቴላዎን ለመክፈት እና ለመጫወት ከታች ያለውን አዝራር ይጫኑ፦",
        parse_mode="Markdown",
        reply_markup=inline_keyboard,
    )

# --- DEPOSIT MENU (Telebirr & CBE only) ---
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not registered(uid):
        await update.message.reply_text("❌ መጀመሪያ /register ያድርጉ።", reply_markup=register_keyboard())
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Telebirr - Mobile money", callback_data="bank_deposit_Telebirr")],
        [InlineKeyboardButton("💳 CBE Birr - Mobile wallet", callback_data="bank_deposit_CBE")]
    ])

    await update.message.reply_text(
        "💳 *Choose payment method for Deposit:*\n"
        "• 📱 Telebirr - Mobile money\n"
        "• 💳 CBE Birr - Mobile wallet\n\n"
        "ገንዘብ ማስገባት የሚፈልጉበትን የክፍያ መንገድ ከታች ይምረጡ፦",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# --- WITHDRAW MENU (Telebirr & CBE only) ---
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not registered(uid):
        await update.message.reply_text("❌ መጀመሪያ /register ያድርጉ።", reply_markup=register_keyboard())
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Telebirr - Mobile money", callback_data="bank_withdraw_Telebirr")],
        [InlineKeyboardButton("💳 CBE Birr - Mobile wallet", callback_data="bank_withdraw_CBE")]
    ])

    await update.message.reply_text(
        "💸 *Choose payout method for Withdrawal:*\n"
        "• 📱 Telebirr - Mobile money\n"
        "• 💳 CBE Birr - Mobile wallet\n\n"
        "ገንዘብ መቀበል (ማውጣት) የሚፈልጉበትን መንገድ ከታች ይምረጡ፦",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# =========================
# CALLBACK & TEXT HANDLERS
# =========================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text == "💰 Balance":
        await balance(update, context)
    elif text == "💵 Deposit":
        await deposit(update, context)
    elif text == "💸 Withdraw":
        await withdraw(update, context)
    elif text == "❓ Help":
        await help_command(update, context)
    elif uid in user_states:
        state_info = user_states[uid]
        action = state_info["action"] 
        bank = state_info["bank"]
        step = state_info.get("step", "default")

        # ----------------- DEPOSIT PROCESSING -----------------
        if action == "deposit":
            # 1. የብር መጠንን ከባንክ SMS ውስጥ መፈለግ
            amount_match = re.search(r'(\d+[\d,]*\.?\d*)\s*(ETB|Birr|ብር|Br)?', text, re.IGNORECASE)
            
            # 2. የቴሌብር እና ሲቢኢ ትራንዛክሽን መለያዎችን (Transaction ID / FT / Ref) መለየት
            trx_match = re.search(r'(FT[A-Za-z0-9]{8,12}|TRX[A-Za-z0-9]{6,12}|TXN[A-Za-z0-9]{6,12}|Ref[:\s]*([A-Za-z0-9]{8,15}))', text, re.IGNORECASE)
            
            amount = 0.0
            if amount_match:
                try:
                    amount_str = amount_match.group(1).replace(',', '')
                    amount = float(amount_str)
                except ValueError:
                    pass

            if amount <= 0:
                await update.message.reply_text(
                    "❌ ከላኩት ጽሑፍ ውስጥ የብር መጠኑን ማግኘት አልቻልንም።\n"
                    "እባክዎ ትክክለኛውን የባንክ ዴፖዚት ፖስታ (SMS/Receipt) ሙሉውን ኮፒ አድርገው ይለጥፉ።",
                    parse_mode="Markdown"
                )
                return

            if not trx_match:
                await update.message.reply_text(
                    "❌ *ትክክለኛ የትራንዛክሽን መለያ (Transaction ID / FT...) አልተገኘም!ه‌*\n\n"
                    "እባክዎ የተሟላ የባንክ ዴፖዚት ኤስኤምኤስ (እንደ ቴሌብር FT ኮድ ወይም የሲቢኢ ሪፈረንስ ቁጥር ያለውን) የያዘ መልእክት ላኩ።",
                    parse_mode="Markdown"
                )
                return

            # ትክክለኛውን የትራንዛክሽን ኮድ ማውጣት
            trx_id = trx_match.group(1).upper()

            if trx_id in used_transactions:
                await update.message.reply_text(
                    f"⚠️ *ማስጠንቀቂያ!*\nይህ የትራንዛክሽን ቁጥር (`{trx_id}`) ከዚህ በፊት ጥቅም ላይ ውሏል! ድጋሚ መጠቀም አይቻልም።",
                    parse_mode="Markdown"
                )
                return

            used_transactions.add(trx_id)
            user_states.pop(uid, None)

            req_id = f"d_{uid}_{random.randint(1000, 9999)}"
            pending_deposits[req_id] = {"user_id": uid, "amount": amount, "bank": bank, "trx_id": trx_id, "transaction": text}

            await update.message.reply_text(
                f"✅ የ {amount:.2f} Birr ዴፖዚት ጥያቄዎ ({bank}) በትክክል ተቀባይነት አግኝቷል!\n"
                f"🔑 Transaction ID: `{trx_id}`\n"
                "⏳ አድሚን አረጋግጦ እስኪያስተካክለው በጥበቃ ላይ ይገኛል።",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )

            admin_kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve", callback_data=f"app_{req_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{req_id}")
            ]])

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "💵 *VERIFIED DEPOSIT REQUEST*\n\n"
                    f"👤 Name: {update.effective_user.full_name}\n"
                    f"🆔 User ID: `{uid}`\n"
                    f"🏦 Bank: *{bank}*\n"
                    f"💵 Amount: *{amount:.2f} Birr*\n"
                    f"🔑 Transaction ID: `{trx_id}`\n\n"
                    f"📄 *Receipt Text:*\n`{text}`"
                ),
                parse_mode="Markdown",
                reply_markup=admin_kb
            )

        # ----------------- WITHDRAW PROCESSING -----------------
        elif action == "withdraw":
            if step == "waiting_amount":
                try:
                    amount = float(text.replace(',', ''))
                except ValueError:
                    await update.message.reply_text("❌ እባክዎ ትክክለኛ የብር መጠን ብቻ ይጻፉ (ለምሳሌ፦ `50`)።", parse_mode="Markdown")
                    return

                if amount <= 0:
                    await update.message.reply_text("❌ መጠን ከ0 በላይ መሆን አለበት።")
                    return

                balance_now = users[uid]["balance"]
                if amount > balance_now:
                    await update.message.reply_text(f"❌ በቂ Balance የለዎትም።\nአሁን ያለዎት: {balance_now:.2f} Birr")
                    return

                user_states[uid] = {"action": "withdraw", "bank": bank, "step": "waiting_account", "amount": amount}

                await update.message.reply_text(
                    f"✅ የብር መጠኑ ({amount:.2f} Birr) ተመዝግቧል።\n\n"
                    f"💳 አሁን ደግሞ ገንዘቡ የሚገባበትን የ *{bank}* **አካውንት ቁጥር ወይም ስልክ ቁጥር** ይጻፉ፦",
                    parse_mode="Markdown"
                )

            elif step == "waiting_account":
                account_info = text.strip()
                if not account_info:
                    await update.message.reply_text("❌ እባክዎ ትክክለኛ አካውንት ቁጥር ይጻፉ።")
                    return

                amount = state_info["amount"]
                balance_now = users[uid]["balance"]

                if amount > balance_now:
                    user_states.pop(uid, None)
                    await update.message.reply_text("❌ በቂ Balance የለዎትም ጥያቄው ተሰርዟል።", parse_mode="Markdown")
                    return

                user_states.pop(uid, None)
                req_id = f"w_{uid}_{random.randint(1000, 9999)}"
                pending_withdrawals[req_id] = {"user_id": uid, "amount": amount, "bank": bank, "account": account_info}

                await update.message.reply_text(
                    f"✅ የ {amount:.2f} Birr withdrawal ጥያቄዎ ወደ *{bank}* ({account_info}) ተልኳል!\n⏳ አድሚን እስኪያረጋግጥ ይጠብቁ።",
                    parse_mode="Markdown",
                    reply_markup=main_keyboard()
                )

                admin_kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Approve", callback_data=f"app_{req_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"rej_{req_id}")
                ]])

                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(
                        "💸 *NEW WITHDRAW REQUEST*\n\n"
                        f"👤 Name: {update.effective_user.full_name}\n"
                        f"🆔 User ID: `{uid}`\n"
                        f"🏦 Selected Bank: *{bank}*\n"
                        f"💵 Amount: *{amount:.2f} Birr*\n"
                        f"💳 Target Account/Phone: `{account_info}`\n"
                        f"💰 Current Balance: {balance_now:.2f} Birr"
                    ),
                    parse_mode="Markdown",
                    reply_markup=admin_kb
                )

async def bank_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = update.effective_user.id

    if data.startswith("bank_"):
        parts = data.split("_")
        action = parts[1] # deposit ወይም withdraw
        bank = parts[2]   # Telebirr ወይም CBE

        if action == "deposit":
            user_states[uid] = {"action": action, "bank": bank}
            admin_acc = ADMIN_ACCOUNTS.get(bank, "0940483108 (kirubel melkamu)")
            instructions = (
                f"📱 *Selected Bank: {bank}*\n\n"
                f"Deposit Name: kirubel melkamu\n\n"
                f"📌 **ገንዘብ የሚልኩበት አካውንት፦**\n"
                f"`{admin_acc}`\n\n"
                f"እባክዎ ከላይ ባለው አካውንት ላይ ገንዘብ ከላኩ በኋላ ከባንኩ/ከቴሌብር የደረሰዎትን **የክፍያ ኤስኤምኤስ (Transaction SMS / Receipt with ID)** ሙሉውን ኮፒ አድርገው በዚህ ቻት ላይ ይለጥፉ (Paste)።\n\n"
                "🔒 ቦቱ የትራንዛክሽን ቁጥሩ ትክክለኛ መሆኑን እና ድጋሚ ጥቅም ላይ ያልዋለ መሆኑን በራሱ ያረጋግጣል!"
            )
        else:
            user_states[uid] = {"action": action, "bank": bank, "step": "waiting_amount"}
            instructions = (
                f"🏦 *Selected Payout Bank: {bank}*\n\n"
                "💸 እባክዎ ማውጣት የሚፈልጉትን **የብር መጠን** ብቻ ይጻፉ (ምሳሌ፦ `50`)፦"
            )

        await query.edit_message_text(text=instructions, parse_mode="Markdown")

# =========================
# ADMIN CALLBACK HANDLER
# =========================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Check pending deposits
    for key, req_info in list(pending_deposits.items()):
        if key in data:
            pending_deposits.pop(key)
            uid = req_info["user_id"]
            amount = req_info["amount"]
            bank = req_info["bank"]
            trx_id = req_info.get("trx_id", "N/A")
            if data.startswith("app"):
                if uid in users:
                    users[uid]["balance"] += amount
                    await query.edit_message_text(f"✅ Deposit of {amount:.2f} Birr ({bank}) [ID: {trx_id}] APPROVED.\n💰 New Balance: {users[uid]['balance']:.2f}")
                    await context.bot.send_message(chat_id=uid, text=f"🎉 የ <b>{amount:.2f} Birr</b> ዴፖዚት ጥያቄዎ ({bank}) ጸድቋል!\n💰 አዲሱ Balance: <b>{users[uid]['balance']:.2f} Birr</b>", parse_mode="HTML")
                else:
                    await query.edit_message_text("❌ User not found.")
            else:
                await query.edit_message_text(f"❌ Deposit REJECTED.")
                await context.bot.send_message(chat_id=uid, text=f"❌ የ {amount:.2f} Birr ዴፖዚት ጥያቄዎ ውድቅ ተደርጓል።")
            return

    # Check pending withdrawals
    for key, req_info in list(pending_withdrawals.items()):
        if key in data:
            pending_withdrawals.pop(key)
            uid = req_info["user_id"]
            amount = req_info["amount"]
            bank = req_info["bank"]
            account = req_info["account"]
            if data.startswith("app"):
                if uid in users and users[uid]["balance"] >= amount:
                    users[uid]["balance"] -= amount
                    await query.edit_message_text(f"✅ Withdraw of {amount:.2f} Birr to {bank} ({account}) APPROVED.\n💰 Remaining: {users[uid]['balance']:.2f}")
                    await context.bot.send_message(chat_id=uid, text=f"🎉 የ {amount:.2f} Birr withdrawal ጥያቄዎ ወደ *{bank}* ({account}) ተፈጽሟል!\n💰 አዲሱ Balance: {users[uid]['balance']:.2f} Birr", parse_mode="Markdown")
                else:
                    await query.edit_message_text(f"❌ User has insufficient balance or not found.")
                    await context.bot.send_message(chat_id=uid, text=f"❌ የ {amount:.2f} withdrawal ጥያቄዎ አልተሳካም (Balance በቂ አይደለም)።")
            else:
                await query.edit_message_text(f"❌ Withdraw REJECTED.")
                await context.bot.send_message(chat_id=uid, text=f"❌ የ {amount:.2f} withdrawal ጥያቄዎ ውድቅ ተደርጓል።")
            return

    await query.edit_message_text("⚠️ Request not found or already processed.")

# =========================
# ADMIN COMMANDS
# =========================
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        if target_id in users:
            users[target_id]["balance"] += amount
            await update.message.reply_text(f"✅ Added {amount} Birr to {target_id}. New balance: {users[target_id]['balance']:.2f}")
            await context.bot.send_message(chat_id=target_id, text=f"🎉 አካውንትዎ ላይ {amount:.2f} ተጨምሯል!\n💰 Balance: {users[target_id]['balance']:.2f} Birr")
        else:
            await update.message.reply_text("❌ ተጠቃሚው አልተገኘም።")
    except Exception:
        await update.message.reply_text("⚠️ አጠቃቀም፦ `/addbalance <user_id> <amount>`", parse_mode="Markdown")

# =========================
# HELP COMMAND
# =========================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *HELP*\n\n"
        "/start - Start bot\n"
        "/register - Contact registration\n"
        "/play - Play Bingo WebApp\n"
        "/balance - Check balance\n"
        "💵 Deposit - Select payment method, view account, send SMS\n"
        "💸 Withdraw - Select method, enter amount, then account",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

# =========================
# MAIN FUNCTION
# =========================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("play", play_game))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("help", help_command))
    
    app.add_handler(CommandHandler("addbalance", add_balance))
    app.add_handler(CallbackQueryHandler(bank_selection_callback, pattern="^bank_"))
    app.add_handler(CallbackQueryHandler(admin_callback))

    app.add_handler(MessageHandler(filters.CONTACT, contact_received))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    print("🤖 Bingo Bot is running with Telebirr & CBE only (Secure Transaction parsing)...")
    app.run_polling()

if __name__ == "__main__":
    main()
