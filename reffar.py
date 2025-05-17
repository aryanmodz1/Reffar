import logging
import json
import os
import random
import string
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# --- Configuration ---
BOT_TOKEN = "7543155411:AAEeD3NmlShioUKrAOOAyvu1umlNiGoRwHA" 
# <<<<<<<<<<<<<< YAHAN APNA BOT TOKEN DAALO
DATA_FILE = "telegram_referral_data.json"
REFERRAL_CODE_LENGTH = 6
REFERRAL_BONUS_REFERRER = 10  # Refer karne wale ko points
SIGNUP_BONUS_REFEREE = 5      # Refer se sign up karne wale ko points

# Enable logging (optional, but good for debugging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Data Handling ---
def load_data():
    if not os.path.exists(DATA_FILE):
        # users: {user_id_str: {"referral_code": "ABC", "balance": 0, "referred_by": None, "referrals_made": []}}
        # referral_codes: {"ABC": user_id_str}
        return {"users": {}, "referral_codes": {}}
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            if "users" not in data: data["users"] = {}
            if "referral_codes" not in data: data["referral_codes"] = {}
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {"users": {}, "referral_codes": {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def generate_referral_code(existing_codes_values):
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=REFERRAL_CODE_LENGTH))
        if code not in existing_codes_values:
            return code

# --- Bot Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id) # User ID ko string mein store karenge JSON keys ke liye
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name

    data = load_data()
    users = data.get("users", {})
    referral_codes_map = data.get("referral_codes", {})

    if user_id in users:
        await update.message.reply_text(
            f"Welcome back, {user_name}!\n"
            f"Aapka referral code hai: {users[user_id]['referral_code']}\n"
            f"Aapka balance hai: {users[user_id]['balance']} points.\n"
            "Use /mycode to see your code, or /balance to check points."
        )
        return

    # New user registration
    my_personal_ref_code = generate_referral_code(referral_codes_map.keys())
    new_user_data = {
        "referral_code": my_personal_ref_code,
        "balance": 0,
        "referred_by": None,
        "referrals_made": []
    }

    reply_message = f"Hi {user_name}! Welcome to the Referral Bot!\n"
    reply_message += "Aap register ho gaye ho.\n"

    # Check if user came with a referral code (e.g., t.me/YourBot?start=REFCODE)
    # context.args will contain the part after /start command, if any
    if context.args and len(context.args) > 0:
        incoming_ref_code = context.args[0].upper()
        if incoming_ref_code in referral_codes_map:
            referrer_user_id = referral_codes_map[incoming_ref_code]
            if referrer_user_id == user_id: # Khud ko refer nahi kar sakte
                reply_message += "Aap khud ko refer nahi kar sakte.\n"
            elif referrer_user_id in users:
                # Bonus to referee (new user)
                new_user_data["balance"] += SIGNUP_BONUS_REFEREE
                new_user_data["referred_by"] = referrer_user_id
                reply_message += f"Referral code '{incoming_ref_code}' successfully use kiya! Aapko {SIGNUP_BONUS_REFEREE} points mile.\n"

                # Bonus to referrer
                users[referrer_user_id]["balance"] += REFERRAL_BONUS_REFERRER
                users[referrer_user_id]["referrals_made"].append(user_id) # Store new user's ID
                try:
                    # Referrer ko message bhejo (agar bot usse pehle baat kar chuka hai)
                    referrer_chat_id = users[referrer_user_id].get("chat_id", referrer_user_id) # Use chat_id if stored
                    await context.bot.send_message(
                        chat_id=referrer_chat_id, # Referrer ka chat_id lagega
                        text=f"Badhai ho! {user_name} (ID: {user_id}) ne aapka referral code use kiya. Aapko {REFERRAL_BONUS_REFERRER} points mile."
                    )
                except Exception as e:
                    logger.error(f"Referrer ko DM karne mein error ({referrer_user_id}): {e}")
                    reply_message += f"(Referrer {referrer_user_id} ko bonus mil gaya hai, but unko DM nahi kar paya.)\n"
            else:
                reply_message += "Invalid referral code. Referrer nahi mila.\n"
        else:
            reply_message += "Invalid referral code. Normal registration ho gaya.\n"

    # Store chat_id for future DMs (like referral notifications)
    new_user_data["chat_id"] = chat_id

    users[user_id] = new_user_data
    referral_codes_map[my_personal_ref_code] = user_id

    save_data({"users": users, "referral_codes": referral_codes_map})

    reply_message += f"Aapka personal referral code hai: {my_personal_ref_code}\n"
    reply_message += f"Aapka current balance hai: {new_user_data['balance']} points."
    await update.message.reply_text(reply_message)


async def my_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    users = data.get("users", {})

    if user_id in users:
        await update.message.reply_text(f"Aapka referral code hai: {users[user_id]['referral_code']}")
    else:
        await update.message.reply_text("Aap abhi tak register nahi hue ho. /start type karo register karne ke liye.")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    users = data.get("users", {})

    if user_id in users:
        await update.message.reply_text(f"Aapka current balance hai: {users[user_id]['balance']} points.")
    else:
        await update.message.reply_text("Aap abhi tak register nahi hue ho. /start type karo register karne ke liye.")

async def referrals_made_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    users = data.get("users", {})

    if user_id in users:
        referred_users_ids = users[user_id].get("referrals_made", [])
        if referred_users_ids:
            message = "Aapne in users ko refer kiya hai (User IDs):\n"
            for ref_id in referred_users_ids:
                # Optionally, you could try to get their name if you store it
                # For now, just showing IDs
                message += f"- {ref_id}\n"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Aapne abhi tak kisi ko refer nahi kiya hai.")
    else:
        await update.message.reply_text("Aap abhi tak register nahi hue ho. /start type karo register karne ke liye.")


# --- Main Bot Setup ---
def main():
    if BOT_TOKEN == "7543155411:AAEeD3NmlShioUKrAOOAyvu1umlNiGoRwHA":
        print("ERROR: Please replace 'YOUR_ACTUAL_BOT_TOKEN' with your real bot token in the code.")
        return

    print("Bot shuru ho raha hai...")

    # Application (using ApplicationBuilder for PTB v20+)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("mycode", my_code_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("myreferrals", referrals_made_command))

    # Start the Bot
    print("Bot poll kar raha hai...")
    app.run_polling()
    print("Bot band ho gaya.")

if __name__ == '__main__':
    main()