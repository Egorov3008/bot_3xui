import asyncio
import logging
import signal

from aiogram.webhook.aiohttp_server import (SimpleRequestHandler,
                                            setup_application)
from aiohttp import web

from backup import backup_database
from bot import bot, dp, router
from config import WEBAPP_HOST, WEBAPP_PORT, WEBHOOK_PATH, WEBHOOK_URL
from database import init_db
from handlers.notifications import notify_expiring_keys
from handlers.pay import payment_webhook

logging.basicConfig(level=logging.DEBUG)


async def periodic_notifications():
    """
    Функция для периодической отправки уведомлений о сроке действия ключей.

    Эта функция выполняет бесконечный цикл, в котором каждые 3600 секунд
    (1 час) вызывается функция `notify_expiring_keys`. Используется для
    мониторинга и уведомления о ключах, срок действия которых скоро истечет.
    """
    while True:
        await notify_expiring_keys(bot)
        await asyncio.sleep(3600)


async def periodic_database_backup():
    """
    Функция для периодического резервного копирования базы данных.

    Эта функция выполняет бесконечный цикл, в котором каждые 21600 секунд
    (6 часов) вызывается функция `backup_database`. Используется для
    регулярного создания резервных копий базы данных.
    """
    while True:
        await backup_database()
        await asyncio.sleep(21600)


async def on_startup(app):
    """
    Обработчик события старта приложения.

    Эта функция вызывается при старте приложения. Она устанавливает вебхук
    для бота, инициализирует базу данных и запускает задачи для
    периодических уведомлений и резервного копирования базы данных.

    :param app: Экземпляр приложения aiohttp.
    """
    await bot.set_webhook(WEBHOOK_URL)
    await init_db()
    asyncio.create_task(periodic_notifications())
    asyncio.create_task(periodic_database_backup())


async def on_shutdown(app):
    """
    Обработчик события завершения работы приложения.

    Эта функция вызывается при завершении работы приложения. Она удаляет
    вебхук бота и отменяет все активные задачи.

    :param app: Экземпляр приложения aiohttp.
    """
    await bot.delete_webhook()
    for task in asyncio.all_tasks():
        task.cancel()
    try:
        await asyncio.gather(*asyncio.all_tasks(), return_exceptions=True)
    except Exception as e:
        logging.error(f"Error during shutdown: {e}")

async def shutdown_site(site):
    """
    Завершает работу веб-сайта.

    Эта функция останавливает указанный сайт и выводит
    информацию о процессе остановки.

    :param site: Экземпляр веб-сайта aiohttp.
    """
    logging.info("Остановка сайта...")
    await site.stop()
    logging.info("Сервер остановлен.")

async def main():
    """
    Основная функция для запуска веб-приложения.

    Эта функция инициализирует приложение aiohttp, настраивает маршруты,
    запускает сервер и обрабатывает сигналы завершения работы.
    """
    dp.include_router(router)

    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    app.router.add_post('/yookassa/webhook', payment_webhook)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=WEBAPP_HOST, port=WEBAPP_PORT)
    await site.start()

    print(f"Webhook URL: {WEBHOOK_URL}")

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_site(site)))

    try:
        await asyncio.Event().wait()
    finally:
        pending = asyncio.all_tasks()
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {e}")