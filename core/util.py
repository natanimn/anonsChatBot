import asyncio
import datetime
import json
import os
import time
from sqlalchemy import update, func, select, text, case
from sqlalchemy import and_, or_
from sqlalchemy.orm import selectinload
from .events import get_event, lock_search, lock_update, get_user_lock
from .state import State
from cache.cache import (
    update_user_cache,
    get_user_cache,
    get_value,
    delete_chat_history,
    create_chat_cache,
    get_banned_words
)
from database.model import (
    User,
    get_session,
    Preference,
    Subscription,
    async_session
)
import logging

logger = logging.getLogger('a2zdatingbot')

async def insert_user(user_id: int) -> User:
    """
    Insert user to a database
    :param user_id:
    :return User:
    """
    async with get_session() as session:
        user = User(id=user_id)
        session.add(user)
        await session.commit()
        return user

async def search_partner(user_id: int) -> dict | None:
    """
    Search a partner for user on a given event ooop
    :param user_id:
    :param event:
    :return:
    """
    event: asyncio.Event = await get_event(user_id)
    async with (get_session() as session):
        timeout = int(os.getenv('TIMEOUT', 120))
        matched_scalar, matched_scalar_id = None, None
        start = time.time()
        user  = await get_user_cache(user_id)
        attempts = 0

        while not event.is_set() and time.time() < start + timeout and user['current_state'] == State.SEARCHING:
            async with lock_search:
                user = await get_user_cache(user_id)
                preference = user['preference']

                if user['current_state'] != State.SEARCHING:
                    break

                filters = [
                    User.id != user_id,
                    User.current_state == State.SEARCHING,
                    User.last_partner_id != user_id,
                    User.id != user['last_partner_id']
                ]

                if user['is_premium']:
                    if countries := preference.get('country'):
                        filters.append(User.country.in_(countries))
                    if min_age := preference.get('min_age'):
                        filters.append(User.age >= int(min_age))
                    if max_age := preference.get('max_age'):
                        filters.append(User.age <= int(max_age))
                    if gender := preference.get('gender'):
                       filters.append(User.gender == gender)
                    if 'india' in preference.get('country', []) and preference.get('india_region', []):
                        regions = preference.get('india_region')
                        filters.append(
                            or_(
                                and_(
                                    User.country == "india",
                                    User.india_region.in_(regions)
                                ),
                                User.india_region.is_(None)
                            )
                        )

                filters.append(
                    or_(
                        User.is_premium == False,
                        and_(
                            User.is_premium == True,
                            or_(
                                ~User.preference.has(),
                                and_(
                                    User.preference.has(
                                        or_(
                                            Preference.gender == user['gender'],
                                            Preference.gender.is_(None)
                                        )
                                    ),
                                    User.preference.has(
                                        or_(
                                            Preference.min_age >= int(user['age']),
                                            Preference.min_age.is_(None)
                                        )
                                    ),
                                    User.preference.has(
                                        or_(
                                            Preference.max_age <= int(user['age']),
                                            Preference.max_age.is_(None)
                                        )
                                    ),
                                    User.preference.has(
                                        or_(
                                            Preference.country.any(user['country']),
                                            func.cardinality(Preference.country) == 0
                                        )
                                    ),
                                    User.preference.has(
                                        or_(
                                            Preference.india_region.any(user['india_region']),
                                            func.cardinality(Preference.india_region) == 0
                                        )
                                    )
                                )
                            )
                        )
                    )
                )

                matched = await session.execute(
                    select(User.id)
                    .where(and_(*filters))
                    .order_by(func.random())
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                matched_scalar_id = matched.scalar_one_or_none()
                matched_scalar    = await get_user_cache(matched_scalar_id)
                if (
                        matched_scalar and
                        matched_scalar['current_state'] == State.SEARCHING and
                        user['current_state'] == State.SEARCHING
                ):
                    try:
                        partner_id = matched_scalar_id
                        m_event = await get_event(partner_id)
                        if not m_event:
                            await session.execute(
                                update(User)
                                .where(User.id == partner_id)
                                .values(current_state=State.NONE)
                            )
                            await session.commit()
                            matched_scalar = None
                            continue

                        elif m_event.is_set():
                            matched_scalar = None
                            continue

                        if not user['is_premium']:
                            count = user['chat_count'] + 1
                        else:
                            count = 0

                        if not matched_scalar['is_premium']:
                            p_count = matched_scalar['chat_count'] + 1
                        else:
                            p_count = 0

                        user_kwargs = dict(
                            current_state=State.CHATTING,
                            chatting_with=partner_id,
                            chat_count=count
                        )
                        partner_kwargs = dict(
                            current_state=State.CHATTING,
                            chatting_with=user_id,
                            chat_count=p_count
                        )

                        await session.execute(
                            update(User)
                            .where(User.id == user_id)
                            .values(**user_kwargs)
                        )

                        await session.execute(
                            update(User)
                            .where(User.id == partner_id)
                            .values(**partner_kwargs)
                        )

                        await session.commit()

                        await create_chat_cache(user_id, partner_id)

                        user_kwargs['match_request_from'] = 0
                        partner_kwargs['match_request_from'] = 0
                        await asyncio.gather(
                            update_user_cache(user_id, **user_kwargs),
                            update_user_cache(partner_id, **partner_kwargs)
                        )

                    except Exception as e:
                        logger.error(e)
                        continue

                    event.set()
                    break
                wait = min(0.1 + attempts*0.1 , 5)
                await asyncio.sleep(0.1)
                attempts += 1

        if not event.is_set():
            event.set()

        if matched_scalar:
            matched_scalar['current_state'] = State.CHATTING
            m_event = await get_event(matched_scalar['id'])
            if m_event:
                m_event.set()

        return matched_scalar


async def close_chat(user_id, partner_id):
    """
    Close the current chat
    :param user_id:
    :param partner_id:
    :return:
    """
    await asyncio.gather(
        update_user(int(partner_id), chatting_with=0, current_state=State.NONE, last_partner_id=user_id),
        update_user(user_id, chatting_with=0, current_state=State.NONE, last_partner_id=int(partner_id)),
        delete_chat_history(user_id, partner_id)
    )

async def update_user(user_id, **kwargs):
    """
    Update user
    :param user_id:
    :param kwargs:
    :return:
    """
    user_id = int(user_id)
    await update_user_cache(user_id, **kwargs)

    async with lock_update:
        async with async_session() as session:
            try:
                stmt = (
                    update(User)
                    .where(User.id == user_id)
                    .values(**kwargs)
                )
                await session.execute(stmt)
                await session.commit()
            except Exception as e:
                logger.error(f"Error updating user {user_id}: {e}")


async def update_user_preference(user_id, **kwargs):
    """
    Update user
    :param user_id:
    :param kwargs:
    :return:
    """

    async with lock_update:
        async with get_session() as session:
            preference = await get_value(user_id, 'preference')
            if not preference:
                session.add(Preference(user_id=user_id, **kwargs))
            else:
                await session.execute(
                    update(Preference)
                    .where(Preference.user_id == user_id)
                    .values(**kwargs)
                )
            await session.commit()
        preference: dict = await get_value(user_id, 'preference')
        for k, v in kwargs.items():
            if v is None: kwargs[k] = ''
            elif isinstance(v, dict): kwargs[k] = json.dumps(v)
        preference.update(kwargs)
        await update_user_cache(user_id, preference=preference)


async def update_user_subscription(user_id, **kwargs) -> Subscription:
    """
    Update user
    :param user_id:
    :param kwargs:
    :return:
    """
    async with lock_update:
        async with get_session() as session:
            __subscription = Subscription(user_id=user_id, **kwargs)
            session.add(__subscription)
            await session.commit()
        subscription: dict = await get_value(user_id, 'subscription')
        subscription['created_at'] = datetime.datetime.now()
        subscription.update(kwargs)
        await update_user_cache(user_id, subscription=subscription, is_premium=True)
    await update_user(user_id, is_premium=True, chat_count=0)
    return __subscription

async def add_user_subscription(user_id, subscription_id: str) -> Subscription:

    if subscription_id == '1':
        price = 100
        _type = "weekly"
        time_delta = datetime.datetime.now() + datetime.timedelta(days=7)

    elif subscription_id == '2':
        price = 250
        _type = "monthly"
        time_delta = datetime.datetime.now() + datetime.timedelta(days=30)

    else:
        price = 1000
        _type = "yearly"
        time_delta = datetime.datetime.now() + datetime.timedelta(days=365)

    subscription = await update_user_subscription(user_id, type=_type, price_in_star=price, end_date=time_delta)

    return subscription



async def delete_user_subscription(user_id):
    """
    Delete user's premium subscription
    :param user_id:
    :return:
    """
    await update_user(user_id, is_premium=False)
    async with lock_update:
        async with get_session() as session:
            result = await session.execute(
                select(Subscription)
                .options(selectinload(Subscription.user))
                .where(Subscription.user_id == user_id)
                .limit(1)
            )
            subs   = result.scalar_one_or_none()
            if subs:
                await session.delete(subs)
                await session.commit()
        await update_user_cache(user_id, subscription={})

async def get_user(user_id: int) -> User | None:
    """
    Get user
    :param user_id:
    :return:
    """
    async with get_session() as session:
        user = await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.preference))
            .limit(1)
        )
        return user.scalar_one_or_none()

