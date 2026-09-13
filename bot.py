import json
import os
import random
import re
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# SETTINGS & CONFIGURATION
# =========================
TOKEN = os.getenv("BOT_TOKEN", "8909328591:AAEay418mvQF9dRBqjtSKgPDM_T-WpWWJ84")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6496982318"))
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://nbghjj.github.io/")

MIN_DEPOSIT = 50.0
MIN_WITHDRAW = 100.0

ADMIN_ACCOUNTS = {
    "Telebirr": "0940483108 (kirubel melkamu)",
    "CBE": "0940483108 (kirubel melkamu)",
}

DATA_FILE = "users_data.json"


def load_data():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r") as f:
        data = json.load(f)
        return {int(k): v for k, v in data.items()}
    except Exception:
      return {}
  return {}


def save_data():
  try:
    with open(DATA_FILE, "w") as f:
      json.dump(users, f, indent=4)
  except Exception as e:
    print(f"Error saving data: {e}")


users = load_data()
pending_withdrawals = {}
pending_deposits = {}
user_states = {}
used_transactions = set()

# =========================
# FLASK BACKEND SERVER (API)
# =========================
app = Flask(__name__)
CORS(app)  # CORS ፈቃድ ለ WebApp ገጽ ከ GitHub Pages


@app.route('/api/balance/<user_id>', methods=['GET'])
def api_get_balance(user_id):
  try:
    uid = int(user_id)
    balance = users.get(uid, {}).get('balance', 0.0)
    return jsonify({'success': True, 'balance': balance})
  except Exception as e:
    return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/check_user/<user_id>', methods=['GET'])
def api_check_user(user_id):
  try:
    uid = int(user_id)
    is_registered = uid in users and bool(users[uid].get('phone'))
    balance = users.get(uid, {}).get('balance', 0.0)
    return jsonify({
        'registered': is_registered,
        'balance': balance,
        'name': users.get(uid, {}).get('name', 'User'),
    })
  except Exception as e:
    return jsonify({'error': str(e)}), 400


@app.route('/api/update_balance', methods=['POST'])
def api_update_balance():
  try:
    data = request.json
    uid = int(data.get('userId'))
    amount = float(data.get('amount', 0.0))

    if uid not in users:
      users[uid] = {'name': 'WebApp User', 'phone': 'N/A', 'balance': 0.0}

    users[uid]['balance'] += amount
    if users[uid]['balance'] < 0:
      users[uid]['balance'] = 0.0

    save_data()
    return jsonify({'success': True, 'newBalance': users[uid]['balance']})
  except Exception as e:
    return jsonify({'success': False, 'error': str(e)}), 400


def run_flask():
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


# =========================
# TELEGRAM BOT FUNCTIONS
# =========================


def register_keyboard():
  return ReplyKeyboardMarkup(
      [[KeyboardButton('📱 Share Contact', request_contact=True)]],
      resize_keyboard=True,
      one_time_keyboard=True,
  )


def main_keyboard():
  return ReplyKeyboardMarkup(
      [
          [
              KeyboardButton(
                  '🎮 Play Bingo', web_app=WebAppInfo(url=WEB_APP_URL)
              )
          ],
          ['💰 Balance', '💵 Deposit'],
          ['💸 Withdraw', '❓ Help'],
      ],
      resize_keyboard=True,
  )


def registered(user_id):
  return user_id in users and bool(users[user_id].get('phone'))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if not registered(update.effective_user.id):
    await update.message.reply_text(
        '🎯 *AYAT BINGO BOT*\n\n'
        'እንኳን ደህና መጡ!\n\n'
        'Bot-ን ለመጠቀም መጀመሪያ Register ያድርጉ።\n'
        '📱 ከታች ያለውን *Share Contact* ይጫኑ።',
        parse_mode='Markdown',
        reply_markup=register_keyboard(),
    )
    return

  await update.message.reply_text(
      '✅ እንኳን ደህና መጡ!\nከታች ያለውን *🎮 Play Bingo* ተጫነው ጨዋታውን ይጀምሩ።',
      reply_markup=main_keyboard(),
  )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if registered(update.effective_user.id):
    await update.message.reply_text(
        '✅ ቀድሞውኑ Registered ነዎት።', reply_markup=main_keyboard()
    )
    return

  await update.message.reply_text(
      '📱 Registration ለመጨረስ *Share Contact* ይጫኑ።',
      parse_mode='Markdown',
      reply_markup=register_keyboard(),
  )


