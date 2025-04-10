from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# In-memory status store (reset on bot restart)
edit_protect_status = {}

# Command to toggle edit protection (now public)
@Client.on_message(filters.command("edit") & filters.group)
async def edit_protect_toggle(client, message: Message):
    chat_id = message.chat.id
    current = "ON" if edit_protect_status.get(chat_id) else "OFF"

    btns = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ ON", callback_data=f"editprotect_on_{chat_id}"),
            InlineKeyboardButton("❌ OFF", callback_data=f"editprotect_off_{chat_id}")
        ]]
    )

    await message.reply(f"Edit Protect is currently **{current}**.\nUse button to toggle:", reply_markup=btns)


# Handle inline button presses
@Client.on_callback_query(filters.regex(r"editprotect_(on|off)_(\-?\d+)"))
async def edit_protect_cb(client, query: CallbackQuery):
    action, chat_id = query.data.split("_")[1:]
    chat_id = int(chat_id)
    user = query.from_user

    if action == "on":
        edit_protect_status[chat_id] = True
        await query.edit_message_text(f"✅ Edit Protect enabled by {user.mention}")
    else:
        edit_protect_status[chat_id] = False
        await query.edit_message_text(f"❌ Edit Protect disabled by {user.mention}")


# Delete edited messages if protection is ON
@Client.on_edited_message(filters.group)
async def delete_edited_messages(client, message: Message):
    chat_id = message.chat.id

    if edit_protect_status.get(chat_id):  # Default is OFF
        try:
            await message.delete()
            user_mention = message.from_user.mention if message.from_user else "Unknown"
            await message.chat.send_message(f"{user_mention} ne message edit kiya tha, jo delete kar diya gaya.")
        except Exception as e:
            print(f"Error deleting edited message: {e}")