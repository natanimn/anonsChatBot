import asyncio
from datetime import date, timedelta
from pyrogram import Client as app, filters
from pyrogram.types import Message
from database.model import get_session, User
from keyboards import keyboard
from core.util import insert_user, search_partner, close_chat, update_user
from core.events import create_event, delete_event, get_event
from core.state import State
from cache.cache import (
    create_user_cache,
    get_user_cache,
    update_user_cache,
    get_value,
    user_exists,
    get_chat_cache,
    create_chat_cache
)
from core import check
from pyrogram.errors.rpc_error import RPCError
from core.var import COUNTRIES
from config import Config

from . import start # Should be imported first


# @app.on_message(filters.create(check.no_gender))
# async def no_gender_update(bot: app, message: Message):
#     user_id = message.from_user.id
#
#     if message.text == '/start':
#         await start.start(bot, message)
#         return
#     gender  = await get_value(user_id, 'gender')
#
#     if not gender:
#         await bot.send_message(user_id,
#             "**🌼 Welcome again\n\n**"
#             "❕ __To continue, you have to select your gender first__",
#             reply_markup=keyboard.first_time_gender()
#         )

from . import chat
from . import exit_chat
from . import delete
from . import premium
from . import rechat
from . import setting
from . import yes_no

@app.on_message(filters.command('help'))
async def help_(_, message: Message):
    await message.reply(
        f"""**🕹 Commands **\n
/start - Start message
/chat - Find a partner
/exit - For stopping the conversation
/premium - Subscribe to premium
/rechat - Connect with previous partner 💎
/delete - Delete sent message to your partner 💎
/setting- Manage profile and preference
/privacy - Privacy Policy
/help - Bot help
/rules - Rules of the chat.\n
**🔒 Security**:
<blockquote>**
- Links Blocked Permanently
- Photos and Stickers will be Allowed After 2 minutes.
- Report System**
</blockquote>
**💡 For regular users, daily chat limit is {Config.DAILY_CHAT_LIMIT}**
""",  reply_markup=keyboard.help_k())


@app.on_message(filters.command('rules'))
async def rules(_, message: Message):
    with open('rules.txt', encoding='utf-8') as file:
        await message.reply(file.read())
        file.close()

@app.on_message(filters.command('privacy'))
async def privacy(_, message: Message):
    with open('privacy.txt', encoding='utf-8') as file:
        await message.reply(file.read())
        file.close()



