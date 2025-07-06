import asyncio
from pyrogram import Client
from schedules.schedule import async_scheduler, add_unsubscription, add_unrestrict
from config import Config
from database.model import Base, async_engine
from pyrogram_patch.fsm.storages import MemoryStorage
from pyrogram_patch.patch import patch
from pyrogram.types import BotCommand
from cache.cache import reset_users_cache

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
        BotCommand('help', "Get help"),
        BotCommand('paysupport', "Payment support"),

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
        add_unsubscription(),
        reset_users_cache()
    )
    async_scheduler.start()
    await bot.start()

    print(bot.me.full_name)
    await add_commands(bot)
    try:
        print("BOT STARTED")
        await asyncio.Event().wait()
    finally:
        async_scheduler.shutdown()
        await bot.stop()

if __name__ == '__main__':
    asyncio.run(run_bot())
