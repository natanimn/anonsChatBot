from . import (
    app,
    filters,
    Message,
    get_value,
    State,
    get_user_cache,
    RPCError,
    update_user,
    update_user_cache,
    create_chat_cache,
    keyboard
)

@app.on_message(filters.private & filters.command(['yes', 'no']))
async def yes_no(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    state   = await get_value(user_id, 'current_state')
    request_from = await get_value(user_id, 'match_request_from')
    last_partner_id = await get_value(user_id, 'last_partner_id')

    if state == State.CHATTING:
        await message.reply("**❗️You have already started a chat**")

    elif request_from != last_partner_id or request_from == 0:
        await message.reply("**❗️No previous partner found**")

    elif state == State.RESTRICTED:
        await message.reply("❗**You can't do this now. You have been restricted**")
        try:
            await bot.send_message(
                request_from,
                "**❌ Sorry, the previous partner rejected your re-match request**"
            )
        finally:
            await update_user(user_id, current_state=State.CHATTING, chatting_with=request_from)
            await update_user_cache(user_id, match_request_from=0)

    else:
        partner = await get_user_cache(request_from)
        if partner['current_state'] != State.SEARCHING_LAST_PARTNER:
            await message.reply(
                "**❕Your previous has already partner started "
                "another chat with another partner **"
            )
        else:
            if message.text == '/yes':
                try:
                    await message.reply("__Connecting you ...__")
                    await bot.send_message(
                        request_from,
                        "**✅ Your previous partner accepted your re-match request**\n\n"
                        "__From now on, you can message them__.",
                        reply_markup=keyboard.exit_k()
                    )

                except RPCError:
                    await message.reply("**❗️️Unable to get the partner")
                    await update_user(request_from, current_state=State.NONE, chatting_with=user_id)
                else:
                    await message.reply("**✅ Re matched**", reply_markup=keyboard.exit_k())
                    await create_chat_cache(user_id, request_from)
                    await update_user(user_id, current_state=State.CHATTING, chatting_with=request_from)
                    await update_user(request_from, current_state=State.CHATTING, chatting_with=user_id)

            else:
                await message.reply("**🚫 Partner blocked**")
                try:
                    await bot.send_message(
                        request_from,
                        "**❌ Sorry, the previous partner rejected your re-match request**"
                    )
                except RPCError: pass
                finally:
                    await update_user(user_id, current_state=State.NONE)
                    await update_user(request_from, current_state=State.NONE)
            await update_user_cache(user_id, match_request_from=0)
