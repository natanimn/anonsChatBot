"""
Admin commands
"""
import asyncio
from datetime import datetime, timedelta

from pyrogram import Client as app, filters
from pyrogram.types import Message
from cache.cache import get_value, add_banned_word, get_user_cache
from core.util import (
    get_users_id,
    delete_user_subscription,
    add_user_subscription,
    update_user
)
from core import check
from pyrogram.errors import BadRequest, FloodWait, RPCError
from schedules.schedule import async_scheduler, unrestrict_user
from core.state import State

@app.on_message(filters.private & filters.create(check.admin) & filters.command('broadcast'))
async def broadcast(bot: app, message: Message):
    admin_id = message.from_user.id
    reply    = message.reply_to_message

    if not reply:
        await message.reply(
            "**This command only works with reply**\n\n"
            "__Please reply to any message you want to broadcast__"
        )
    else:
        await message.reply("**✅ Sending started..**")
        users_id = await get_users_id()
        sent_to  = 0
        for user_id in users_id:
            if sent_to == 30:
                await asyncio.sleep(1)
                sent_to = 0
            try:
                await bot.copy_message(user_id, admin_id, reply.id)
            except BadRequest:
                continue
            except FloodWait as fw:
                await asyncio.sleep(fw.value)
                try:
                    await bot.copy_message(user_id, admin_id, reply.id)
                except RPCError:
                    continue
            finally:
                sent_to += 1


@app.on_message(filters.private & filters.create(check.admin) & filters.command('refund'))
async def refund(bot: app, message: Message):
    args = message.text.split()

    if len(args) != 3:
        await message.reply(
            "**ERROR**\n\n"
            "__This command works only as:\n"
            "/refund charge_id user_id __"
        )
    else:
        charge_id, user_id = args[1:]
        try:
            await bot.refund_star_payment(int(user_id), charge_id)
            try:
                await bot.send_message(
                    int(user_id),
                    "**Dear user**,\n\n"
                    "✅ __As you have requested for star refund, your star is refunded, "
                    "and your premium subscription is stopped.__\n\n"
                    "**Thankyou for using this bot**"
                )
            except BadRequest:
                pass
            finally:
                await delete_user_subscription(int(user_id))
        except RPCError as e:
            await message.reply(
                f"**ERROR**\n\n"
                f"**Telegram says**"
                f"\n__{e.MESSAGE}__"
            )
        else:
            async_scheduler.remove_job(f"subscription-{user_id}")
            await message.reply("**✅ Star refunded successfully**")


@app.on_message(filters.private & filters.create(check.admin) & filters.command('subscribe'))
async def subscribe(bot: app, message: Message):
    args = message.text.split()
    if len(args) != 3:
        await message.reply(
            "**ERROR**\n\n"
            "__This command works only as:\n"
            "/refund user_id [w|m|y] __"
        )
    else:
        user_id, duration = args[1:]
        if not user_id.isdigit():
            return
        user_id = int(user_id)
        user = await get_value(user_id, 'id')
        if not user:
            await message.reply("User not found")
            return
        duration = duration.lower()
        if not duration in ['w', 'm', 'y']:
            await message.reply(
                "**Invalid time duration**\n\n"
                "**Duration can be only one of the following**\n"
                "__w__ - Weekly\n"
                "__m__ - Monthly\n"
                "__y__ - Yearly"
            )
        else:
            is_premium: bool = await get_value(int(user_id), 'is_premium')
            if is_premium:
                await message.reply(
                    "**This user has already subscribed to premium**"
                )
            else:
                ids = {'w': '1', 'm': '2', 'y': '3'}
                _id = ids[duration]
                try:
                    subscription = await add_user_subscription(user_id, _id)
                    async_scheduler.add_job(
                        delete_user_subscription,
                        trigger='date',
                        id=f"subscription-{user_id}",
                        run_date=subscription.end_date,
                        args=(user_id,)
                    )
                except:
                    await message.reply("**Something went wrong, please try again**")
                else:
                    try:
                        await bot.send_message(
                            user_id,
                            f"**✅ You have subscribed to {subscription.type} premium successfully**\n\n"
                            "__🔥 From now on, you can access to the bot's premium features.__\n\n"
                            "**Enjoy premium features**"
                        )
                    except BadRequest:
                        await message.reply(
                            "Cannot get the user and subscription is rolled back"
                        )
                        await delete_user_subscription(user_id)

                    else:
                        await message.reply(
                            f"**✅ {subscription.type} has been added to {user_id} successfully**"
                        )

@app.on_message(filters.private & filters.create(check.admin) & filters.command('addbword'))
async def add_banned_words(bot: app, message: Message):
    word = message.text.replace("/addbword", "")
    words = [w.strip() for w in word.split(",")]

    if not words:
        await message.reply("No word is added")
    else:
        await add_banned_word(words)
        await message.reply(f"{", ".join(words)}\n\nAdded as banned word")

@app.on_message(filters.private & filters.create(check.admin) & filters.command('ban'))
async def ban(bot: app, message: Message):
    user_id = message.text.split()[-1]

    if user_id == message.text:
        await message.reply("**ERROR**\n\n__This command only works as\n /ban user_id__")
    else:
        user  = await get_user_cache(int(user_id))

        if user is None:
            await message.reply("**User not found**")
        else:
            if user['current_state'] == State.RESTRICTED:
                await message.reply("**This user is already banned/restricted**")
            else:
                tomorrow = datetime.now() + timedelta(days=1)
                await update_user(
                    int(user_id),
                    report_count=10,
                    current_state=State.RESTRICTED,
                    release_date=tomorrow
                )
                try:
                    await bot.send_message(
                        int(user_id),
                        "**Dear user**,\n\n"
                        f"__❗️Due to rule violation, and you have been reported frequently by many users, "
                        f"you are restricted from chatting with anyone until {tomorrow}__"
                    )
                finally:
                    async_scheduler.add_job(
                        unrestrict_user,
                        'date',
                        run_date=tomorrow,
                        args=(int(user_id),),
                        id=f'ban_user-{user_id}'
                    )
                    await message.reply(f"**User has been banned until __{tomorrow}__**")


@app.on_message(filters.private & filters.create(check.admin) & filters.command('unban'))
async def unban(bot: app, message: Message):
    user_id = message.text.split()[-1]
    if user_id == message.text:
        await message.reply("**ERROR**\n\n__This command only works as:\n /unban user_id__")
    else:
        user = await get_user_cache(int(user_id))
        if user is None:
            await message.reply("**User not found**")
        else:
            if user['current_state'] != State.RESTRICTED:
                await message.reply("**This user is not banned/restricted**")
            else:
                await unrestrict_user(int(user_id))
                async_scheduler.remove_job(f'ban_user-{user_id}')
                await message.reply("**User has been unbanned successfully!**")