async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  contact = update.message.contact

  if contact.user_id != user.id:
    await update.message.reply_text(
        '❌ እባክዎ የራስዎን Telegram contact ብቻ Share ያድርጉ።',
        reply_markup=register_keyboard(),
    )
    return

  if user.id not in users:
    users[user.id] = {'balance': 0.0}

  users[user.id].update({
      'name': user.full_name,
      'phone': contact.phone_number,
  })
  save_data()

  await update.message.reply_text(
      '✅ *Registration successful!*\n\n'
      f'👤 Name: {user.full_name}\n'
      f'🆔 ID: `{user.id}`\n'
      '📱 Contact: Verified\n\n'
      'አሁን Bot-ን መጠቀም ይችላሉ።',
      parse_mode='Markdown',
      reply_markup=main_keyboard(),
  )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
  uid = update.effective_user.id
  if not registered(uid):
    await update.message.reply_text(
        '❌ መጀመሪያ /register ያድርጉ።', reply_markup=register_keyboard()
    )
    return

  current_bal = users[uid].get('balance', 0.0)
  await update.message.reply_text(
      f'💰 Your Balance: *{current_bal:.2f} Birr*',
      parse_mode='Markdown',
      reply_markup=main_keyboard(),
  )


async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
  uid = update.effective_user.id
  if not registered(uid):
    await update.message.reply_text(
        '❌ መጀመሪያ ጨዋታውን ለመጀመር 📱 *Share Contact* በማድረግ ሬጅስተር ማድረግ አለብዎት።',
        parse_mode='Markdown',
        reply_markup=register_keyboard(),
    )
    return

  inline_keyboard = InlineKeyboardMarkup([[
      InlineKeyboardButton(
          '🎟️ Open Bingo WebApp', web_app=WebAppInfo(url=WEB_APP_URL)
      )
  ]])

  await update.message.reply_text(
      '🎯 *AYAT BINGO CARTELLA*\n\n'
      'ካርቴላዎን ለመክፈት እና ለመጫወት ከታች ያለውን አዝራር ይጫኑ፦',
      parse_mode='Markdown',
      reply_markup=inline_keyboard,
  )


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
  uid = update.effective_user.id
  if not registered(uid):
    await update.message.reply_text(
        '❌ መጀመሪያ /register ያድርጉ።', reply_markup=register_keyboard()
    )
    return

  keyboard = InlineKeyboardMarkup([
      [
          InlineKeyboardButton(
              '📱 Telebirr', callback_data='bank_deposit_Telebirr'
          )
      ],
      [InlineKeyboardButton('💳 CBE Birr', callback_data='bank_deposit_CBE')],
  ])

  await update.message.reply_text(
      '💳 *Choose payment method for Deposit:*\n'
      f'📌 (ዝቅተኛው የዲፖዚት መጠን: *{MIN_DEPOSIT:.2f} Birr*)\n\n'
      'ገንዘብ ማስገባት የሚፈልጉበትን የክፍያ መንገድ ከታች ይምረጡ፦',
      parse_mode='Markdown',
      reply_markup=keyboard,
  )


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
  uid = update.effective_user.id
  if not registered(uid):
    await update.message.reply_text(
        '❌ መጀመሪያ /register ያድርጉ።', reply_markup=register_keyboard()
    )
    return

  keyboard = InlineKeyboardMarkup([
      [
          InlineKeyboardButton(
              '📱 Telebirr', callback_data='bank_withdraw_Telebirr'
          )
      ],
      [InlineKeyboardButton('💳 CBE Birr', callback_data='bank_withdraw_CBE')],
  ])

  await update.message.reply_text(
      '💸 *Choose payout method for Withdrawal:*\n'
      f'📌 (ዝቅተኛው የዊዝድሮ መጠን: *{MIN_WITHDRAW:.2f} Birr*)\n\n'
      'ገንዘብ መቀበል (ማውጣት) የሚፈልጉበትን መንገድ ከታች ይምረጡ፦',
      parse_mode='Markdown',
      reply_markup=keyboard,
  )


