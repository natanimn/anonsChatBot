import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.model import User, Subscription, get_session
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from core.util import delete_user_subscription, update_user
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
                    id=f"subscription-{subscription.user_id}",
                    run_date=subscription.end_date,
                    args=(subscription.user.id,)
                )

async def unrestrict_user(user_id):
    await update_user(user_id, current_state=State.NONE, report_count=0, release_date=None)

async def add_unrestrict():
    async with get_session() as session:
        fetched = await session.execute(
            select(User)
            .where(User.current_state == State.RESTRICTED)
        )
        users: list[User] = fetched.scalars()

        for user in users:
            if user.release_date < datetime.datetime.now():
                await unrestrict_user(user.id)
            else:
                async_scheduler.add_job(
                    unrestrict_user,
                    'date',
                    run_date=user.release_date,
                    args=(user.id,),
                    id=f'ban_user-{user.id}'
                )