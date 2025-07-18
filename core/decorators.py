from functools import wraps
from pyrogram.errors import (
    FloodWait,
    UserIsBlocked,
    BadRequest,
    QueryIdInvalid,
    MessageNotModified
)
import logging
import asyncio
from pyrogram import Client
from pyrogram.types import Message, CallbackQuery
from config import Config

logger = logging.getLogger("a2zdatingbot")


def safe(handler):
    @wraps(handler)
    async def wrapper(client, obj, **kwargs):
        try:
            await handler(client, obj, **kwargs)
        except FloodWait as e:
            logger.error(f"FloodWait - The bot stopped receiving updates for {e.value} second(s).")
            await client.stop()
            await asyncio.sleep(e.value)
            await client.start()
        except Exception as e:
            if not isinstance(e, (UserIsBlocked, MessageNotModified, QueryIdInvalid, BadRequest)):
                logger.error(e)

    return wrapper


def safe_c(handler):
    @wraps(handler)
    async def wrapper(client: Client, obj, state):
        try:
            await handler(client, obj, state)
        except FloodWait as e:
            logger.error(f"FloodWait - Sleeping for {e.value}. The bot stopped receiving updates")
            await client.stop()
            await asyncio.sleep(e.value)
            await client.start()
        except Exception as e:
            if not isinstance(e, (UserIsBlocked, MessageNotModified, QueryIdInvalid, BadRequest)):
                logger.error(e)

    return wrapper


def admin(handler):
    @wraps(handler)
    async def wrapper(client: Client, obj: Message | CallbackQuery, *args, **kwargs):
        user_id = obj.from_user.id
        if user_id == Config.ADMIN_ID:
            return await handler(client, obj, *args, **kwargs)
        return None

    return wrapper