async def web_app_data_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  uid = update.effective_user.id
  if not registered(uid):
    return

  try:
    data = json.loads(update.message.web_app_data.data)
    action = data.get('action')
    amount = float(data.get('amount', 0))

    if action == 'update_balance':
      users[uid]['balance'] += amount
      if users[uid]['balance'] < 0:
        users[uid]['balance'] = 0.0

      save_data()
      await update.message.reply_text(
          '🎮 የዌብ አፕ ጨዋታ ውጤት ተዘምኗል!\n'
          f"💰 አዲሱ Balance: *{users[uid]['balance']:.2f} Birr*",
          parse_mode='Markdown',
          reply_markup=main_keyboard(),
      )
  except Exception as e:
    print(f'WebAppData Error: {e}')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = update.message.text
  uid = update.effective_user.id

  if text == '💰 Balance':
    await balance(update, context)
  elif text == '💵 Deposit':
    await deposit(update, context)
  elif text == '💸 Withdraw':
    await withdraw(update, context)
  elif text == '❓ Help':
    await help_command(update, context)
  elif uid in user_states:
    state_info = user_states[uid]
    action = state_info['action']
    bank = state_info['bank']
    step = state_info.get('step', 'default')

    if action == 'deposit':
      if step == 'waiting_amount':
        try:
          entered_amount = float(text.replace(',', '').strip())
        except ValueError:
          await update.message.reply_text(
              '❌ እባክዎ ትክክለኛ የብር መጠን ብቻ ይጻፉ (ምሳሌ፦ `100`)።',
              parse_mode='Markdown',
          )
          return

        if entered_amount < MIN_DEPOSIT:
          await update.message.reply_text(
              f'❌ ይቅርታ፣ ዝቅተኛው የዲፖዚት መጠን *{MIN_DEPOSIT:.2f} Birr* መሆን'
              ' አለበት።',
              parse_mode='Markdown',
          )
          return

        user_states[uid] = {
            'action': 'deposit',
            'bank': bank,
            'step': 'waiting_receipt',
            'amount': entered_amount,
        }
        admin_acc = ADMIN_ACCOUNTS.get(bank, '0940483108 (kirubel melkamu)')

        await update.message.reply_text(
            f'✅ የብር መጠኑ (*{entered_amount:.2f} Birr*) ተመዝግቧል።\n\n'
            f'📌 **ገንዘብ የሚልኩበት አካውንት ({bank})፦**\n'
            f'`{admin_acc}`\n\n'
            'እባክዎ ከላይ ባለው አካውንት ላይ ገንዘቡን ከላኩ በኋላ የደረሰዎትን **የክፍያ ኤስኤምኤስ (SMS)'
            ' ወይም ፖስታ** ሙሉውን ኮፒ አድርገው በዚህ ቻት ላይ ይለጥፉ (Paste)።',
            parse_mode='Markdown',
        )

      elif step == 'waiting_receipt':
        expected_amount = state_info['amount']
        text_lower = text.lower()
        is_valid_format = False

        if bank == 'Telebirr':
          if any(
              keyword in text_lower
              for keyword in [
                  'transferred',
                  'paid',
                  'sent',
                  'telebirr',
                  'account',
                  'etb',
                  'ብር',
              ]
          ):
            is_valid_format = True
        elif bank == 'CBE':
          if any(
              keyword in text_lower
              for keyword in [
                  'debited',
                  'credited',
                  'cbe',
                  'commercial bank',
                  'etb',
                  'ብር',
                  'account',
              ]
          ):
            is_valid_format = True

        if not is_valid_format:
          await update.message.reply_text(
              '❌ *ልክ ያልሆነ የክፍያ ፖስታ (Invalid Receipt)!*\n\n'
              f'ላኩት ጽሑፍ ትክክለኛ የ *{bank}* የባንክ መረጃ/ኤስኤምኤስ ሆኖ አልተገኘም።\n'
              'እባክዎ ትክክለኛውን ኦሪጅናል የባንክ ፖስታ ኮፒ አድርገው ይላኩ።',
              parse_mode='Markdown',
          )
          return

        amount_match = re.search(
            r'(\d+[\d,]*\.?\d*)\s*(ETB|Birr|ብር|Br)?', text, re.IGNORECASE
        )
        trx_match = re.search(
            r'(FT[A-Za-z0-9]{8,12}|TRX[A-Za-z0-9]{6,12}|TXN[A-Za-z0-9]{6,12}|Ref[:\s]*([A-Za-z0-9]{8,15}))',
            text,
            re.IGNORECASE,
        )

        sms_amount = 0.0
        if amount_match:
          try:
            amount_str = amount_match.group(1).replace(',', '')
            sms_amount = float(amount_str)
          except ValueError:
            pass

        if sms_amount <= 0 or not trx_match:
          await update.message.reply_text(
              '❌ ከላኩት ጽሑፍ ውስጥ ትክክለኛ የብር መጠን ወይም የትራንዛክሽን ኮድ ማግኘት አልቻልንም።\n'
              'እባክዎ ትክክለኛውን የባንክ ዴፖዚት ፖስታ ሙሉውን ኮፒ አድርገው እንደገና ይላኩ።',
              parse_mode='Markdown',
          )
          return

        trx_id = trx_match.group(1).upper()

        if trx_id in used_transactions:
          await update.message.reply_text(
              '⚠️ *ማስጠንቀቂያ!*\nይህ የትራንዛክሽን ቁጥር'
              f' (`{trx_id}`) ከዚህ በፊት ጥቅም ላይ ውሏል! ድጋሚ መጠቀም አይቻልም።',
              parse_mode='Markdown',
          )
          return

        used_transactions.add(trx_id)
        user_states.pop(uid, None)

        req_id = f'd_{uid}_{random.randint(1000, 9999)}'
        pending_deposits[req_id] = {
            'user_id': uid,
            'amount': expected_amount,
            'bank': bank,
            'trx_id': trx_id,
            'transaction': text,
        }

        await update.message.reply_text(
            f'✅ የ {expected_amount:.2f} Birr ዴፖዚት ጥያቄዎ ({bank}) በትክክል ተቀባይነት'
            ' አግኝቷል!\n'
            f'🔑 Transaction ID: `{trx_id}`\n'
            '⏳ አድሚን አረጋግጦ እስኪያስተካክለው በጥበቃ ላይ ይገኛል።',
            parse_mode='Markdown',
            reply_markup=main_keyboard(),
        )

        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton('✅ Approve', callback_data=f'app_{req_id}'),
            InlineKeyboardButton('❌ Reject', callback_data=f'rej_{req_id}'),
        ]])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                '💵 *VERIFIED DEPOSIT REQUEST*\n\n'
                f'👤 Name: {update.effective_user.full_name}\n'
                f'🆔 User ID: `{uid}`\n'
                f'🏦 Bank: *{bank}*\n'
                f'💵 Amount: *{expected_amount:.2f} Birr*\n'
                f'🔑 Transaction ID: `{trx_id}`\n\n'
                f'📄 *Receipt Text:*\n`{text}`'
            ),
            parse_mode='Markdown',
            reply_markup=admin_kb,
        )

    elif action == 'withdraw':
      if step == 'waiting_amount':
        try:
          amount = float(text.replace(',', ''))
        except ValueError:
          await update.message.reply_text(
              '❌ እባክዎ ትክክለኛ የብር መጠን ብቻ ይጻፉ (ለምሳሌ፦ `100`)።',
              parse_mode='Markdown',
          )
          return

        if amount < MIN_WITHDRAW:
          await update.message.reply_text(
              f'❌ ይቅርታ፣ ዝቅተኛው የማውጫ (Withdraw) መጠን *{MIN_WITHDRAW:.2f} Birr*'
              ' መሆን አለበት።',
              parse_mode='Markdown',
          )
          return

        balance_now = users.get(uid, {}).get('balance', 0.0)
        if amount > balance_now:
          await update.message.reply_text(
              f'❌ በቂ Balance የለዎትም።\nአሁን ያለዎት: {balance_now:.2f} Birr'
          )
          return

        user_states[uid] = {
            'action': 'withdraw',
            'bank': bank,
            'step': 'waiting_account',
            'amount': amount,
        }

        await update.message.reply_text(
            f'✅ የብር መጠኑ ({amount:.2f} Birr) ተመዝግቧል።\n\n'
            f'💳 አሁን ደግሞ ገንዘቡ የሚገባበትን የ *{bank}* **ትክክለኛ አካውንት ቁጥር ወይም ስልክ'
            ' ቁጥር** ይጻፉ፦',
            parse_mode='Markdown',
        )

      elif step == 'waiting_account':
        account_info = text.strip()
        if len(account_info) < 9 or not any(
            char.isdigit() for char in account_info
        ):
          await update.message.reply_text(
              '❌ እባክዎ ትክክለኛ የቴሌብር ስልክ ቁጥር ወይም የባንክ አካውንት ቁጥር ብቻ ይጻፉ።'
          )
          return

        amount = state_info['amount']
        user_states[uid] = {
            'action': 'withdraw',
            'bank': bank,
            'step': 'waiting_name',
            'amount': amount,
            'account': account_info,
        }

        await update.message.reply_text(
            f'✅ አካውንት ቁጥር: `{account_info}` ተመዝግቧል።\n\n'
            '👤 በመጨረሻም የዚህ አካውንት **ባለቤት ስም (Account Holder Name)** ሙሉውን ጽፈው'
            ' ይላኩ፦',
            parse_mode='Markdown',
        )

      elif step == 'waiting_name':
        account_name = text.strip()
        if len(account_name) < 3:
          await update.message.reply_text('❌ እባክዎ ትክክለኛ ሙሉ ስም ይጻፉ።')
          return

        amount = state_info['amount']
        account_info = state_info['account']
        balance_now = users.get(uid, {}).get('balance', 0.0)

        if amount > balance_now:
          user_states.pop(uid, None)
          await update.message.reply_text(
              '❌ በቂ Balance የለዎትም ጥያቄው ተሰርዟል።', parse_mode='Markdown'
          )
          return

        user_states.pop(uid, None)
        req_id = f'w_{uid}_{random.randint(1000, 9999)}'
        pending_withdrawals[req_id] = {
            'user_id': uid,
            'amount': amount,
            'bank': bank,
            'account': account_info,
            'account_name': account_name,
        }

        await update.message.reply_text(
            f'✅ የ {amount:.2f} Birr withdrawal ጥያቄዎ ወደ *{bank}* ({account_info} -'
            ' {account_name}) ተልኳል!\n⏳ አድሚን እስኪያረጋግጥ ይጠብቁ።',
            parse_mode='Markdown',
            reply_markup=main_keyboard(),
        )

        admin_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton('✅ Approve', callback_data=f'app_{req_id}'),
            InlineKeyboardButton('❌ Reject', callback_data=f'rej_{req_id}'),
        ]])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                '💸 *NEW WITHDRAW REQUEST*\n\n'
                f'👤 Telegram Name: {update.effective_user.full_name}\n'
                f'🆔 User ID: `{uid}`\n'
                f'🏦 Selected Bank: *{bank}*\n'
                f'💵 Amount: *{amount:.2f} Birr*\n'
                f'💳 Account/Phone: `{account_info}`\n'
                f'👤 Holder Name: *{account_name}*\n'
                f'💰 Current Balance: {balance_now:.2f} Birr'
            ),
            parse_mode='Markdown',
            reply_markup=admin_kb,
        )


