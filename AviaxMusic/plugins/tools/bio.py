
from AviaxMusic import app
import re
from pyrogram import Client, filters, enums, errors
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions

# Improved Regex Patterns
url_pattern = re.compile(
    r"(https?://|www\.)"              # http://, https:// or www.
    r"[a-zA-Z0-9.-]+"                 # domain name
    r"\.[a-zA-Z]{2,}"                 # top-level domain
    r"([/?][^\s]*)?"                  # optional path/query string
)
username_pattern = re.compile(r"@[\w]{5,32}")  # Telegram usernames are 5–32 characters

# Configurations
warnings = {}  # user_id: warning_count
default_warning_limit = 3
default_punishment = "mute"
approved_users = {5738579437, 6258915779, 8093150680}

# Toggle per group
bio_protection_enabled = {}  # Keeps bio protector ON/OFF per group

@app.on_message(filters.command("bio_protect") & filters.group)
async def toggle_bio_protection(client, message):
    chat_id = message.chat.id

    if not await is_admin(client, chat_id, message.from_user.id):
        return await message.reply_text("❌ You must be an admin to use this command.")

    current = bio_protection_enabled.get(chat_id, True)
    new_status = not current
    bio_protection_enabled[chat_id] = new_status

    status = "✅ Enabled" if new_status else "❌ Disabled"
    button_text = "Turn OFF" if new_status else "Turn ON"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(button_text, callback_data=f"toggle_bio_{chat_id}")]
    ])
    await message.reply_text(f"Bio Link Protector is now: <b>{status}</b>", reply_markup=keyboard)

@app.on_callback_query(filters.regex("toggle_bio_"))
async def toggle_bio_callback(client, callback_query):
    chat_id = int(callback_query.data.split("_")[2])
    user_id = callback_query.from_user.id

    if not await is_admin(client, chat_id, user_id):
        return await callback_query.answer("❌ You are not an admin.", show_alert=True)

    current = bio_protection_enabled.get(chat_id, True)
    new_status = not current
    bio_protection_enabled[chat_id] = new_status

    status = "✅ Enabled" if new_status else "❌ Disabled"
    button_text = "Turn OFF" if new_status else "Turn ON"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(button_text, callback_data=f"toggle_bio_{chat_id}")]
    ])

    await callback_query.message.edit(f"Bio Link Protector is now: <b>{status}</b>", reply_markup=keyboard)
    await callback_query.answer("Settings updated.")

@app.on_message(filters.group)
async def check_bio(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if protection is enabled
    if not bio_protection_enabled.get(chat_id, True):
        return

    if await is_admin(client, chat_id, user_id) or user_id in approved_users:
        return

    try:
        user_info = await client.get_chat(user_id)
    except Exception:
        return  # Ignore users that can't be fetched

    bio = user_info.bio
    user_name = f"@{user_info.username} [<code>{user_id}</code>]" if user_info.username else f"{user_info.first_name} [<code>{user_id}</code>]"

    if bio and (re.search(url_pattern, bio) or re.search(username_pattern, bio)):
        try:
            await message.delete()
        except errors.MessageDeleteForbidden:
            await message.reply_text("Pʟᴇᴀsᴇ Gʀᴀɴᴛ Mᴇ Dᴇʟᴇᴛᴇ Pᴇʀᴍɪssɪᴏɴ.")
            return

        warnings[user_id] = warnings.get(user_id, 0) + 1
        sent_msg = await message.reply_text(f"{user_name} ⚠️ Warning {warnings[user_id]}/{default_warning_limit}. Remove bio links or get muted.")

        if warnings[user_id] >= default_warning_limit:
            try:
                await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Unmute", callback_data=f"unmute_{user_id}")]])
                await sent_msg.edit(f"{user_name} has been 🔇 Muted for violating bio rules.", reply_markup=keyboard)
            except errors.ChatAdminRequired:
                await sent_msg.edit("❌ I don't have permission to mute users.")

@app.on_callback_query(filters.regex("unmute_"))
async def handle_unmute(client, callback_query):
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    if not await is_admin(client, chat_id, user_id):
        return await callback_query.answer("❌ You are not an admin.", show_alert=True)

    target_user_id = int(callback_query.data.split("_")[1])
    try:
        await client.restrict_chat_member(chat_id, target_user_id, ChatPermissions(can_send_messages=True))
        await callback_query.message.edit(f"✅ Unmuted user <code>{target_user_id}</code>", parse_mode=enums.ParseMode.HTML)
    except errors.ChatAdminRequired:
        await callback_query.message.edit("❌ I don't have permission to unmute users.")
    await callback_query.answer()