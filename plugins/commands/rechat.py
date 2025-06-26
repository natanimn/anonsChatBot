from . import (
    app,
    filters,
    Message,
    get_user_cache,
    keyboard,
    get_value,
    State,
    RPCError,
    update_user_cache
)

@app.on_message(filters.private & filters.command('rechat'))
async def re_chat(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    user = await get_user_cache(user_id)
    if not user['is_premium']:
        await message.reply(
            "**☝️ Premium Subscription Required**\n\n"
            "❕__Subscribe to premium to use this feature__",
            reply_markup=keyboard.premium_k()
        )

    else:
        last_partner_id = user['last_partner_id']
        try:
            assert last_partner_id != 0
            last_partner_state = await get_value(last_partner_id, 'current_state')
            assert bool(last_partner_state | (State.CHATTING & State.RESTRICTED)) == True
            assert user['current_state'] != State.SEARCHING_LAST_PARTNER, "TF"
        except AssertionError as e:
            if last_partner_id == 0:
                await message.reply(
                    "**❌ Partner not found.**\n\n"
                    "__Start another /chat __"
                )
            elif user['current_state'] == State.SEARCHING_LAST_PARTNER:
                await message.reply(
                    "**❗️You have already requested to the partner**\n\n"
                    "__Please wait for their response__"
                )
            else:
                await message.reply(
                    "**Sorry**,\n\n"
                    "__Your previous partner started chat with another person. "
                    "Send /chat, and find another partner.__"
                )
            print(e)
        else:
            try:
                await bot.send_message(
                    last_partner_id,
                    "👥 **Your previous partner wanted to chat with you again.**\n\n"
                    "❔ __Would you like to chat with them again__?\n\n/yes or /no"
                )
            except RPCError:
                await message.reply(
                    "**❌ Partner not found.**\n\n"
                    "__Start another /chat __"
                )
            else:
                await update_user_cache(user_id, current_state=State.SEARCHING_LAST_PARTNER)
                await update_user_cache(last_partner_id, match_request_from=user_id)
                await message.reply(
                    "**🔄 Connecting you with the last partner....**\n\n"
                    "__Wait a moment__"
                )

