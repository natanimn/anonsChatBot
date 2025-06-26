from . import (
    app,
    filters,
    Message,
    State,
    get_value,
    close_chat,
    keyboard,
    RPCError,
    update_user
)
from core.events import delete_event

@app.on_message(filters.private & filters.command('exit'))
async def exit_chat(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    state = await get_value(user_id, 'current_state')

    if state == State.CHATTING:
        partner_id = await get_value(user_id, 'chatting_with')
        await close_chat(user_id, partner_id)
        try:
            await message.reply(
                "**🚫 You left the chat**\n\n"
                "__/chat - start new chat __\n\n"
                "__⚠️ If the partner was violate any rule, "
                "please report the activity using bellow button.__",
                reply_markup=keyboard.report_k(partner_id)
            )
            await bot.send_message(
                partner_id,
                "**🚫 Partner left the chat**\n\n"
                "__/chat - Start new chat __\n\n"
                "__⚠️ If the partner was violate any rule, "
                "please report the activity using bellow button.__",
                reply_markup=keyboard.report_k(user_id)
            )
            await bot.send_message(partner_id, '.', reply_markup=keyboard.main())
        finally:
            await message.reply('.', reply_markup=keyboard.main())

    elif state == State.SEARCHING:
        # await delete_event(user_id)
        await update_user(user_id, current_state=State.NONE)
        await message.reply("**🚫 Search exited**", reply_markup=keyboard.main())
    else:
        await message.reply("**There is not chat/search to exit**")