async def get_users_id() -> list[int]:
    async with get_session() as session:
        fetched = await session.execute(select(User.id).order_by(User.created_at))
        scalars = fetched.scalars()
        return scalars

async def contains_banned_words(text):
    sp_word = set(text.split())
    banned  = await get_banned_words()
    common  = list(sp_word & set(banned))

    return len(common)!= 0

async def get_user_statistics():
    now = datetime.datetime.now()
    day_ago = now - datetime.timedelta(days=1)
    hour_ago = now - datetime.timedelta(hours=1)
    query = select(
        func.count().label("total_users"),
        func.sum(
            case(
                (User.created_at >= day_ago, 1),
                else_=0
            )
        ).label("users_joined_24h"),
        func.sum(
            case(
                (User.created_at >= hour_ago, 1),
                else_=0
            )
        ).label("users_joined_1h"),
        func.count().filter(User.gender == 'male').label("male_users"),
        func.count().filter(User.gender == 'female').label("female_users"),
        func.count().filter(User.gender.is_(None)).label("other_users")
    )

    async with get_session() as session:
        result = await session.execute(query)
        stats = result.one()

        return {
            "total_users": stats.total_users or 0,
            "users_joined_24h": stats.users_joined_24h or 0,
            "users_joined_1h": stats.users_joined_1h or 0,
            "male_users": stats.male_users or 0,
            "female_users": stats.female_users or 0,
            "other_users": stats.other_users or 0
        }