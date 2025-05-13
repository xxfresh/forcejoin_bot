import os
import json
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("forcejoin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

admin_id = 123456789  # Replace this with your real Telegram ID
data_file = "data.json"

# Load or initialize data
def load_data():
    if not os.path.exists(data_file):
        return {"channels": [], "buttons": [], "instruction": ""}
    with open(data_file, "r") as f:
        return json.load(f)

def save_data(data):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()
users = set()

# Helper to check if user joined all required channels
async def has_joined_required(user_id):
    for ch in data.get("channels", []):
        try:
            member = await app.get_chat_member(ch, user_id)
            if member.status not in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
                return False
        except:
            return False
    return True

@app.on_message(filters.command("start"))
async def start_handler(client, message: Message):
    user_id = message.from_user.id
    users.add(user_id)
    save_data(data)

    keyboard = [[InlineKeyboardButton(btn["text"], url=btn["url"])] for btn in data.get("buttons", [])]
    keyboard.append([InlineKeyboardButton("✅ Verify", callback_data="verify")])
    sent = await message.reply(data.get("instruction", "Welcome!"), reply_markup=InlineKeyboardMarkup(keyboard))
    await asyncio.sleep(1800)
    await sent.delete()

@app.on_callback_query(filters.regex("verify"))
async def verify_callback(client, callback_query):
    user_id = callback_query.from_user.id
    if await has_joined_required(user_id):
        await callback_query.answer("You're verified! Here's your code.", show_alert=True)
        await callback_query.message.edit("🎉 Your code: `ABC123XYZ`", parse_mode="markdown")
    else:
        await callback_query.answer("❌ You must join the required channel(s) first.", show_alert=True)
        keyboard = [[InlineKeyboardButton(btn["text"], url=btn["url"])] for btn in data.get("buttons", [])]
        keyboard.append([InlineKeyboardButton("✅ Verify", callback_data="verify")])
        await callback_query.message.edit("Please join the required channel(s) and press Verify again.",
                                          reply_markup=InlineKeyboardMarkup(keyboard))

@app.on_message(filters.private & filters.user(admin_id) & filters.command("panel"))
async def admin_panel(client, message: Message):
    kb = [
        [InlineKeyboardButton("➕ Set Instruction", callback_data="set_instruction")],
        [InlineKeyboardButton("➕ Add Button", callback_data="add_button")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    await message.reply("Admin Panel", reply_markup=InlineKeyboardMarkup(kb))

@app.on_message(filters.forwarded & filters.private & filters.user(admin_id))
async def add_channel(client, message: Message):
    chat_id = message.forward_from_chat.id
    if chat_id not in data["channels"]:
        data["channels"].append(chat_id)
        save_data(data)
        await message.reply(f"Channel {chat_id} added for force join.")

@app.on_callback_query(filters.regex("set_instruction"))
async def set_instruction_cb(client, cb):
    await cb.message.edit("Send the new instruction message.")
    response = await app.listen(cb.from_user.id)
    data["instruction"] = response.text
    save_data(data)
    await response.reply("Instruction updated!")

@app.on_callback_query(filters.regex("add_button"))
async def add_button_cb(client, cb):
    await cb.message.edit("Send button text.")
    btn_text = (await app.listen(cb.from_user.id)).text
    await cb.message.reply("Now send button link.")
    btn_url = (await app.listen(cb.from_user.id)).text
    data["buttons"].append({"text": btn_text, "url": btn_url})
    save_data(data)
    await cb.message.reply("Button added!")

@app.on_callback_query(filters.regex("broadcast"))
async def broadcast_cb(client, cb):
    await cb.message.edit("Send the broadcast message.")
    response = await app.listen(cb.from_user.id)
    count = 0
    for user_id in users:
        try:
            await app.send_message(user_id, response.text, reply_markup=response.reply_markup)
            count += 1
        except:
            continue
    await cb.message.reply(f"Broadcast sent to {count} users.")

@app.on_callback_query(filters.regex("stats"))
async def stats_cb(client, cb):
    await cb.message.reply(f"👥 Total Users: {len(users)}")

app.run()
