from functools import wraps
from pyrogram.errors import (
    FloodWait,
    UserIsBlocked,
    BadRequest,
    QueryIdInvalid,
    MessageNotModified,
    MessageDeleteForbidden
)
import logging
import asyncio
from pyrogram.types import Message, CallbackQuery
from config import Config
logger = logging.getLogger("a2zdatingbot")

ignore_update = False
active_tasks  = list()

def safe(handler):
    @wraps(handler)
    async def wrapper(client, obj, **kwargs):
        global ignore_update, active_tasks
        loop = None
        try:
            loop = asyncio.create_task(handler(client, obj, **kwargs))
            active_tasks.append(loop)
            if not ignore_update:
                await loop
        except FloodWait as e:
            logger.error(f"FloodWait - bot ignored updates fpr {e.value} seconds")
            for tasks in active_tasks:
                tasks.cancel()
            ignore_update = True
            await asyncio.sleep(e.value)
            ignore_update = False
        except asyncio.CancelledError:
            active_tasks.remove(loop)
        except Exception as e:
            if not isinstance(e, (UserIsBlocked, MessageNotModified, QueryIdInvalid, BadRequest, MessageDeleteForbidden)):
                logger.error(e)

    return wrapper


def safe_c(handler):
    @wraps(handler)
    async def wrapper(client, obj, state):
        global ignore_update, active_tasks
        loop = None
        try:
            loop = asyncio.create_task(handler(client, obj, state))
            active_tasks.append(loop)
            if not ignore_update:
                await loop
        except FloodWait as e:
            logger.error(f"FloodWait - bot ignored updates fpr {e.value} seconds")
            for tasks in active_tasks:
                tasks.cancel()
            ignore_update = True
            await asyncio.sleep(e.value)
            ignore_update = False
        except asyncio.CancelledError:
            active_tasks.remove(loop)
        except Exception as e:
            if not isinstance(e, (UserIsBlocked, MessageNotModified, QueryIdInvalid, BadRequest, MessageDeleteForbidden)):
                logger.error(e)
    return wrapper


def admin(handler):
    @wraps(handler)
    async def wrapper(client, obj: Message | CallbackQuery, *args, **kwargs):
        user_id = obj.from_user.id
        if user_id == Config.ADMIN_ID:
            return await handler(client, obj, *args, **kwargs)
        return None

    return wrapper