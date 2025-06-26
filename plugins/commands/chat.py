import asyncio
from . import (
    app,
    filters,
    Message,
    get_user_cache,
    date,
    update_user_cache,
    State,
    keyboard,
    update_user,
    create_event,
    search_partner,
    delete_event,
    get_value,
    COUNTRIES,
    Config
)


@app.on_message(filters.private & filters.command('chat'))
async def chat(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    cache = await get_user_cache(user_id)
    state = cache['current_state']
    limit = cache['chat_count']
    closed_date = cache['chat_closed_date']
    is_premium = cache['is_premium']

    if closed_date != date.today():
        await update_user(user_id, chat_count=0, chat_closed_date=date.today())

    if state == State.RESTRICTED:
        await message.reply(
            "**❗️Due to violation of rules,** "
            f"__you have been restricted from chatting with anyone until {cache['release_date']}__"
        )
    elif limit == Config.DAILY_CHAT_LIMIT:
        await message.reply(
            f"❌ **Oops, you have reached your daily free {Config.DAILY_CHAT_LIMIT} chat package.**\n\n"
            "❕ __Please come again tomorrow or subscribe to **/premium**.__"
        )
        await update_user(user_id, current_state=State.NONE)

    elif state == State.CHATTING:
        await message.reply(
            "**❗️You are already in chat**\n\n"
            "__Press the the bellow button, or send /exit to exit current chat.__",
            reply_markup=keyboard.exit_k()
        )

    elif state == State.SEARCHING:
        await message.reply(
            "❗️We are already searching for you a partner\n\n"
            "__Press the the bellow button, or send /exit to exit current chat.__",
            reply_markup=keyboard.exit_k()
        )
    else:
        await update_user(user_id, current_state=State.SEARCHING)
        await message.reply(
            "🔎 __Searching for a partner__",
            reply_markup=keyboard.exit_k()
        )
        event = await create_event(user_id) # create an event first
        man, matched_user = await search_partner(user_id)
        user         = await get_user_cache(user_id)

        if event.is_set():
            if not matched_user and user['current_state'] == State.SEARCHING:
                await message.reply(
                    "😞 __Sorry, we could not get any partner for you, based on your current preference__\n\n"
                    "❕ **Change your current preference, and try again**",
                    reply_markup=keyboard.main()
                )
                await update_user(user_id, current_state=State.NONE)

            elif matched_user :
                new_state = await get_value(user_id, 'current_state')
                partner_state = await get_value(matched_user.id, 'current_state')

                if new_state == State.CHATTING and partner_state == State.CHATTING:
                    partner_country = ''
                    partner_region = ''
                    user_country = ''
                    user_region = ''

                    if matched_user.country or user['country']:
                        for k, v in  COUNTRIES.items():
                            if matched_user.country == v:
                                partner_country = k
                            if user['country'] == v:
                                user_country = k

                    if matched_user.india_region:
                        partner_region = matched_user.india_region

                    if user['india_region']:
                        user_region = user['india_region']

                    partner_full_country = partner_country + ('/' +  partner_region if partner_region else '')
                    user_full_country = user_country + ('/' + user_region if user_region else '')

                    await message.reply(
                        "**✅ Partner found**\n\n"
                        f"**🔢 Age**: {matched_user.age or ''}\n"
                        f"**👥 Gender**: {matched_user.gender if user['is_premium'] else '||VIP||' }\n"
                        f"**🌍 Country**: {partner_full_country}\n\n"
                        f"🚫 **Links are blocked**.\n"
                        f"__✔️ You can send media after 2 minutes__\n\n"
                        f"**/exit - Leave Partner**",
                        reply_markup=keyboard.exit_k()
                    )

                    await bot.send_message(
                        matched_user.id,
                        "**✅ Partner found**\n\n"
                        f"**🔢 Age**: {user['age'] or ''}\n"
                        f"**👥 Gender**: {user['gender'] if matched_user.is_premium else '||VIP||'}\n"
                        f"**🌍 Country**: {user_full_country}\n\n"
                        f"🚫 **Links are blocked**.\n"
                        f"__✔️ You can send media after 2 minutes__\n\n"
                        f"**/exit - Leave Partner**",
                        reply_markup=keyboard.exit_k()
                    )
            await delete_event(user_id) # Event needed no more, delete it
            await asyncio.sleep(1)
