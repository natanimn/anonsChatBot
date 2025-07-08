import asyncio

user_search_events = {}
lock_search        = asyncio.Lock()
lock_update        = asyncio.Lock()

locks = {}

def get_user_lock(user_id):
    if user_id not in locks:
        locks[user_id] = asyncio.Lock()
    return locks[user_id]

async def create_event(user_id: int) -> asyncio.Event:
    """
    Create and register user event
    :param user_id:
    :return:
    """
    event = asyncio.Event()
    user_search_events[user_id] = event
    return event


async def get_event(user_id: int) -> asyncio.Event | None:
    """
    Get user event
    :param user_id:
    :return:
    """
    if user_id in user_search_events:
        return user_search_events[user_id]
    else:
        return None

async def delete_event(user_id: int):
    """
    Delete an existing user event when it is not needed anymore
    :param user_id:
    :return:
    """
    if user_id in user_search_events:
        del user_search_events[user_id]
