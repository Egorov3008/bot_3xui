import re
import random
from config import SERVERS


def sanitize_key_name(key_name: str) -> str:
    """Очищает имя ключа, удаляя недопустимые символы.

    Args:
        key_name (str): Исходное имя ключа, которое нужно очистить.

    Returns:
        str: Очищенное имя ключа, содержащее только допустимые символы (a-z, 0-9, @, ., _, -).
    """
    return re.sub(r'[^a-z0-9@._-]', '', key_name.lower())


def generate_random_email() -> str:
    """Генерирует случайный адрес электронной почты.

    Генерируемый адрес состоит из случайной строки из 6 символов (буквы и цифры) и добавляется домен.

    Returns:
        str: Случайный адрес электронной почты в формате {random_string}@example.com.
    """
    random_string = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
    return f"{random_string}@example.com"  # Добавляем домен для полноты


async def get_least_loaded_server(conn):
    """Находит сервер с наименьшей загрузкой.

    Выполняет запрос к базе данных для определения количества текущих подключений к каждому серверу,
    и вычисляет процент загрузки. Возвращает ID сервера с наименьшим процентом загрузки.

    Args:
        conn: Соединение с базой данных для выполнения запросов.

    Returns:
        str: ID сервера с наименьшей загрузкой, или None, если серверов нет.
    """
    least_loaded_server_id = None
    min_load_percentage = float('inf')

    for server_id, server in SERVERS.items():
        count = await conn.fetchval('SELECT COUNT(*) FROM keys WHERE server_id = $1', server_id)
        percent_full = (count / 60) * 100 if count <= 60 else 100
        if percent_full < min_load_percentage:
            min_load_percentage = percent_full
            least_loaded_server_id = server_id

    return least_loaded_server_id