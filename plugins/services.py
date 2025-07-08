from pyrogram import Client as app, filters
from pyrogram.types import PreCheckoutQuery, Message
from core.var import PREMIUM
from core.util import add_user_subscription, delete_user_subscription
from cache.cache import get_value, create_user_cache
from schedules.schedule import async_scheduler
from core import check
from database.model import User, get_session
from config import Config
from core import safe

@app.on_pre_checkout_query()
async def on_pre_checkout_query(_, query: PreCheckoutQuery):
    price   = query.total_amount
    # premium = await get_value(query.from_user.id, 'premium')
    is_premium = await get_value(query.from_user.id, 'is_premium')

    try:
        # assert premium is not None
        assert not is_premium
    except AssertionError:
        await query.answer(False, "You have already subscribed to premium")

    else:
        await query.answer(True)

@app.on_message(filters.successful_payment)
@safe
async def on_successful_payment(bot: app, message: Message):
    user_id = message.from_user.id
    payment = message.successful_payment
    charge_id = payment.telegram_payment_charge_id
    try:
        subscription = await add_user_subscription(user_id, payment.invoice_payload)
        async_scheduler.add_job(
            delete_user_subscription,
            trigger='date',
            id=f"subscription-{user_id}",
            run_date=subscription.end_date,
            args=(user_id,)
        )
    except Exception:
        await message.reply(
            "**❌ Something went wrong with subscription**\n\n"
            "✔️ __Your money will be refunded__"
        )
        await bot.refund_star_payment(user_id, charge_id)

    else:
        await message.reply(
            "**✅ You have subscribed to premium successfully**\n\n"
            "__🔥 From now on, you can access to the bot's premium features.__\n\n"
            "**Enjoy premium features**"
        )
        await bot.send_message(
            Config.PREMIUM_CHANNEL_ID,
            "**🔥 New Premium Subscription Added**\n\n"
            f"**By**: {message.from_user.mention}\n"
            f"**User ID**: <code>{message.from_user.id}</code>\n"
            f"**Subscription Type**: __{subscription.type}__\n"
            f"**Telegram charge id**: <code>{payment.telegram_payment_charge_id}</code>"
        )



