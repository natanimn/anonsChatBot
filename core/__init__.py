import asyncio

from . import check
from . import events
from . import util
from . import var
import logging
from pyrogram.errors import (
    UserIsBlocked,
    FloodWait,
    BadRequest,
    MessageNotModified,
    QueryIdInvalid
)
from pyrogram import Client
logger = logging.getLogger("a2zdatingbot")

def safe(handler):
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


from . import state