async def bank_selection_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  query = update.callback_query
  await query.answer()
  data = query.data
  uid = update.effective_user.id

  if data.startswith('bank_'):
    parts = data.split('_')
    action = parts[1]
    bank = parts[2]

    user_states[uid] = {'action': action, 'bank': bank, 'step': 'waiting_amount'}
    instructions = (
        f'📱 *Selected Bank: {bank}*\n\n'
        '💸 እባክዎ ማስገባት/ማውጣት የሚፈልጉትን **የብር መጠን** ይጻፉ፦'
    )
    await query.edit_message_text(text=instructions, parse_mode='Markdown')


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  data = query.data

  for key, req_info in list(pending_deposits.items()):
    if key in data:
      pending_deposits.pop(key)
      uid = req_info['user_id']
      amount = req_info['amount']
      bank = req_info['bank']

      if data.startswith('app'):
        if uid in users:
          users[uid]['balance'] += amount
          save_data()
          await query.edit_message_text(
              f'✅ Deposit of {amount:.2f} Birr ({bank}) APPROVED.\n💰 New'
              f' Balance: {users[uid]["balance"]:.2f}'
          )
          await context.bot.send_message(
              chat_id=uid,
              text=(
                  f'🎉 የ <b>{amount:.2f} Birr</b> ዴፖዚት ጥያቄዎ ({bank})'
                  f' ጸድቋል!\n💰 አዲሱ Balance: <b>{users[uid]["balance"]:.2f}'
                  ' Birr</b>'
              ),
              parse_mode='HTML',
          )
      else:
        await query.edit_message_text('❌ Deposit REJECTED.')
        await context.bot.send_message(
            chat_id=uid, text=f'❌ የ {amount:.2f} ዴፖዚት ጥያቄዎ ውድቅ ተደርጓል።'
        )
      return

  for key, req_info in list(pending_withdrawals.items()):
    if key in data:
      pending_withdrawals.pop(key)
      uid = req_info['user_id']
      amount = req_info['amount']
      bank = req_info['bank']

      if data.startswith('app'):
        if uid in users and users[uid]['balance'] >= amount:
          users[uid]['balance'] -= amount
          save_data()
          await query.edit_message_text(
              f'✅ Withdraw of {amount:.2f} Birr APPROVED.\n💰 Remaining:'
              f' {users[uid]["balance"]:.2f}'
          )
          await context.bot.send_message(
              chat_id=uid,
              text=(
                  f'🎉 የ {amount:.2f} Birr withdrawal ጥያቄዎ ጸድቋል!\n💰 አዲሱ Balance:'
                  f' {users[uid]["balance"]:.2f} Birr'
              ),
              parse_mode='Markdown',
          )
        else:
          await query.edit_message_text('❌ User has insufficient balance.')
      else:
        await query.edit_message_text('❌ Withdraw REJECTED.')
        await context.bot.send_message(
            chat_id=uid, text=f'❌ የ {amount:.2f} withdrawal ጥያቄዎ ውድቅ ተደርጓል።'
        )
      return


