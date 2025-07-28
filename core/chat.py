import asyncio

from pyrogram import Client
from pyrogram.errors import UserIsBlocked
from cache.cache import get_value, get_user_cache, update_user_cache, create_chat_cache
from .state import State
from database.model import get_session, User, Preference, Subscription
from sqlalchemy import or_, and_, func, select, update
from core.var import COUNTRIES

online_users_queue = asyncio.PriorityQueue()
online_users_list  = list()

async def add_user_to_queue(user_id: int):
    if not user_id in online_users_list:
        online_users_list.append(user_id)

async def remove_user_from_queue(user_id: int):
    if user_id in online_users_list:
        online_users_list.pop(user_id)

async def prepare_filter(user_id, user, preference):
    filters = [
        User.id != user_id,
        User.id.in_(online_users_list),
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
    return filters


async def background_match(app: Client):
    print("Background match started")

    while True:
        if online_users_list:
            user_id: int = online_users_list.pop(0)
        else:
            await asyncio.sleep(0.5)
            continue

        user       = await get_user_cache(user_id)
        preference = user['preference']
        query      = await prepare_filter(user_id, user, preference)

        if user['current_state'] != State.SEARCHING:
            continue

        async with get_session() as session:
            matched = await session.execute(
                select(User.id)
                .where(and_(*query))
                .order_by(func.random())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            matched_scalar_id = matched.scalar_one_or_none()
            matched_scalar = await get_user_cache(matched_scalar_id)
            if (
                    matched_scalar and
                    matched_scalar['current_state'] == State.SEARCHING and
                    user['current_state'] == State.SEARCHING
            ):
                    partner_id = matched_scalar_id
                    partner_state = await get_value(partner_id, "current_state")
                    if partner_state != State.SEARCHING:
                        await add_user_to_queue(user_id)
                        continue

                    user_state = await get_value(user_id, "current_state")

                    if user_state != State.SEARCHING:
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

                    user_notified, partner_notified = await notify(app, user, matched_scalar)

                    if not user_notified or not partner_notified:
                        await session.rollback()
                    else:
                        await create_chat_cache(user_id, partner_id)
                        user_kwargs['match_request_from'] = 0
                        partner_kwargs['match_request_from'] = 0

                        await asyncio.gather(
                            update_user_cache(user_id, **user_kwargs),
                            update_user_cache(partner_id, **partner_kwargs)
                        )
                        await session.commit()

            else:
                await add_user_to_queue(user_id)
            await asyncio.sleep(0)

async def notify(app: Client, user, matched_user) -> tuple[bool, bool]:
    new_state = user['current_state']
    partner_state = matched_user['current_state']
    if new_state == partner_state == State.SEARCHING:
        partner_country = ''
        partner_region = ''
        user_country = ''
        user_region = ''

        if matched_user['country'] or user['country']:
            for k, v in COUNTRIES.items():
                if matched_user['country'] == v:
                    partner_country = k
                if user['country'] == v:
                    user_country = k

        if matched_user['india_region']:
            partner_region = matched_user['india_region']

        if user['india_region']:
            user_region = user['india_region']

        partner_full_country = partner_country + ('/' + partner_region if partner_region else '')
        user_full_country = user_country + ('/' + user_region if user_region else '')
        partner_id = matched_user['id']

        try:
            age = 'Unknown' if int(matched_user['age']) == 0 else matched_user['age']
            gender = matched_user['gender'] if user['is_premium'] else '||For Premium||'
            await app.send_message(user['id'],
                "**✅ Partner found**\n\n"
                f"**🔢 __Age: {age}\n__**"
                f"**👥 __Gender: {gender}__**\n"
                f"**🌍 __Country: {partner_full_country}__**\n\n"
                f"🚫 **Links are blocked**.\n"
                f"__✔️ You can send media after 2 minutes__\n\n"
                f"**/exit - Leave Partner**",
            )
        except UserIsBlocked:
            try:
                await app.send_message(
                    partner_id,
                    "**Error**\n\n"
                    "__The partner we have found you just blocked the bot.\n\n"
                    "Searching for partner again",
                )
            except UserIsBlocked:
                return False, False
            else:
                return False, True
        else:
            try:
                age = 'Unknown' if int(user['age']) == 0 else user['age']
                gender = user['gender'] if matched_user['is_premium'] else '||For Premium||'
                await app.send_message(
                    partner_id,
                    "**✅ Partner found**\n\n"
                    f"**🔢 __Age: {age}\n__**"
                    f"**👥 __Gender: {gender}__**\n"
                    f"**🌍 __Country: {user_full_country}__**\n\n"
                    f"🚫 **Links are blocked**.\n"
                    f"__✔️ You can send media after 2 minutes__\n\n"
                    f"**/exit - Leave Partner**",
                )
            except UserIsBlocked:
                try:
                    await app.send_message(user['id'],
                        "**Error**\n\n"
                        "__The partner we have found you just blocked the bot.\n\n"
                        "Searching for partner again__",
                    )
                except UserIsBlocked:
                    return False, False
                else:
                    return True, False
            else:
                return True, True
    return False, False
