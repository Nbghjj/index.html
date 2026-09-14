import random
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

registered_users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id in registered_users:
        await update.message.reply_text(
            f"ሰላም {user.first_name}! ቀደም ብለው ተመዝግበዋል።\n"
            "ጨዋታ ለመጀመር /play የሚለውን ይጫኑ።"
        )
        return

    contact_keyboard = KeyboardButton(text="📱 ስልክ ቁጥር አጋራ", request_contact=True)
    custom_keyboard = [[contact_keyboard]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        f"ሰላም {user.first_name}! ወደ ቢንጎ ጨዋታ እንኳን ደህና መጡ።\n\n"
        "ለመመዝገብ እባክዎን ከታች ያለውን **'ስልክ ቁጥር አጋራ'** የሚለውን ቁልፍ ይጫኑ፡",
        reply_markup=reply_markup
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user

    registered_users[user.id] = {
        "full_name": f"{user.first_name} {user.last_name or ''}".strip(),
        "username": user.username,
        "phone_number": contact.phone_number
    }

    await update.message.reply_text(
        f"✅ ተመዝግበዋል!\n\n"
        f"👤 ስም: {user.first_name}\n"
        f"📞 ስልክ: {contact.phone_number}\n\n"
        "አሁን /play በማለት የቢንጎ ካርድዎን ማግኘት ይችላሉ።",
        reply_markup=ReplyKeyboardRemove()
    )

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in registered_users:
        await update.message.reply_text("⚠️ ጨዋታ ለመጀመር በመጀመሪያ /start ብለው ይመዝገቡ!")
        return

    numbers = list(range(1, 26))
    random.shuffle(numbers)
    card = [numbers[i:i+5] for i in range(0, 25, 5)]

    card_text = "🎲 **የእርስዎ የቢንጎ ካርድ** 🎲\n\n"
    for row in card:
        card_text += " | ".join(f"{num:2d}" for num in row) + "\n"
        card_text += "---------------------\n"

    await update.message.reply_text(card_text, parse_mode='Markdown')

if __name__ == '__main__':
    BOT_TOKEN = "8909328591:AAEay418mvQF9dRBqjtSKgPDM_T-WpWWJ84"
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    print("ቦቱ ሥራ ጀምሯል...")
    app.run_polling()
