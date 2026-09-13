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
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://nbghjj.github.io/index.html")

# =========================
# IN-MEMORY DATA STORE
# =========================
users = {}
pending_withdrawals = {}

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

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not registered(update.effective_user.id):
        await update.message.reply_text("❌ መጀመሪያ /register ያድርጉ።", reply_markup=register_keyboard())
        return

    await update.message.reply_text(
        "💰 *DEPOSIT INSTRUCTIONS*\n\n"
        "ክፍያ ለመፈጸም ከታች ባሉት የክፍያ አማራጮች ይጠቀሙ፦\n\n"
        "📱 *Telebirr / CBE Birr*\n"
        "• Phone: `0940484108`\n"
        "• Name: *Kirubel*\n\n"
        "📌 *ክፍያ ከፈፀሙ በኋላ፦*\n"
        "1️⃣ የከፈሉበትን የ Transaction SMS ማረጋገጫ ወይም Receipt Screenshot ለAdmin ይላኩ።\n"
        "2️⃣ Admin መረጃውን አረጋግጦ Balance ይጨምርልዎታል።",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not registered(uid):
        await update.message.reply_text("❌ መጀመሪያ /register ያድርጉ።", reply_markup=register_keyboard())
        return

    if not context.args:
        await update.message.reply_text(
            "💸 Withdrawal amount ያስገቡ።\n\nምሳሌ፦ `/withdraw 100`",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Amount ቁጥር መሆን አለበት።")
        return

    if amount <= 0:
        await update.message.reply_text("❌ Amount ከ0 በላይ መሆን አለበት።")
        return

    balance_now = users[uid]["balance"]
    if amount > balance_now:
        await update.message.reply_text(f"❌ Insufficient balance.\nYour balance: {balance_now:.2f} Birr")
        return

    req_id = f"{uid}_{int(random.randint(1000, 9999))}"
    pending_withdrawals[req_id] = {"user_id": uid, "amount": amount}

    await update.message.reply_text(
        f"✅ Withdrawal request received.\n\n💰 Amount: {amount:.2f} Birr\n"
        "⏳ Admin እስኪያረጋግጥ ድረስ ይጠብቁ።",
        reply_markup=main_keyboard(),
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"app_w_{req_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_w_{req_id}")
        ]
    ])

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "💸 *NEW WITHDRAW REQUEST*\n\n"
                f"👤 Name: {update.effective_user.full_name}\n"
                f"🆔 User ID: `{uid}`\n"
                f"📱 Phone: `{users[uid]['phone']}`\n"
                f"💵 Amount: *{amount:.2f} Birr*\n"
                f"💰 Current Balance: {balance_now:.2f} Birr"
            ),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    except Exception as e:
        print("Admin notification error:", e)

# =========================
# ADMIN CALLBACK HANDLER
# =========================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("app_w_"):
        req_id = data.replace("app_w_", "")
        if req_id in pending_withdrawals:
            req_info = pending_withdrawals.pop(req_id)
            uid = req_info["user_id"]
            amount = req_info["amount"]

            if users[uid]["balance"] >= amount:
                users[uid]["balance"] -= amount
                await query.edit_message_text(f"✅ Withdrawal of {amount} Birr APPROVED for User {uid}.")
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"🎉 የጥያቄዎትን {amount:.2f} Birr withdrawal Admin አጽድቆታል።\n💰 አዲሱ Balance: {users[uid]['balance']:.2f} Birr"
                )
            else:
                await query.edit_message_text(f"❌ Failed: User ID {uid} has insufficient balance now.")
        else:
            await query.edit_message_text("⚠️ Request not found or already processed.")

    elif data.startswith("rej_w_"):
        req_id = data.replace("rej_w_", "")
        if req_id in pending_withdrawals:
            req_info = pending_withdrawals.pop(req_id)
            uid = req_info["user_id"]
            amount = req_info["amount"]

            await query.edit_message_text(f"❌ Withdrawal of {amount} Birr REJECTED.")
            await context.bot.send_message(
                chat_id=uid,
                text=f"❌ የ {amount:.2f} Birr withdrawal ጥያቄዎ ውድቅ ተደርጓል።"
            )

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
            await context.bot.send_message(chat_id=target_id, text=f"🎉 አካውንትዎ ላይ {amount:.2f} Birr ተጨምሯል!\n💰 Balance: {users[target_id]['balance']:.2f} Birr")
        else:
            await update.message.reply_text("❌ ተጠቃሚው አልተገኘም።")
    except Exception:
        await update.message.reply_text("⚠️ አጠቃቀም፦ `/addbalance <user_id> <amount>`", parse_mode="Markdown")

# =========================
# HELP & BUTTON HANDLER
# =========================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *HELP*\n\n"
        "/start - Start bot\n"
        "/register - Register with contact\n"
        "/play - Play Bingo WebApp\n"
        "/balance - Check balance\n"
        "/deposit - Deposit\n"
        "/withdraw 100 - Withdraw 100 Birr",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💰 Balance":
        await balance(update, context)
    elif text == "💵 Deposit":
        await deposit(update, context)
    elif text == "💸 Withdraw":
        await withdraw(update, context)
    elif text == "❓ Help":
        await help_command(update, context)

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
    app.add_handler(CallbackQueryHandler(admin_callback))

    app.add_handler(MessageHandler(filters.CONTACT, contact_received))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    print("🤖 Bingo Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
