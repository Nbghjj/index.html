import os
import random
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

# =========================
# IN-MEMORY DATA STORE
# =========================
users = {}
pending_withdrawals = {}
pending_deposits = {}
user_states = {}  # ተጠቃሚው አሁን የትኛውን ሂደት ላይ እንዳለ ለመያዝ (deposit/withdraw)

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

# --- DEPOSIT MENU WITH BANK CHOICES ---
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not registered(uid):
        await update.message.reply_text("❌ መጀመሪያ /register ያድርጉ።", reply_markup=register_keyboard())
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Telebirr", callback_data="bank_deposit_Telebirr")],
        [InlineKeyboardButton("🏦 CBE Birr", callback_data="bank_deposit_CBE")],
        [InlineKeyboardButton("🏛️ Awash Bank", callback_data="bank_deposit_Awash")],
        [InlineKeyboardButton("🏛️ Abyssinia Bank", callback_data="bank_deposit_Abyssinia")]
    ])

    await update.message.reply_text(
        "💵 *DEPOSIT - የክፍያ አማራጭ ይምረጡ*\n\n"
        "ገንዘብ ማስገባት የሚፈልጉበትን ባንክ/የክፍያ መንገድ ከታች ይምረጡ፦",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# --- WITHDRAW MENU WITH BANK CHOICES ---
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not registered(uid):
        await update.message.reply_text("❌ መጀመሪያ /register ያድርጉ።", reply_markup=register_keyboard())
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Telebirr", callback_data="bank_withdraw_Telebirr")],
        [InlineKeyboardButton("🏦 CBE Birr", callback_data="bank_withdraw_CBE")],
        [InlineKeyboardButton("🏛️ Awash Bank", callback_data="bank_withdraw_Awash")],
        [InlineKeyboardButton("🏛️ Abyssinia Bank", callback_data="bank_withdraw_Abyssinia")]
    ])

    await update.message.reply_text(
        "💸 *WITHDRAW - የባንክ አማራጭ ይምረጡ*\n\n"
        "ገንዘብ መቀበል የሚፈልጉበትን ባንክ/የክፍያ መንገድ ከታች ይምረጡ፦",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# =========================
# CALLBACK & TEXT HANDLERS (STEPS)
# =========================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if it's menu text first
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
        # User is typing the amount and account details after selecting a bank
        state_info = user_states[uid]
        action = state_info["action"] # 'deposit' or 'withdraw'
        bank = state_info["bank"]

        parts = text.split(" ", 1)
        try:
            amount = float(parts[0])
            account_info = parts[1] if len(parts) > 1 else "Not Provided"
        except ValueError:
            await update.message.reply_text("❌ ትክክለኛ ቅርጸት አልተጠቀሙም።\nእባክዎ እንደዚህ ይጻፉ፦ `100 0911223344`", parse_mode="Markdown")
            return

        if amount <= 0:
            await update.message.reply_text("❌ መጠን ከ0 በላይ መሆን አለበት።")
            return

        if action == "deposit":
            req_id = f"d_{uid}_{random.randint(1000, 9999)}"
            pending_deposits[req_id] = {"user_id": uid, "amount": amount, "bank": bank, "account": account_info}
            user_states.pop(uid, None)

            await update.message.reply_text(
                f"✅ የ {amount:.2f} Birr ዴፖዚት ጥያቄዎ ({bank} - {account_info}) ተልኳል!\n⏳ አድሚን እስኪያረጋግጥ ይጠብቁ።",
                reply_markup=main_keyboard()
            )

            admin_kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve", callback_data=f"app_{req_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{req_id}")
            ]])

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "💵 *NEW DEPOSIT REQUEST*\n\n"
                    f"👤 Name: {update.effective_user.full_name}\n"
                    f"🆔 User ID: `{uid}`\n"
                    f"🏦 Bank: *{bank}*\n"
                    f"💵 Amount: *{amount:.2f} Birr*\n"
                    f"💳 Account/Phone: `{account_info}`"
                ),
                parse_mode="Markdown",
                reply_markup=admin_kb
            )

        elif action == "withdraw":
            balance_now = users[uid]["balance"]
            if amount > balance_now:
                await update.message.reply_text(f"❌ በቂ Balance የለዎትም።\nአሁን ያለዎት: {balance_now:.2f} Birr")
                return

            req_id = f"w_{uid}_{random.randint(1000, 9999)}"
            pending_withdrawals[req_id] = {"user_id": uid, "amount": amount, "bank": bank, "account": account_info}
            user_states.pop(uid, None)

            await update.message.reply_text(
                f"✅ የ {amount:.2f} Birr withdrawal ጥያቄዎ ({bank} - {account_info}) ተልኳል!\n⏳ አድሚን እስኪያረጋግጥ ይጠብቁ።",
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
                    f"🏦 Bank: *{bank}*\n"
                    f"💵 Amount: *{amount:.2f} Birr*\n"
                    f"💳 Target Account: `{account_info}`\n"
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
        parts = data.split("_") # ['bank', 'deposit'/'withdraw', 'Telebirr'/'CBE'/...]
        action = parts[1]
        bank = parts[2]

        user_states[uid] = {"action": action, "bank": bank}

        if action == "deposit":
            instructions = (
                f"📱 *Selected Bank: {bank}*\n\n"
                "እባክዎ ገንዘብ ያስገቡበትን **መጠን** እና **የከፈሉበትን ቁጥር/አካውንት** በአንድ ላይ ይጻፉ።\n\n"
                "📌 *ምሳሌ፦* `100 0911223344`"
            )
        else:
            instructions = (
                f"🏦 *Selected Bank: {bank}*\n\n"
                "እባክዎ ማውጣት የሚፈልጉትን **የብር መጠን** እና **ገንዘቡ የሚላክበትን የባንክ/አካውንት ቁጥር** በአንድ ላይ ይጻፉ።\n\n"
                "📌 *ምሳሌ፦* `50 1000123456789`"
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
            account = req_info["account"]
            if data.startswith("app"):
                if uid in users:
                    users[uid]["balance"] += amount
                    await query.edit_message_text(f"✅ Deposit of {amount:.2f} Birr ({bank}) APPROVED.\n💰 New Balance: {users[uid]['balance']:.2f}")
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
                    await context.bot.send_message(chat_id=uid, text=f"🎉 የ {amount:.2f} Birr withdrawal ጥያቄዎ ወደ {bank} ({account}) ተፈጽሟል!\n💰 አዲሱ Balance: {users[uid]['balance']:.2f} Birr")
                else:
                    await query.edit_message_text(f"❌ User has insufficient balance or not found.")
                    await context.bot.send_message(chat_id=uid, text=f"❌ የ {amount:.2f} Birr withdrawal ጥያቄዎ አልተሳካም (Balance በቂ አይደለም)።")
            else:
                await query.edit_message_text(f"❌ Withdraw REJECTED.")
                await context.bot.send_message(chat_id=uid, text=f"❌ የ {amount:.2f} Birr withdrawal ጥያቄዎ ውድቅ ተደርጓል።")
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
        "/register - Register with contact\n"
        "/play - Play Bingo WebApp\n"
        "/balance - Check balance\n"
        "💵 Deposit - Select bank and deposit\n"
        "💸 Withdraw - Select bank and withdraw",
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

    print("🤖 Bingo Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
