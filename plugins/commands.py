import asyncio
from datetime import date, timedelta
from pyrogram import Client as app, filters
from pyrogram.errors import UserIsBlocked
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
from core.chat import add_user_to_queue, remove_user_from_queue
from core import check
from pyrogram.errors.rpc_error import RPCError
from core.var import COUNTRIES
from config import Config
from core.decorators import safe
import logging

logger = logging.getLogger("a2zdatingbot")


@app.on_message(filters.private & filters.command('start'))
@safe
async def start(bot: app, message: Message):
    user_id = message.from_user.id
    text = (f"**🌷 Welcome to {bot.me.full_name}**!\n\n"
            f"__We're excited to help you find your perfect match. "
            f"To get started, we need to know a bit about you.__\n\n"
            f"Firstly, could you please tell us your gender? "
            f"Press the button below to choose any of the below\n"
            f"- Male\n- Female\n\n"
            "__Just press the button below. We're looking forward to helping you find love!__"
            )

    user = await get_user_cache(user_id)
    if user is None:
        await insert_user(user_id)
        await create_user_cache(user_id)
        await message.reply(text, reply_markup=keyboard.first_time_gender())
    elif not user['gender']:
        await message.reply(text, reply_markup=keyboard.first_time_gender())
    else:
        await message.reply(
        f"**🌟 Welcome back**\n\n"
        f"__With this bot, you can chat with boys and girls, choosing your preferences about gender.__\n\n"
        f"The chat is 𝙎𝙚𝙘𝙧𝙚𝙩 and 𝘼𝙣𝙤𝙣𝙮𝙢𝙤𝙪𝙨, and the people you chat with have no way to understand who you really are!\n\n"
        f"Choose your preferences with 𝙎𝙚𝙩𝙩𝙞𝙣𝙜𝙨 🛠\n\n"
        f"⚠️ **Spam and illegal stuff are forbidden and punished with a ban..**\n\n"
        f"**Happy chatting! 😊**",
        reply_markup=keyboard.main()
    )

@app.on_message(filters.private & filters.create(check.is_new))
@safe
async def on_new_user(bot: app, message: Message):
    if bot.me.id == message.from_user.id:
        return

    user = await get_user_cache(message.from_user.id)

    if user is None:
        await start(bot, message)
    elif not user['gender']:
        await start(bot, message)
    else:
        await message.reply(
            "❕**__Please select your country__**",
            reply_markup=keyboard.first_time_country()
        )

