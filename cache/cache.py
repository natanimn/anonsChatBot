from datetime import datetime, timedelta, date
import json

from redis.asyncio import Redis
# from core.util import get_user
from database.model import User, get_session, async_session
from sqlalchemy import select
from sqlalchemy.orm import selectinload

cache_client = Redis(decode_responses=True)

async def create_user_cache(user_id: int):
    """
    Create a single user cache
    :param user_id:
    :return:
    """
    async with get_session() as session:
        scalar = await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.preference),
                selectinload(User.subscription)
            )
            .limit(1)
        )
        user = scalar.scalar_one_or_none()
        if user is None:
            return

        data = {
            'id': user.id,
            'age': user.age or 0,
            'gender': user.gender or '',
            'is_premium': int(user.is_premium),
            'country': user.country or '',
            'india_region': user.india_region or '',
            'preference': json.dumps({
                'max_age': user.preference.max_age,
                'min_age': user.preference.min_age,
                'gender': user.preference.gender,
                'country': user.preference.country,
                'india_region': user.preference.india_region
            }) if user.preference else '{}',
            'subscription': json.dumps({
                'start_date': user.subscription.created_at.isoformat(),
                'end_date':   user.subscription.end_date,
                'type':       user.subscription.type
            }, default=str) if user.is_premium else '{}',
            'current_state': user.current_state,
            'chatting_with': user.chatting_with or 0,
            'last_partner_id': user.last_partner_id,
            'chat_count': user.chat_count,
            'chat_closed_date': (user.chat_closed_date or date.today() - timedelta(days=1)).isoformat(),
            'report_count': user.report_count,
            'release_date': str(user.release_date or '')
        }
        await cache_client.hset(f"user-{user.id}-cache", mapping=data)

async def user_exists(user_id: int):
    data = await get_user_cache(user_id)
    return data

async def get_user_cache(user_id: int):
    """
    Get user's cache sored in a memory
    :param user_id:
    :return:
    """
    cached_user = await cache_client.hgetall(f'user-{user_id}-cache')

    if not cached_user:
        await create_user_cache(user_id)
        cached_user = await cache_client.hgetall(f'user-{user_id}-cache')
        if not cached_user:
            return None

    user_data = {
        'id': int(cached_user['id']),
        'age': cached_user['age'],
        'is_premium': bool(int(cached_user['is_premium'])),
        'gender': cached_user['gender'],
        'country': cached_user['country'],
        'preference': json.loads(cached_user['preference']),
        'subscription': json.loads(cached_user['subscription']),
        'current_state': int(cached_user['current_state']),
        'premium': json.loads(cached_user.get('premium', '{}')),
        'chatting_with': int(cached_user['chatting_with']),
        'last_partner_id': int(cached_user['last_partner_id']),
        'match_request_from': int(cached_user.get('match_request_from', 0)),
        'india_region': cached_user['india_region'],
        'chat_count': int(cached_user['chat_count']),
        'chat_closed_date': date.fromisoformat(cached_user['chat_closed_date']),
        'report_count': int(cached_user['report_count']),
        'release_date': cached_user['release_date']
    }
    return user_data


async def update_user_cache(user_id: int, **kwargs):
    """
    Update user's cache
    :param user_id:
    :return:
    """

    cache = await get_user_cache(user_id)
    cache.update(kwargs)

    for k, v in cache.items():
        if isinstance(v, bool): cache[k] = int(v)
        elif isinstance(v, dict): cache[k] = json.dumps(v, default=str)
        elif v is None: cache[k] = ''
        elif isinstance(v, date) or isinstance(v, datetime): cache[k] = v.isoformat()

    await cache_client.hset(f'user-{user_id}-cache', mapping=cache)

async def get_value(user_id: int, key: str):
    """
    Get specific value
    :param user_id:
    :param key:
    :return:
    """
    result = await get_user_cache(user_id)
    if result is None:
        return None
    return result[key]

async def create_chat_cache(user_id, partner_id):
    """
    Create chat cache for the first time
    :return:
    """
    filename = await get_chat_cache_file(user_id, partner_id)
    if filename:
        await cache_client.delete(filename)
    await cache_client.hset(f'{user_id}-chat-{partner_id}', mapping={
        user_id: '{}',
        partner_id: '{}',
        'created_at': datetime.now().isoformat()
    })

def parse_chat(chat: dict) -> dict:
    for k, v in chat.items():
        if k.isdigit():
            chat[int(k)] = json.loads(v)
            del chat[k]
        else:
            chat[k] = datetime.fromisoformat(v)
            break
    return chat

async def get_chat_cache(user_id, partner_id) -> dict | None:
    """
    Get cache history
    :param user_id:
    :param partner_id:
    :return:
    """
    if chat := await cache_client.hgetall(f'{user_id}-chat-{partner_id}'):
        return parse_chat(chat)
    elif chat := await cache_client.hgetall(f'{partner_id}-chat-{user_id}'):
        return parse_chat(chat)
    else: return None

async def get_chat_cache_file(user_id, partner_id) -> str | None:
    if await cache_client.hgetall(f'{user_id}-chat-{partner_id}'):
        return f'{user_id}-chat-{partner_id}'
    elif await cache_client.hgetall(f'{partner_id}-chat-{user_id}'):
        return f'{partner_id}-chat-{user_id}'
    else:
        return None

async def update_chat_cache(user_id, partner_id, user_message_id, partner_message_id):
    """
    Update users' cache chat history
    :param user_id:
    :param partner_id:
    :param user_message_id:
    :param partner_message_id:
    :return:
    """
    chat_history = await get_chat_cache(user_id, partner_id)

    if chat_history:
        user_dict = chat_history.get(user_id, {})
        user_dict[user_message_id] = partner_message_id
        chat_history[user_id] = user_dict
        filename = await get_chat_cache_file(user_id, partner_id)
        chat_history[user_id] = json.dumps(chat_history[user_id])
        chat_history[partner_id] = json.dumps(chat_history.get(partner_id, {}))
        chat_history['created_at'] = chat_history['created_at'].isoformat()
        await cache_client.hset(filename, mapping=chat_history)

async def delete_chat_history(user_id, partner_id):
    """
    Delete chat history
    :param user_id:
    :param partner_id:
    :return:
    """
    filename = await get_chat_cache_file(user_id, partner_id)
    if filename:
        await cache_client.delete(filename)

async def reset_users_cache():
    size = 50_000
    batch = []
    async for key in cache_client.scan_iter(match="user-*"):
        batch.append(key)
        if len(batch) >= size:
            await cache_client.unlink(*batch)
            batch = []
    if batch:
        await cache_client.unlink(*batch)

async def add_banned_word(word: str | list[str]):
    data = await get_banned_words()
    if isinstance(word, list):
        data.extend(word)
    else:
        data.append(word)
    await cache_client.set('banned-words', json.dumps(data))

async def get_banned_words():
    cache = await cache_client.get('banned-words')
    if not cache:
        data = []
    else:
        data = json.loads(cache)
    return data