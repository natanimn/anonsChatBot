import asyncio
from pyrogram import Client, idle
from schedules.schedule import add_unsubscription, add_unrestrict, async_scheduler
from config import Config
from database.model import Base, async_engine
from pyrogram_patch.fsm.storages import MemoryStorage
from pyrogram_patch.patch import patch
from pyrogram.types import BotCommand
import logging
from core.chat import background_match

logging.basicConfig(
    level=logging.ERROR,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("a2zdatingbot.log"),
        logging.StreamHandler()
    ]
)

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
        BotCommand('developer', "Bot developer")
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
        },
        workers=200,
        skip_updates=True
    )

    patch_manager = patch(bot)
    patch_manager.set_storage(MemoryStorage())

    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    await asyncio.gather(
        add_unrestrict(),
        add_unsubscription()
    )

    async with bot:
        async_scheduler.start()
        print("Bot Started...")
        await asyncio.gather(idle(), background_match(bot))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_bot())
