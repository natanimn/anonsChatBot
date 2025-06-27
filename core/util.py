import asyncio
import datetime
import json
import os

import time
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy import and_, or_, not_
from sqlalchemy.orm import selectinload
from .events import get_event, lock_search, lock_update, get_user_lock
from .state import State
from cache.cache import (
    update_user_cache,
    get_user_cache,
    get_value,
    delete_chat_history,
    create_chat_cache
)
from database.model import (
    User,
    get_session,
    Preference,
    Subscription,
    async_session
)


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

async def search_partner(user_id: int) -> User | None:
    """
    Search a partner for user on a given event ooop
    :param user_id:
    :param event:
    :return:
    """
    event: asyncio.Event = await get_event(user_id)
    async with (get_session() as session):
        timeout = int(os.getenv('TIMEOUT', 120))
        matched_scalar = None
        start = time.time()
        user  = await get_user_cache(user_id)
        attempts = 0

        while not event.is_set() and time.time() < start + timeout and user['current_state'] == State.SEARCHING:
            user = await get_user_cache(user_id)
            if user['current_state'] != State.SEARCHING:
                break

            filters = [
                User.id != user_id,
                User.current_state == State.SEARCHING,
                User.last_partner_id != user_id,
                User.id != user['last_partner_id']
            ]
            if user['is_premium']:
                if preference:=user['preference']:
                    if countries:=preference.get('country', []): # country based filtering
                        filters.append(or_(
                            and_(
                                User.country.in_(countries),
                                User.is_premium == False
                            ),
                            and_(
                                User.is_premium == True,
                                User.preference.has(Preference.country.any(user['country'])),
                                User.country.in_(countries),
                            )
                        ))

                    if min_age:=preference.get('min_age'):# and preference.max_age:
                        filters.append(or_(
                            and_(
                                User.age >= min_age,
                                User.is_premium == False
                            ),
                            and_(
                                User.is_premium == True,
                                User.preference.has(Preference.min_age <= int(user['age']))),
                                User.age >= int(min_age),
                        ))

                    if max_age:=preference.get('max_age'):
                        filters.append(or_(
                            and_(
                                User.age <= max_age,
                                User.is_premium == False
                            ),
                            and_(
                                User.is_premium == True,
                                User.preference.has(Preference.max_age >= int(user['age']))),
                                User.age <= int(max_age),

                        ))

                    if gender:=preference.get('gender'):
                        filters.append(or_(
                            and_(
                                User.gender == gender,
                                User.is_premium == False
                            ),
                            and_(
                                User.is_premium == True,
                                User.preference.has(Preference.gender == user['gender']),
                                User.gender == gender
                            )
                        ))

                    if user['country'] == 'india' and preference.get('india_region'):
                        regions = preference.get('india_region')
                        filters.append(or_(
                            and_(
                                User.india_region.in_(regions),
                                User.is_premium == False
                            ),
                            and_(
                                User.is_premium == True,
                                User.preference.has(Preference.india_region.any(user['indian_region'])),
                                User.india_region.in_(regions)
                            )
                        ))
            else:
                filters.append(User.is_premium == False)

            async with lock_search:
                matched = await session.execute(
                    select(User)
                    .where(and_(*filters)).limit(1)
                    .options(selectinload(User.preference), selectinload(User.subscription))
                    .with_for_update(skip_locked=True)
                )
                matched_scalar = matched.scalar_one_or_none()

                if matched_scalar and \
                matched_scalar.current_state == State.SEARCHING and \
                user['current_state'] == State.SEARCHING:
                    try:
                        partner_id = matched_scalar.id
                        m_event = await get_event(partner_id)
                        if not m_event:
                            continue

                        if not user['is_premium']:
                            count = user['chat_count'] + 1
                        else:
                            count = 0

                        if not matched_scalar.is_premium:
                            p_count = matched_scalar.chat_count + 1
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

                        await update_user_cache(user_id, **user_kwargs)
                        await update_user_cache(partner_id, **partner_kwargs)
                        await update_user_cache(user_id, match_request_from=0)
                        await update_user_cache(partner_id, match_request_from=0)
                        await create_chat_cache(user_id, partner_id)
                        m_event.set()
                    except Exception as e:
                        print(e)
                    event.set()
                    break
                wait = min(0.1 + attempts*0.1 , 5)
                await asyncio.sleep(wait)
                attempts += 1

        if not event.is_set():
            event.set()

        return user, matched_scalar


async def close_chat(user_id, partner_id):
    """
    Close the current chat
    :param user_id:
    :param partner_id:
    :return:
    """
    await update_user(int(partner_id), chatting_with=0, current_state=State.NONE, last_partner_id=user_id)
    await update_user(user_id, chatting_with=0, current_state=State.NONE, last_partner_id=int(partner_id))
    await delete_chat_history(user_id, partner_id)

async def update_user(user_id, **kwargs):
    """
    Update user
    :param user_id:
    :param kwargs:
    :return:
    """
    user_id = int(user_id)  # ensure correct type

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
                await update_user_cache(user_id, **kwargs)
            except Exception as e:
                print(f"Error updating user {user_id}: {e}")


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


async def update_user_subscription(user_id, **kwargs):
    """
    Update user
    :param user_id:
    :param kwargs:
    :return:
    """
    async with lock_update:
        async with get_session() as session:
            session.add(Subscription(user_id=user_id, **kwargs))
            await session.commit()
        subscription: dict = await get_value(user_id, 'subscription')
        subscription['created_at'] = datetime.datetime.now()
        subscription.update(kwargs)
        await update_user_cache(user_id, subscription=subscription, is_premium=True)
    await update_user(user_id, is_premium=True, chat_count=0)

async def delete_user_subscription(user_id):
    """
    Delete user's premium subscription
    :param user_id:
    :return:
    """
    async with lock_update:
        async with get_session() as session:
            subs = await session.execute(select(Subscription).options(selectinload(Subscription.user))
                                  .where(Subscription.user_id == user_id)
                                  .limit(1))
            await session.delete(subs)
        await update_user_cache(user_id, subscription={})

    await update_user(user_id, is_premium=False)
    

async def update_users_state():
    """
    Update all users states to State.NONE
    :return:
    """
    CHUNK_SIZE = 100_000

    async with get_session() as session:
        # for offset in range(0, len(all_users), CHUNK_SIZE):
        await session.execute(
            update(User)
            .values(current_state=State.NONE)
        )
        await session.commit()


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
