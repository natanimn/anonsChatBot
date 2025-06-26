from pyrogram import Client as app, filters
from pyrogram.types import PreCheckoutQuery, Message
from core.var import PREMIUM
from core.util import update_user_subscription, update_user, delete_user_subscription
from cache.cache import get_value, create_user_cache
from datetime import timedelta, datetime, UTC
from schedules.schedule import async_scheduler
from core import check
from database.model import User, get_session


@app.on_pre_checkout_query()
async def on_pre_checkout_query(_, query: PreCheckoutQuery):
    payload = query.invoice_payload
    price   = query.total_amount
    premium = await get_value(query.from_user.id, 'premium')
    is_premium = await get_value(query.from_user.id, 'is_premium')

    try:
        assert premium is not None
        assert payload == premium.get(7)
        assert not is_premium
    except AssertionError:
        await query.answer(False, "Order not found")

    else:
        await query.answer(True)

@app.on_message(filters.successful_payment)
async def on_successful_payment(bot: app, message: Message):
    user_id = message.from_user.id
    payment = message.successful_payment
    price   = payment.total_amount
    charge_id = payment.telegram_payment_charge_id

    if price == 100:
        _type = "weekly"
        time_delta = datetime.now() + timedelta(days=7)
    elif price == 250:
        _type = "monthly"
        time_delta = datetime.now() + timedelta(days=30)
    else:
        _type = "annual"
        time_delta = datetime.now() + timedelta(days=365)
    try:
        await update_user_subscription(
                user_id,
            type=_type,
            price_in_star=price,
            end_date=time_delta
        )
    except:
        await message.reply(
            "**❌ You have already subscribed to premium**\n\n"
            "✔️ __Your money will be refunded__"
        )
        await bot.refund_star_payment(user_id, charge_id)

    else:
        await message.reply(
            "**✅ You have subscribed to premium successfully**\n\n"
            "__🔥 From now on, you can access to the bot's premium features.__"
        )

        async_scheduler.add_job(
            delete_user_subscription,
            trigger='date',
            run_date=time_delta,
            args=(user_id,)
        )