@app.on_message(filters.private & filters.command('chat'))
@safe
async def chat(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    cache = await get_user_cache(user_id)
    state = cache['current_state']
    closed_date = cache['chat_closed_date']

    if closed_date != date.today():
        await update_user(user_id, chat_count=0, chat_closed_date=date.today())

    limit = await get_value(user_id, 'chat_count')

    if state == State.RESTRICTED:
        await message.reply(
            "**❗️Due to violation of rules,** "
            f"__you have been restricted from chatting with anyone until {cache['release_date']}__"
        )
    elif limit >= Config.DAILY_CHAT_LIMIT:
        await message.reply(
            f"❌ **Oops, you have finished your daily free {Config.DAILY_CHAT_LIMIT} chat package.**\n\n"
            "❕ __Please come again tomorrow or subscribe to **/premium**.__"
        )
        await update_user(user_id, current_state=State.NONE)

    elif state == State.CHATTING:
        await message.reply(
            "**❗️You are already in chat**\n\n"
            "__Send /exit to exit current chat.__",
        )

    elif state == State.SEARCHING:
        await message.reply(
            "❗️We are already searching for you a partner\n\n"
            "__Send /exit to exit current chat.__",
        )
    else:
        await update_user(user_id, current_state=State.SEARCHING)
        await message.reply(
            "🔎 __Searching for a partner__",
        )
        await add_user_to_queue(user_id)

        # event = await create_event(user_id) # create an event first
        # task  = asyncio.create_task(search_partner(user_id))
        # matched_user = await task
        #
        # if event.is_set():
        #     user = await get_user_cache(user_id)
        #     if not matched_user and user['current_state'] == State.SEARCHING:
        #         try:
        #             await message.reply(
        #                 "😞 __Sorry, we could not get any partner for you, "
        #                 "based on your current preference__\n\n"
        #                 "❕ **Change your current preference, and try again**",
        #                 reply_markup=keyboard.main()
        #             )
        #         finally:
        #             await update_user(user_id, current_state=State.NONE)
        #             await delete_event(user_id)
        #
        #     elif matched_user:
        #         new_state = user['current_state']
        #         partner_state = matched_user['current_state']
        #
        #         if new_state == State.CHATTING and partner_state == State.CHATTING:
        #             partner_country = ''
        #             partner_region = ''
        #             user_country = ''
        #             user_region = ''
        #
        #             if matched_user['country'] or user['country']:
        #                 for k, v in  COUNTRIES.items():
        #                     if matched_user['country'] == v:
        #                         partner_country = k
        #                     if user['country'] == v:
        #                         user_country = k
        #
        #             if matched_user['india_region']:
        #                 partner_region = matched_user['india_region']
        #
        #             if user['india_region']:
        #                 user_region = user['india_region']
        #
        #             partner_full_country = partner_country + ('/' +  partner_region if partner_region else '')
        #             user_full_country = user_country + ('/' + user_region if user_region else '')
        #             partner_id = matched_user['id']
        #             try:
        #                 age = 'Unknown' if int(matched_user['age']) == 0 else matched_user['age']
        #                 gender = matched_user['gender'] if user['is_premium'] else '||For Premium||'
        #                 await message.reply(
        #                     "**✅ Partner found**\n\n"
        #                     f"**🔢 __Age: {age}\n__**"
        #                     f"**👥 __Gender: {gender}__**\n"
        #                     f"**🌍 __Country: {partner_full_country}__**\n\n"
        #                     f"🚫 **Links are blocked**.\n"
        #                     f"__✔️ You can send media after 2 minutes__\n\n"
        #                     f"**/exit - Leave Partner**",
        #
        #                 )
        #             except UserIsBlocked:
        #                 try:
        #                     await bot.send_message(
        #                         partner_id,
        #                         "**Error**\n\n"
        #                         "__The partner we have found you just blocked the bot.\n\n"
        #                         "Send /chat and find new partner__",
        #                     )
        #                 finally:
        #                     await asyncio.gather(
        #                         update_user(user_id,
        #                                     current_state=State.NONE,
        #                                     last_partner_id=partner_id,
        #                                     chatting_with=0),
        #                         update_user(partner_id,
        #                                     current_state=State.NONE,
        #                                     last_partner_id=user_id,
        #                                     chatting_with=0)
        #                     )
        #                     for _id in [partner_id, user_id]:
        #                         await delete_event(_id)
        #             else:
        #                 try:
        #                     age = 'Unknown' if int(user['age']) == 0 else user['age']
        #                     gender = user['gender'] if matched_user['is_premium'] else '||For Premium||'
        #                     await bot.send_message(
        #                         partner_id,
        #                         "**✅ Partner found**\n\n"
        #                         f"**🔢 __Age: {age}\n__**"
        #                         f"**👥 __Gender: {gender}__**\n"
        #                         f"**🌍 __Country: {user_full_country}__**\n\n"
        #                         f"🚫 **Links are blocked**.\n"
        #                         f"__✔️ You can send media after 2 minutes__\n\n"
        #                         f"**/exit - Leave Partner**",
        #                     )
        #                 except UserIsBlocked:
        #                     try:
        #                         await message.reply(
        #                             "**Error**\n\n"
        #                             "__The partner we have found you just blocked the bot.\n\n"
        #                             "Send /chat and find new partner__",
        #                         )
        #                     finally:
        #                         await asyncio.gather(
        #                             update_user(user_id,
        #                                         current_state=State.NONE,
        #                                         last_partner_id=partner_id,
        #                                         chatting_with=0),
        #                             update_user(partner_id,
        #                                         current_state=State.NONE,
        #                                         last_partner_id=user_id,
        #                                         chatting_with=0)
        #                         )
        #                         for _id in [partner_id, user_id]:
        #                             await delete_event(_id)
        #
        #     await delete_event(user_id) # Event needed no more, delete it
        #     await asyncio.sleep(1)


@app.on_message(filters.private & filters.command('exit'))
@safe
async def exit_chat(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    state = await get_value(user_id, 'current_state')

    if state == State.CHATTING:
        partner_id = await get_value(user_id, 'chatting_with')
        await close_chat(user_id, partner_id)
        try:
            await bot.send_message(
                partner_id,
                "**🚫 Partner left the chat**\n\n"
                "__/chat - Start new chat __\n\n"
                "__⚠️ If the partner violated any rule or commited illegal activity, "
                "please report the user using bellow button.__",
                reply_markup=keyboard.report_k(user_id)
            )
        finally:
            await message.reply(
                "**🚫 You left the chat**\n\n"
                "__/chat - start new chat __\n\n"
                "__⚠️ If the partner violated any rule or commited illegal activity, "
                "please report the user using bellow button.__",
                reply_markup=keyboard.report_k(partner_id)
            )

    elif state == State.SEARCHING:
        await asyncio.gather(
            remove_user_from_queue(user_id),
            update_user(user_id, current_state=State.NONE)
        )
        await message.reply("**🚫 Search exited**", reply_markup=keyboard.main())
        
    else:
        await message.reply("**There is not chat/search to exit**")


@app.on_message(filters.private & filters.command('premium'))
@safe
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
@safe
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
            except UserIsBlocked:
                await message.reply(
                    "**❌ Partner not found.**\n\n"
                    "__Start another /chat __"
                )
                await update_user(user_id, last_partner_id=0)
            else:
                await update_user_cache(user_id, current_state=State.SEARCHING_LAST_PARTNER)
                await update_user_cache(last_partner_id, match_request_from=user_id)
                await message.reply(
                    "**🔄 Connecting you with the last partner....**\n\n"
                    "__Wait a moment__"
                )

@app.on_message(filters.private & filters.command('setting'))
@safe
async def setting(_, message: Message, **kwargs):
    user_id = message.from_user.id
    limit = await get_value(user_id, 'chat_count')
    is_premium = await get_value(user_id, 'is_premium')
    lim_text = f"**__You have used __{limit}__ out of {Config.DAILY_CHAT_LIMIT} your daily chat limit.__**" \
        if not is_premium else "**__Enjoy your unlimited daily chat__**"
    await message.reply(
        f"**⚙️ Setting**\n\n"
        f"✔️ __From this menu, you can customize your profile: gender, age and country.__\n\n"
        f"{lim_text}",
        reply_markup=keyboard.setting_k()
    )


@app.on_message(filters.private & filters.command("delete"))
@safe
async def delete(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    user = await get_user_cache(user_id)
    if not user['is_premium']:
        await message.reply(
            "**☝️ Premium Subscription Required**\n\n"
            "❕__Subscribe to premium to use this feature__",
            reply_markup=keyboard.premium_k()
        )

    elif not message.reply_to_message:
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
@safe
async def yes_no(bot: app, message: Message, **kwargs):
    user_id = message.from_user.id
    state   = await get_value(user_id, 'current_state')
    request_from = await get_value(user_id, 'match_request_from')
    last_partner_state = await get_value(request_from, 'current_state')

    if state == State.CHATTING:
        await message.reply("**❗️You have already started a chat**")

    elif request_from == 0:
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
                    )

                except UserIsBlocked:
                    await message.reply("**❗️️Unable to get the partner")
                    await update_user(request_from, current_state=State.NONE, last_partner_id=0)
                else:
                    await create_chat_cache(user_id, request_from)
                    await asyncio.gather(
                        update_user(user_id, current_state=State.CHATTING, chatting_with=request_from),
                        update_user(request_from, current_state=State.CHATTING, chatting_with=user_id)
                    )
                    await message.reply("**✅ Re matched**")
            else:
                await message.reply("**🚫 Partner blocked**")
                try:
                    await bot.send_message(
                        request_from,
                        "**❌ Sorry, the previous partner rejected your re-match request**"
                    )
                except UserIsBlocked as e:
                    logger.error(e)
                finally:
                    await asyncio.gather(
                        update_user(user_id, current_state=State.NONE),
                        update_user(request_from, current_state=State.NONE, last_partner_id=0)
                    )
            await update_user_cache(user_id, match_request_from=0)

@app.on_message(filters.command('help'))
@safe
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
@safe
async def rules(_, message: Message):
    with open('./privacy_and_rules/rules.txt', encoding='utf-8') as file:
        await message.reply(file.read())
        file.close()

@app.on_message(filters.command('privacy'))
@safe
async def privacy(_, message: Message):
    with open('./privacy_and_rules/privacy.txt', encoding='utf-8') as file:
        await message.reply(file.read(), disable_web_page_preview=True)
        file.close()

@app.on_message(filters.command('paysupport'))
@safe
async def pay_support(_, message: Message):
    await message.reply(
        "**If you have any questions, do not hesitate to get in touch 👇**",
        reply_markup=keyboard.support()

    )

@app.on_message(filters.command("developer"))
async def developer(_, message: Message):
    text = """**🤖 Bot Developer**
    
**Whether you need a:**
🤖 Customer service bot
👨‍👩‍👧‍👦 Group/channel moderation bot
💰 Airdrop or crypto campaign bot
💬 Anonymous Chatting bot
🌐 Full-featured web app integration

🔧 **What I Offer:**
__
▫️API integrations with any platform
▫️Admin panels & user management systems
▫️Secure payment gateway integration
▫️Hosting + deployment
▫️Clean, scalable Python code
▫️Long term support & updates
__

✅ **My bots are:**

Fast ⚡️
Secure 🔐
Easy to use 🎯
Fully documented 📄

📩 **DM me if you're looking for:**

✅ A serious developer (not a script copier)
✅ Someone who understands your goals
✅ A custom solution, not a one size fits all template

DM @Natiprado
"""
    await message.reply(text)

