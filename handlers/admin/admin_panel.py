from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from config import ADMIN_ID, DATABASE_URL
import asyncpg
from datetime import datetime
from bot import bot

router = Router()

class UserEditorState(StatesGroup):
    """
    Класс состояний для редактора пользователей.

    Используется для управления состояниями диалога с пользователем в процессе редактирования данных пользователя.
    """
    waiting_for_tg_id = State()  # Состояние ожидания Telegram ID
    displaying_user_info = State()  # Состояние отображения информации о пользователе

@router.message(Command('admin'))
async def handle_admin_command(message: types.Message):
    """
    Обрабатывает команду /admin для отображения панели администратора.

    Проверяет, является ли пользователь администратором. Если да, то отправляет сообщение с
    кнопками для доступа к статистике пользователей и редактору пользователей.

    Параметры:
    - message (types.Message): Объект сообщения, содержащий команду /admin.

    Ответы:
    - Отправляет сообщение с кнопками, если пользователь администратор.
    - Отправляет сообщение о запрете доступа, если пользователь не администратор.
    """
    if message.from_user.id != ADMIN_ID:
        await message.reply("У вас нет доступа к этой команде.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статистика пользователей", callback_data="user_stats")],
        [InlineKeyboardButton(text="Редактор пользователей", callback_data="user_editor")]
    ])
    await message.reply("Панель администратора", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "user_stats")
async def user_stats_menu(callback_query: CallbackQuery):
    """
    Обрабатывает запрос на отображение статистики пользователей.

    Подключается к базе данных, извлекает статистику пользователей, ключей и рефералов,
    а затем отправляет ее в ответ на запрос.

    Параметры:
    - callback_query (CallbackQuery): Объект обратного вызова, содержащий информацию о запросе.

    Ответы:
    - Отправляет сообщение с общей статистикой пользователей.
    """
    conn =await asyncpg.connect(DATABASE_URL)
    try:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM connections")
        total_keys = await conn.fetchval("SELECT COUNT(*) FROM keys")
        total_referrals = await conn.fetchval("SELECT COUNT(*) FROM referrals")

        active_keys = await conn.fetchval("SELECT COUNT(*) FROM keys WHERE expiry_time > $1", int(datetime.utcnow().timestamp() * 1000))
        expired_keys = total_keys - active_keys

        stats_message = (
            f"🔹 <b>Общая статистика пользователей:</b>\n"
            f"• Всего пользователей: <b>{total_users}</b>\n"
            f"• Всего ключей: <b>{total_keys}</b>\n"
            f"• Всего рефералов: <b>{total_referrals}</b>\n"
            f"• Активные ключи: <b>{active_keys}</b>\n"
            f"• Истекшие ключи: <b>{expired_keys}</b>"
        )

        back_button = InlineKeyboardButton(text="Назад", callback_data="back_to_admin_menu")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [back_button]
        ])

        await callback_query.message.edit_text(stats_message, reply_markup=keyboard, parse_mode="HTML")
    finally:
        await conn.close()

    await callback_query.answer()

@router.callback_query(lambda c: c.data == "user_editor")
async def user_editor_menu(callback_query: CallbackQuery):
    """
    Обрабатывает запрос на отображение меню редактора пользователей.

    Отправляет сообщение с кнопками для выбора метода поиска пользователей.

    Параметры:
    - callback_query (CallbackQuery): Объект обратного вызова, содержащий информацию о запросе.

    Ответы:
    - Отправляет сообщение с кнопками для выбора метода поиска.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поиск по имени ключа", callback_data="search_by_key_name")],
        [InlineKeyboardButton(text="Поиск по tg_id", callback_data="search_by_tg_id")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_admin_menu")]
    ])
    await callback_query.message.edit_text("Выберите метод поиска:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "back_to_admin_menu")
async def back_to_admin_menu(callback_query: CallbackQuery):
    """
    Обрабатывает запрос на возврат в меню администратора.

    Отправляет сообщение с кнопками для доступа к статистике пользователей и редактору пользователей.

    Параметры:
    - callback_query (CallbackQuery): Объект обратного вызова, содержащий информацию о запросе.

    Ответы:
    - Отправляет сообщение с кнопками для возврата в панель администратора.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Статистика пользователей", callback_data="user_stats")],
        [InlineKeyboardButton(text="Редактор пользователей", callback_data="user_editor")]
    ])
    await callback_query.message.edit_text("Панель администратора", reply_markup=keyboard)

async def handle_error(tg_id, callback_query, message):
    """
    Обрабатывает ошибку, отправляя сообщение о ней пользователю.

    Параметры:
    - tg_id (int): Telegram ID пользователя, которому будет отправлено сообщение.
    - callback_query (CallbackQuery): Объект обратного вызова, содержащий информацию о запросе.
    - message (str): Сообщение об ошибке для отправки пользователю.

    Ответы:
    - Редактирует сообщение с ошибкой в чате пользователя.
    """
    await bot.edit_message_text(message, chat_id=tg_id, message_id=callback_query.message.message_id)