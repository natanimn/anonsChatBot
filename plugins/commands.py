import asyncio
from datetime import date, timedelta
from pyrogram import Client as app, filters
from pyrogram.types import Message
from database.model import get_session, User
from keyboards import keyboard
from core.util import insert_user, search_partner, close_chat, update_user
from core.events import create_event, delete_event, get_event
from core.state import State
from cache.cache import (
    create_user_cache,
    get_user_cache,
    update_user_cache,
    get_value,
    user_exists,
    get_chat_cache,
    create_chat_cache
)
from core import check
from pyrogram.errors.rpc_error import RPCError
from core.var import COUNTRIES
from config import Config


@app.on_message(filters.private & filters.command('start'))
async def start(_, message: Message):
    user_id = message.from_user.id

    if not await user_exists(user_id):
        await insert_user(user_id)
        await create_user_cache(user_id)
        await message.reply(
            "**🌼 Welcome**\n\n"
            "❕ __To continue, you have to select your gender first__",
            reply_markup=keyboard.first_time_gender()
        )
    else:
        await message.reply(
        f"👋 **Hello {message.from_user.mention}**,\n\n"
        f"__Welcome to anonymous chat bot. I help you find a new "
        f"friend on telegram from all over the world. __\n\n"
        f"**Happy chatting! 😊**",
        reply_markup=keyboard.main()
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
        await update_user(user_id, current_state=State.NONE)
        await message.reply("**🚫 Search exited**", reply_markup=keyboard.main())
    else:
        await message.reply("**There is not chat/search to exit**")


@app.on_message(filters.private & filters.command('premium'))
async def premium(_, message: Message, **kwargs):
    user = await get_user_cache(message.from_user.id)
    if user['is_premium']:
        subscription = user['subscription']
        await message.reply(
            f"**😊 You have already subscribed to {subscription['type']} premium feature.**\n\n"
            f"📅 __It will end on {subscription['end_date']}__"
        )
    else:
        await message.reply(
            "**💫 Premium**\n\n"
            "**🔥 Unlock premium features of the bot:**\n\n"
            "1. Filtered search.\n"
            "2. Choose your partner's: gender, age and location, and match with them.\n"
            "3. Rematch with previous partner.\n"
            "4. Delete unwanted message, while chatting from you and your partner.\n"
            "5. Daily unlimited chat.**\n\n"
            "😉 __Subscribe now__",
            reply_markup=keyboard.premium_k()
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
    elif user['current_state'] in [State.RESTRICTED, State.CHATTING]:
        await chat(bot, message)

    elif user['current_state'] == State.SEARCHING_LAST_PARTNER:
        await message.reply(
            "**❗️You have already requested to the partner**\n\n"
            "__Please wait for their response__"
        )

    else:
        last_partner_id = user['last_partner_id']
        try:
            assert last_partner_id != 0
            last_partner_state = await get_value(last_partner_id, 'current_state')
            assert last_partner_state == State.NONE

        except AssertionError as e:
            if last_partner_id == 0:
                await message.reply(
                    "**❌ Partner not found.**\n\n"
                    "__Start another /chat __"
                )

            else:
                await message.reply(
                    "**Sorry**,\n\n"
                    "__Your previous partner has started chat with another person."
                    "Send /chat, and find another partner.__"
                )
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

@app.on_message(filters.private & filters.command('setting'))
async def setting(_, message: Message, **kwargs):
    await message.reply(
        f"**⚙️ Setting**\n\n"
        f"✔️ __From this menu, you can customize your profile: gender, age and country.__\n\n"
        f"**🔥 If you are premium user, you can also customize your preference.**\n"
        f"(__this will increase the matching time__)",
        reply_markup=keyboard.setting_k()
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
            if message_id:=user_chat.get(user_id, {}).get(str(reply_message.id)):
                try:
                    await bot.delete_messages(user['chatting_with'], message_id)
                except RPCError:
                    await message.reply("**❗️Unable to delete the message**")
                else:
                    await message.reply("**✅ Deleted**")
            await bot.delete_messages(user_id, reply_message.id)


@app.on_message(filters.private & filters.command(['yes', 'no']))
async def yes_no(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    state   = await get_value(user_id, 'current_state')
    request_from = await get_value(user_id, 'match_request_from')
    last_partner_id = await get_value(user_id, 'last_partner_id')
    last_partner_state = await get_value(request_from, 'current_state')

    if state == State.CHATTING:
        await message.reply("**❗️You have already started a chat**")

    elif request_from != last_partner_id or request_from == 0:
        await message.reply("**❗️No request found**")

    elif state == State.RESTRICTED:
        await message.reply("❗**You can't do this right now. You have been restricted**")
        try:
            await bot.send_message(
                request_from,
                "**❌ Sorry, the previous partner has rejected your re-match request**"
            )
        finally:
            if last_partner_state == State.SEARCHING_LAST_PARTNER:
                await update_user(request_from, current_state=State.NONE, last_partner_id=0)
            await update_user_cache(user_id, match_request_from=0)

    elif last_partner_state == State.RESTRICTED:
        await message.reply("**❗️️Unable to get the partner")
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
                    await update_user(user_id, current_state=State.NONE, last_partner_id=0)
                    await update_user(request_from, current_state=State.NONE)
            await update_user_cache(user_id, match_request_from=0)

@app.on_message(filters.command('help'))
async def help_(_, message: Message):
    await message.reply(
        f"""**🕹 Commands **\n
/start - Start message
/chat - Find a partner
/exit - For stopping the conversation
/premium - Subscribe to premium
/rechat - Connect with previous partner 💎
/delete - Delete sent message to your partner 💎
/setting- Manage profile and preference
/privacy - Privacy Policy
/help - Bot help
/rules - Rules of the chat.\n
**🔒 Security**:
<blockquote>**
- Links Blocked Permanently
- Photos and Stickers will be Allowed After 2 minutes.
- Report System**
</blockquote>
**💡 For regular users, daily chat limit is {Config.DAILY_CHAT_LIMIT}**
""",  reply_markup=keyboard.help_k())


@app.on_message(filters.command('rules'))
async def rules(_, message: Message):
    with open('rules.txt', encoding='utf-8') as file:
        await message.reply(file.read())
        file.close()

@app.on_message(filters.command('privacy'))
async def privacy(_, message: Message):
    with open('privacy.txt', encoding='utf-8') as file:
        await message.reply(file.read(), disable_web_page_preview=True)
        file.close()

@app.on_message(filters.command('paysupport'))
async def pay_support(_, message: Message):
    await message.reply(
        "**If you have any questions, do not hesitate to get in touch 👇**",
        reply_markup=keyboard.support()

    )




