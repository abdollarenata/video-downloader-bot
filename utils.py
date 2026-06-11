"""
🛠️ UTILS.PY - Вспомогательные функции
Логирование, работа с файлами, проверка и валидация
"""

import logging
import os
import shutil
from pathlib import Path
from datetime import datetime
from config import LOG_LEVEL, LOG_FORMAT, LOGS_DIR, DOWNLOADS_DIR

# ============= ЛОГИРОВАНИЕ =============

def setup_logger(name):
    """
    Настраивает логгер для модуля
    
    Args:
        name: Имя логгера (обычно __name__)
    
    Returns:
        logger: Объект логгера
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Формат логирования
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Обработчик для файла
    log_file = LOGS_DIR / f'bot_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logger(__name__)


# ============= РАБОТА С ФАЙЛАМИ =============

def get_file_size_mb(file_path):
    """
    Получает размер файла в МБ
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        float: Размер файла в МБ
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError as e:
        logger.error(f"Ошибка при получении размера файла: {e}")
        return 0


def clean_downloads_dir():
    """
    Очищает папку downloads от старых файлов
    Удаляет файлы старше 1 часа
    """
    try:
        now = datetime.now()
        for file in DOWNLOADS_DIR.glob('*'):
            if file.is_file():
                file_age_seconds = (now - datetime.fromtimestamp(file.stat().st_mtime)).total_seconds()
                # Удаляем файлы старше 1 часа
                if file_age_seconds > 3600:
                    file.unlink()
                    logger.info(f"Удалён файл: {file.name}")
    except Exception as e:
        logger.error(f"Ошибка при очистке папки downloads: {e}")


def remove_file(file_path):
    """
    Удаляет файл
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        bool: True если успешно, False если ошибка
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Файл удалён: {file_path}")
            return True
    except Exception as e:
        logger.error(f"Ошибка при удалении файла {file_path}: {e}")
    return False


def get_file_extension(file_path):
    """
    Получает расширение файла
    
    Args:
        file_path: Путь к файлу
    
    Returns:
        str: Расширение (включая точку)
    """
    return Path(file_path).suffix.lower()


# ============= ВАЛИДАЦИЯ =============

def is_valid_url(url):
    """
    Проверяет, является ли строка валидной ссылкой
    
    Args:
        url: Строка для проверки
    
    Returns:
        bool: True если валидная ссылка
    """
    if not url:
        return False
    return url.strip().startswith(('http://', 'https://'))


def extract_url_from_text(text):
    """
    Извлекает первую ссылку из текста
    
    Args:
        text: Текст для поиска
    
    Returns:
        str: Найденная ссылка или None
    """
    import re
    urls = re.findall(r'https?://[^\s]+', text)
    return urls[0] if urls else None


# ============= ФОРМАТИРОВАНИЕ =============

def format_file_size(size_bytes):
    """
    Форматирует размер файла в читаемый вид
    
    Args:
        size_bytes: Размер в байтах
    
    Returns:
        str: Форматированный размер (1.5 МБ, 2.3 ГБ и т.д.)
    """
    for unit in ['B', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"


def sanitize_filename(filename):
    """
    Очищает имя файла от неразрешённых символов
    
    Args:
        filename: Исходное имя файла
    
    Returns:
        str: Очищенное имя
    """
    import re
    # Заменяем проблемные символы
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Убираем многоточия в конце
    filename = filename.rstrip('.')
    # Ограничиваем длину имени
    return filename[:200]


# ============= СПАМ-ЗАЩИТА =============

class RateLimiter:
    """
    Класс для защиты от спама (анти-флуд)
    Отслеживает количество запросов от пользователя
    """
    
    def __init__(self):
        self.users = {}  # {user_id: [timestamp1, timestamp2, ...]}
    
    def is_allowed(self, user_id, limit=5, window=60):
        """
        Проверяет, может ли пользователь выполнить действие
        
        Args:
            user_id: ID пользователя
            limit: Максимум действий в окне
            window: Временное окно в секундах
        
        Returns:
            bool: True если действие разрешено
        """
        now = datetime.now().timestamp()
        
        if user_id not in self.users:
            self.users[user_id] = []
        
        # Удаляем старые записи
        self.users[user_id] = [ts for ts in self.users[user_id] if now - ts < window]
        
        # Проверяем лимит
        if len(self.users[user_id]) >= limit:
            return False
        
        # Добавляем новую запись
        self.users[user_id].append(now)
        return True
    
    def get_remaining_time(self, user_id, window=60):
        """
        Получает оставшееся время до возможности нового запроса
        
        Args:
            user_id: ID пользователя
            window: Временное окно в секундах
        
        Returns:
            int: Оставшиеся секунды или 0
        """
        if user_id not in self.users or not self.users[user_id]:
            return 0
        
        now = datetime.now().timestamp()
        oldest_request = self.users[user_id][0]
        remaining = int(window - (now - oldest_request)) + 1
        
        return max(0, remaining)


# Глобальный экземпляр rate limiter
rate_limiter = RateLimiter()


logger.info("✅ Utils инициализирован")
