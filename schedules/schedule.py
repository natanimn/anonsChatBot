import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import UTC
from TelegramBots.anonChat.database.model import User, Subscription, get_session
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from core.util import delete_user_subscription
from core.events import lock_update
from core.state import State

async_scheduler = AsyncIOScheduler()

async def unsubscribe_premium(user_id: int):
    await delete_user_subscription(user_id)

async def add_unsubscription():
    async with get_session() as session:
        fetched = await session.execute(select(Subscription).options(selectinload(Subscription.user)))
        subscriptions: list[Subscription] = fetched.scalars()

        for subscription in subscriptions:
            if subscription.end_date < datetime.datetime.now():
                await unsubscribe_premium(subscription.user_id)
            else:
                async_scheduler.add_job(
                    unsubscribe_premium,
                    'date',
                    run_date=subscription.end_date,
                    args=(subscription.user.id,)
                )

async def unrestrict_user(user_id):
    async with get_session() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                current_state=State.RESTRICTED,
                report_count=0,
                release_date=None
            ))
        await session.commit()

async def add_unrestrict():
    async with get_session() as session:
        fetched = await session.execute(
            select(User)
            .where(User.current_state == State.RESTRICTED)
        )
        users: list[User] = fetched.scalars()

        for user in users:
            if user.release_date < datetime.datetime.now(UTC):
                await unrestrict_user(user.id)
            else:
                async_scheduler.add_job(
                    unrestrict_user,
                    'date',
                    run_date=user.release_date,
                    args=(user.id,)
                )
