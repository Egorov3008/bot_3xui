from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncpg

from bot import bot
from config import ADMIN_ID, DATABASE_URL
from handlers.pay import ReplenishBalanceState, process_custom_amount_input
from handlers.profile import process_callback_view_profile
from handlers.start import start_command
from handlers.texts import TRIAL
from handlers.admin.admin import cmd_add_balance
from handlers.keys.key_management import handle_key_name_input
from aiogram.types import Message

router = Router()

class Form(StatesGroup):
    """Класс состояний для управления состояниями FSM (Finite State Machine)."""
    waiting_for_server_selection = State()
    waiting_for_key_name = State()
    viewing_profile = State()
    waiting_for_message = State()

@router.message(Command('backup'))
async def backup_command(message: Message):
    """Обрабатывает команду /backup, выполняя резервное копирование базы данных.

    Проверяет, является ли пользователь администратором. Если нет,
    отправляет сообщение об отсутствии прав. В противном случае
    запускает процесс резервного копирования базы данных и уведомляет
    пользователя о завершении.

    Args:
        message (Message): Сообщение, полученное от пользователя.
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    from backup import backup_database
    await message.answer("Запускаю бэкап базы данных...")
    await backup_database()
    await message.answer("Бэкап завершен и отправлен админу.")

@router.message(Command('start'))
async def handle_start(message: types.Message, state: FSMContext):
    """Обрабатывает команду /start, инициируя процесс приветствия.

    Вызывает функцию start_command для отправки приветственного сообщения
    пользователю.

    Args:
        message (types.Message): Сообщение, полученное от пользователя.
        state (FSMContext): Контекст состояния для управления состояниями.
    """
    await start_command(message)

@router.message(Command('add_balance'))
async def handle_add_balance(message: types.Message, state: FSMContext):
    """Обрабатывает команду /add_balance, инициируя процесс добавления баланса.

    Вызывает функцию cmd_add_balance для управления добавлением баланса
    пользователю.

    Args:
        message (types.Message): Сообщение, полученное от пользователя.
        state (FSMContext): Контекст состояния для управления состояниями.
    """
    await cmd_add_balance(message)

@router.message(Command('menu'))
async def handle_menu(message: types.Message, state: FSMContext):
    """Обрабатывает команду /menu, отправляя главное меню пользователю.

    Вызывает функцию start_command для отображения главного меню.

    Args:
        message (types.Message): Сообщение, полученное от пользователя.
        state (FSMContext): Контекст состояния для управления состояниями.
    """
    await start_command(message)

@router.message(Command('send_trial'))
async def handle_send_trial_command(message: types.Message, state: FSMContext):
    """Обрабатывает команду /send_trial, отправляя сообщения о пробном периоде
    пользователям.

    Проверяет, является ли пользователь администратором. Если нет,
    отправляет сообщение об отсутствии доступа. Если да, то извлекает
    пользователей с неиспользованными пробными ключами из базы данных и
    отправляет им сообщения. Обрабатывает возможные ошибки при отправке сообщений.

    Args:
        message (types.Message): Сообщение, полученное от пользователя.
        state (FSMContext): Контекст состояния для управления состояниями.
    """
    # Проверка на администратора
    if message.from_user.id != ADMIN_ID:
        await message.reply("У вас нет доступа к этой команде.")
        return

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            records = await conn.fetch('''
                SELECT tg_id FROM connections WHERE trial = 0
            ''')

            if records:
                for record in records:
                    tg_id = record['tg_id']
                    trial_message = TRIAL
                    try:
                        await bot.send_message(chat_id=tg_id, text=trial_message)
                    except Exception as e:
                        if "Forbidden: bot was blocked by the user" in str(e):
                            print(f"Бот заблокирован пользователем с tg_id: {tg_id}")
                        else:
                            print(f"Ошибка при отправке сообщения пользователю {tg_id}: {e}")

                await message.answer("Сообщения о пробном периоде отправлены всем пользователям с не использованным ключом.")
            else:
                await message.answer("Нет пользователей с не использованными пробными ключами.")

        finally:
            await conn.close()

    except Exception as e:
        await message.answer(f"Ошибка при отправке сообщений: {e}")


@router.message(Command('send_to_all'))
async def send_message_to_all_clients(message: types.Message, state: FSMContext):
    """
    Обрабатывает команду отправки сообщения всем клиентам.

    Проверяет, является ли пользователь администратором.
    Если пользователь не является администратором, отправляет сообщение об отсутствии прав.
    В противном случае запрашивает текст сообщения и переходит в состояние ожидания ввода сообщения.

    Args:
        message (types.Message): Сообщение, полученное от пользователя.
        state (FSMContext): Контекст состояния для управления состояниями.
    """
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return

    await message.answer("Введите текст сообщения, который вы хотите отправить всем клиентам:")
    await state.set_state(Form.waiting_for_message)

@router.message(Form.waiting_for_message)
async def process_message_to_all(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод текстового сообщения для отправки всем клиентам.

    Получает текст сообщения и пытается соединиться с базой данных для извлечения всех идентификаторов
    телеграм-пользователей. Затем отправляет сообщение каждому пользователю.
    В случае возникновения ошибок при отправке сообщения или подключении к базе данных,
    выводит соответствующее сообщение и завершает состояние.

    Args:
        message (types.Message): Сообщение, полученное от пользователя.
        state (FSMContext): Контекст состояния для управления состояниями.
    """
    text_message = message.text

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        tg_ids = await conn.fetch('SELECT tg_id FROM connections')

        for record in tg_ids:
            tg_id = record['tg_id']
            try:
                await bot.send_message(chat_id=tg_id, text=text_message)
            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {tg_id}: {e}. Пропускаем этого пользователя.")

        await message.answer("Сообщение было отправлено всем клиентам.")
    except Exception as e:
        print(f"Ошибка при подключении к базе данных: {e}")
        await message.answer("Произошла ошибка при отправке сообщения.")
    finally:
        await conn.close()

    await state.clear()

@router.message()
async def handle_text(message: types.Message, state: FSMContext):
    """
    Обрабатывает текстовые сообщения от пользователей.

    В зависимости от текста сообщения выполняет соответствующие действия:
    отправляет команду отправки сообщения всем клиентам, обрабатывает запросы на просмотр профиля,
    управление балансом и резервное копирование.
    Если состояние не задано, обрабатывает команду старта.

    Args:
        message (types.Message): Сообщение, полученное от пользователя.
        state (FSMContext): Контекст состояния для управления состояниями.
    """
    current_state = await state.get_state()

    if message.text in ["/send_to_all"]:
        await send_message_to_all_clients(message, state)
        return

    if message.text == "Мой профиль":
        callback_query = types.CallbackQuery(
            id="1",
            from_user=message.from_user,
            chat_instance='',
            data='view_profile',
            message=message
        )
        await process_callback_view_profile(callback_query, state)
        return

    if current_state == ReplenishBalanceState.entering_custom_amount.state:
        await process_custom_amount_input(message, state)
        return

    if current_state == Form.waiting_for_key_name.state:
        await handle_key_name_input(message, state)
        return

    if message.text == "/backup":
        await backup_command(message)
        return

    elif current_state is None:
        await start_command(message)