async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id != ADMIN_ID:
    return

  try:
    target_id = int(context.args[0])
    amount = float(context.args[1])
    if target_id not in users:
      users[target_id] = {'balance': 0.0}

    users[target_id]['balance'] += amount
    save_data()

    await update.message.reply_text(
        f'✅ Added {amount} Birr to {target_id}. New balance:'
        f' {users[target_id]["balance"]:.2f}'
    )
    await context.bot.send_message(
        chat_id=target_id,
        text=(
            f'🎉 አካውንትዎ ላይ {amount:.2f} ተጨምሯል!\n💰 Balance:'
            f' {users[target_id]["balance"]:.2f} Birr'
        ),
    )
  except Exception:
    await update.message.reply_text(
        '⚠️ አጠቃቀም፦ `/addbalance <user_id> <amount>`', parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      '📖 *HELP*\n\n'
      '/start - Start bot\n'
      '/register - Contact registration\n'
      '/play - Play Bingo WebApp\n'
      '/balance - Check balance\n'
      f'💵 Deposit - Min: {MIN_DEPOSIT} Birr\n'
      f'💸 Withdraw - Min: {MIN_WITHDRAW} Birr',
      parse_mode='Markdown',
      reply_markup=main_keyboard(),
  )


def main():
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()
  print('🌐 Flask API Server started...')

  bot_app = Application.builder().token(TOKEN).build()

  bot_app.add_handler(CommandHandler('start', start))
  bot_app.add_handler(CommandHandler('register', register))
  bot_app.add_handler(CommandHandler('play', play_game))
  bot_app.add_handler(CommandHandler('balance', balance))
  bot_app.add_handler(CommandHandler('deposit', deposit))
  bot_app.add_handler(CommandHandler('withdraw', withdraw))
  bot_app.add_handler(CommandHandler('help', help_command))
  bot_app.add_handler(CommandHandler('addbalance', add_balance))

  bot_app.add_handler(
      CallbackQueryHandler(bank_selection_callback, pattern='^bank_')
  )
  bot_app.add_handler(CallbackQueryHandler(admin_callback))

  bot_app.add_handler(MessageHandler(filters.CONTACT, contact_received))
  bot_app.add_handler(
      MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler)
  )
  bot_app.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)
  )

  print('🤖 Bingo Bot is running...')
  bot_app.run_polling()


if __name__ == '__main__':
  main()
