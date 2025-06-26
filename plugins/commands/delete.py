from . import (
    app,
    filters,
    Message,
    get_user_cache,
    State,
    keyboard,
    get_value,
    get_chat_cache,
    RPCError
)

@app.on_message(filters.private & filters.command("delete"))
async def delete(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    user = await get_user_cache(user_id)
    if not user['is_premium']:
        await message.reply(
            "**☝️ Premium Subscription Required**\n\n"
            "❕__Subscribe to premium to use this feature__",
            reply_markup=keyboard.premium_k()
        )
        return

    if not message.reply_to_message:
        await message.reply(
            "❗️ __Please reply to your message you want to delete from your partner"
        )
    else:
        if user['current_state'] != State.CHATTING:
            await message.reply("❗️ **You can only delete message in active chat**")
        else:
            user_chat = await get_chat_cache(user_id, user['chatting_with'])
            reply_message = message.reply_to_message
            if message_id:=user_chat(user_id, {}).get(str(reply_message.id)):
                try:
                    await bot.delete_messages(user['chatting_with'], message_id)
                except RPCError:
                    await message.reply("**❗️Unable to delete the message**")
                else:
                    await message.reply("**✅ Deleted**")
            await bot.delete_messages(user_id, reply_message.id)
