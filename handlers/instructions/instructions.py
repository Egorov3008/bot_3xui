import os

from aiogram import types
from aiogram.types import (BufferedInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup)

from handlers.texts import INSTRUCTIONS


async def send_instructions(callback_query: types.CallbackQuery):
    """
    Обрабатывает запрос на отправку инструкций пользователю.

    Удаляет сообщение с кнопкой, отправляет изображение инструкций
    и текст с инструкциями. Если изображение не найдено,
    отправляет сообщение об ошибке. Также добавляет кнопку для
    возврата к главному меню.

    Args:
        callback_query (types.CallbackQuery): Объект обратного вызова,
            содержащий информацию о запросе от пользователя и его сообщении.
    """
    await callback_query.message.delete()

    instructions_message = (
        INSTRUCTIONS
    )

    # Формируем путь к изображению инструкций
    image_path = os.path.join(os.path.dirname(file), 'instructions.jpg')

    # Проверяем, существует ли файл изображения
    if not os.path.isfile(image_path):
        await callback_query.message.answer("Файл изображения не найден.")
        await callback_query.answer()
        return

    # Создаем кнопку "Назад" для возврата в главное меню
    back_button = InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_button]])

    # Открываем изображение и отправляем его пользователю
    with open(image_path, 'rb') as image_from_buffer:
        await callback_query.message.answer_photo(
            BufferedInputFile(image_from_buffer.read(), filename="instructions.jpg"),
            caption=instructions_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    # Подтверждаем обработку обратного вызова
    await callback_query.answer()