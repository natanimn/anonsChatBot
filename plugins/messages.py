import asyncio
import datetime
from datetime import timedelta
from pyrogram import Client as app, filters
from core import check
from pyrogram.types import Message
from pyrogram.enums import MessageEntityType
from .commands import (
    setting,
    chat,
    help_,
    premium,
    re_chat,
)
from cache.cache import (
    get_value,
    update_chat_cache,
    update_user_cache,
    get_chat_cache
)
from pyrogram.errors import BadRequest, UserIsBlocked, FloodWait
from core.util import close_chat, update_user
from keyboards import keyboard
from core.state import State
from core.util import contains_banned_words


@app.on_message(filters.private & filters.text & filters.create(check.is_keyboard))
async def message_keyboad(_, message: Message):

    if message.text == "💫 Premium":
        await premium(_, message)

    elif message.text == "⚙️ Setting":
        await setting(_, message)

    elif message.text == "👥 Chat":
        await chat(_, message)

    elif message.text == "🔄 Re Chat":
        await re_chat(_, message)

    elif message.text == "❓Help":
        await help_(_, message)

    else:
        await message.reply(
            "**ℹ️ About**\n\n"
            "__This bot helps to meet other people over the world. It will help to connect "
            "with other people with common interest. We dont collect any of your chats; Everything is anonymous.__\n\n"
            "**Thanks for your support.**",
            reply_markup=keyboard.support()
        )


@app.on_message(filters.private & filters.create(check.is_chatting) & (filters.text | filters.media))
async def get_chat_message(bot: app, message: Message):
    user_id = message.from_user.id
    message_id = message.id
    partner_id = await get_value(user_id, 'chatting_with')
    user_status = await get_value(user_id, 'current_state')
    partner_status = await get_value(partner_id, 'current_state')

    if user_status == State.RESTRICTED or partner_status == State.RESTRICTED:
        await close_chat(user_id, partner_id)
        try:
            await bot.send_message(partner_id, "**Chat closed**", reply_markup=keyboard.main())
        finally:
            await message.reply("**Chat closed**", reply_markup=keyboard.main())
            return None

    if message.entities or message.caption_entities:
        for entity in message.entities or message.caption_entities:
            if entity.type in [
                MessageEntityType.TEXT_LINK,
                MessageEntityType.MENTION,
                MessageEntityType.URL,
                MessageEntityType.TEXT_MENTION,
                MessageEntityType.EMAIL
            ]:

                return await message.reply("📵 **Sending any link is not allowed**")

    text = message.text or message.caption or ''

    if await contains_banned_words(text):
        return None

    try:
        history = await get_chat_cache(user_id, partner_id)
        if message.media:
            now = datetime.datetime.now()
            created_at = history['created_at']
            total = created_at + timedelta(minutes=2)
            if now < total:
                return await message.reply("**☝️ You can't any send media now**")
            else:
                await asyncio.sleep(0.5)
                if message.photo:
                    try:
                        sent_message = await bot.send_photo(
                            partner_id,
                            message.photo.file_id,
                            caption=message.caption,
                            has_spoiler=True,
                        )
                    except FloodWait as fw:
                        await asyncio.sleep(fw.value)
                        sent_message = await bot.send_photo(
                            partner_id,
                            message.photo.file_id,
                            caption=message.caption,
                            has_spoiler=True,
                        )
                else:
                    try:
                        sent_message = await bot.copy_message(partner_id, user_id, message_id)
                    except FloodWait as fw:
                        await asyncio.sleep(fw.value)
                        sent_message = await bot.copy_message(partner_id, user_id, message_id)
        else:
            await asyncio.sleep(0.5)
            try:
                sent_message = await bot.copy_message(partner_id, user_id, message_id)
            except FloodWait as fw:
                await asyncio.sleep(fw.value)
                sent_message = await bot.copy_message(partner_id, user_id, message_id)

    except (BadRequest, UserIsBlocked):
        await message.reply(
            "**⚠ Error**\n\n"
            "__Sorry, your partner blocked the bot, and chat is closed__",
            reply_markup=keyboard.main()
        )
        return await close_chat(user_id, partner_id)
    else:
        if sent_message:
            return await update_chat_cache(user_id, partner_id, message_id, sent_message.id)
        return None

