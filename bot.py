"""
Telegram бот с интеграцией OpenAI
Поддерживает несколько бесед, анализ изображений и документов
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import router


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция запуска бота"""
    
    # Проверяем токен
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("❌ Укажите BOT_TOKEN в файле config.py!")
        logger.error("   Получите токен у @BotFather в Telegram")
        return
    
    # Создаем экземпляр бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties()
    )
    
    # Создаем диспетчер с хранилищем состояний
    dp = Dispatcher(storage=MemoryStorage())
    
    # Подключаем роутер с обработчиками
    dp.include_router(router)
    
    # Удаляем вебхук и очищаем очередь обновлений
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("🚀 Бот запущен!")
    logger.info("   Нажмите Ctrl+C для остановки")
    
    # Запускаем polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    # Исправление для Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
