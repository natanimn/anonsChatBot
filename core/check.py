from pyrogram.types import Message, CallbackQuery, PreCheckoutQuery

from .state import State
from keyboards.keyboard import keyboards
from cache.cache import get_value, get_user_cache

async def is_keyboard(_, __, message: Message):
    return message.text in keyboards

async def setting(_, __, callback: CallbackQuery):
    return callback.data.startswith('setting')

async def gender(_, __, callback: CallbackQuery):
    return callback.data.startswith('gender')

async def age(_, __, callback: CallbackQuery):
    return callback.data.startswith('ge')

async def country(_, __, callback: CallbackQuery):
    return callback.data.startswith('country')

async def preference(_, __, callback: CallbackQuery):
    return callback.data.startswith('preference')

async def gender_preference(_, __, callback: CallbackQuery):
    return callback.data.startswith('pr_gender')

async def age_preference(_, __, callback: CallbackQuery):
    return callback.data.startswith('pr_age')

async def country_preference(_, __, callback: CallbackQuery):
    return callback.data.startswith('pr_country')

async def is_chatting(_, __, message: Message):
    user_id = message.from_user.id
    state   = await get_value(user_id, 'current_state')
    return state == State.CHATTING

async def subscribe_premium(_, __, callback: CallbackQuery):
    return callback.data.startswith('subscribe_premium')

async def user_not_exist(_, __, update: CallbackQuery | Message | PreCheckoutQuery):
    user_id = update.from_user.id
    data = await get_user_cache(user_id)
    return not data

async def first(_, __, callback: CallbackQuery):
    return callback.data.startswith('first')

async def no_gender(_, __, callback: CallbackQuery | Message | PreCheckoutQuery):
    user_id = callback.from_user.id
    data = await get_user_cache(user_id)
    return data['gender'] == ''

async def report(_, __, callback: CallbackQuery):
    return callback.data.startswith('report_chat')

async def c_report(_, __, callback: CallbackQuery):
    return callback.data.startswith('c_report')

async def india_region(_, __, callback: CallbackQuery):
    return callback.data.startswith('india_region')

async def india_region_preference(_, __, callback: CallbackQuery):
    return callback.data.startswith('pr_india_region')

# async def gender(_, __, callback: CallbackQuery):
#     return callback.data.startswith('gender')