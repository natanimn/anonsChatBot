import asyncio
from pyrogram import Client
from schedules.schedule import async_scheduler, add_unsubscription, add_unrestrict
from core import linux
from config import Config
from database.model import Base, async_engine
from pyrogram_patch.fsm.storages import MemoryStorage
from pyrogram_patch.patch import patch
from pyrogram.types import BotCommand

async def add_commands(bot: Client):
    await bot.set_bot_commands([
        BotCommand('start', "Start message"),
        BotCommand('rules', "Bot rules"),
        BotCommand('chat', "Find new partner"),
        BotCommand('exit', "Stop conversation"),
        BotCommand('premium', "Subscribe to premium"),
        BotCommand('rechat', "Re-chat with previous user"),
        BotCommand('delete', "Delete sent message from partner"),
        BotCommand('setting', "Manage setting"),
        BotCommand('privacy', "Privacy and Policy"),
        BotCommand('help', "Get help")
    ])

async def run_bot():
    """
    Main function to run the bot
    :return:
    """

    bot = Client(
        'anon_chat',
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.TOKEN,
        plugins={
            'root': 'plugins'
        }
    )

    patch_manager = patch(bot)
    patch_manager.set_storage(MemoryStorage())

    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    await asyncio.gather(
        add_unrestrict(),
        add_unsubscription()
    )
    await bot.start()
    await add_commands(bot)
    try:
        print("BOT STARTED")
        await asyncio.Event().wait()
    finally:
        await bot.stop()
        async_scheduler.shutdown()

if __name__ == '__main__':
    asyncio.run(run_bot())
