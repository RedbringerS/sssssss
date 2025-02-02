import asyncio
import logging
import sys
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from vfs_trpl import run_vfs_trpl
from handlers import router, send_info_message_to_subscribers
from vfs_trpl import DB_CONFIG
from config import get_config


def read_config():
    config = get_config()
    return config


async def main():
    config_data = read_config()
    console_level = config_data.get('LOGGING', 'console_level', fallback='INFO')
    logging.getLogger().setLevel(console_level.upper())

    bot = Bot(token=config_data.get('TELEGRAM', 'auth_token'), parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    async with asyncpg.create_pool(**DB_CONFIG) as pool:
        async with pool.acquire():
            asyncio.ensure_future(run_vfs_trpl(send_info_message_to_subscribers, bot))
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), timeout=60)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
