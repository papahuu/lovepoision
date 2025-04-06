import re
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from AviaxMusic import app

# Regex to detect URLs or Telegram usernames
URL_REGEX = re.compile(r"(https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
USERNAME_REGEX = re.compile(r"@[\w]{5,32}")

# Settings
bio_protection_enabled = {}  # group_id: bool
warnings = {}  # (chat_id, user_id): count
warning_limit = 3
approved_users = {5738579437, 6258915779, 8093150680}  # bot owner IDs

# Admin checker
async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

@app.on_message(filters.command("bio_protect") & filters.group)
async def toggle_bio_protect(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        return await message.reply("❌ You must be an admin to toggle bio protection.")

    current = bio_protection_enabled.get(chat_id, False)
    bio_protection_enabled[chat_id] = not current

    status = "Enabled ✅" if not current else "Disabled ❌"
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton("Toggle", callback_data=f"toggle_bio_{chat_id}")]
    ])
    await message.reply(f"Bio Link Protection: <b>{status}</b>", reply_markup=button)

@app.on_callback_query(filters.regex(r"toggle_bio_"))
async def toggle_bio_callback(client, query):
    chat_id = int(query.data.split("_")[2])
    user_id = query.from_user.id

    if not await is_admin(client, chat_id, user_id):
        return await query.answer("❌ You're not an admin.", show_alert=True)

    current = bio_protection_enabled.get(chat_id, False)
    bio_protection_enabled[chat_id] = not current
    status = "Enabled ✅" if not current else "Disabled ❌"

    await query.message.edit(f"Bio Link Protection: <b>{status}</b>", reply_markup=query.message.reply_markup)
    await query.answer("Status updated!")

@app.on_message(filters.group)
async def bio_link_watcher(client, message):
    chat_id = message.chat.id
    user = message.from_user

    if not bio_protection_enabled.get(chat_id, False):
        return

    if not user or await is_admin(client, chat_id, user.id) or user.id in approved_users:
        return

    try:
        full_user = await client.get_users(user.id)
        bio = full_user.bio or ""
    except:
        return

    if URL_REGEX.search(bio) or USERNAME_REGEX.search(bio):
        try:
            await message.delete()
        except:
            return await message.reply("❌ Please give me delete permission!")

        key = (chat_id, user.id)
        warnings[key] = warnings.get(key, 0) + 1

        if warnings[key] >= warning_limit:
            try:
                await client.restrict_chat_member(chat_id, user.id, ChatPermissions())
                button = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Unmute", callback_data=f"unmute_{user.id}")]])
                return await message.reply(f"<b>{user.mention} has been muted due to bio links.</b>", reply_markup=button)
            except:
                return await message.reply("❌ I can't mute users. Promote me as admin.")
        else:
            return await message.reply(f"<b>{user.mention} Warning {warnings[key]}/{warning_limit}</b>\nRemove links from your bio.")

@app.on_callback_query(filters.regex(r"unmute_"))
async def unmute_callback(client, query):
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    if not await is_admin(client, chat_id, user_id):
        return await query.answer("❌ You're not an admin.", show_alert=True)

    target_id = int(query.data.split("_")[1])
    try:
        await client.restrict_chat_member(chat_id, target_id, ChatPermissions(can_send_messages=True))
        await query.message.edit(f"✅ User <code>{target_id}</code> has been unmuted.")
    except:
        await query.message.edit("❌ Unable to unmute. Do I have admin rights?")
    await query.answer()