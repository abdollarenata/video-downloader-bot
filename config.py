"""
📋 CONFIG.PY - Конфигурация и константы бота
Здесь хранятся все настройки, параметры и константы приложения
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Загружаем переменные окружения из .env файла
load_dotenv()

# ============= ТОКЕНЫ И КЛЮЧИ =============
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ Ошибка: BOT_TOKEN не найден в .env файле!")

# ============= ПУТИ И ПАПКИ =============
BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / 'downloads'
DOWNLOADS_DIR.mkdir(exist_ok=True)  # Создаём папку, если её нет

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# ============= ОГРАНИЧЕНИЯ И ЛИМИТЫ =============
MAX_VIDEO_SIZE_MB = 50  # Максимальный размер для send_video (в МБ)
MAX_CONCURRENT_DOWNLOADS = 3  # Максимум одновременных скачиваний
DOWNLOAD_TIMEOUT = 600  # Таймаут скачивания в секундах (10 минут)
SPAM_LIMIT_PER_USER = 5  # Максимум запросов в минуту на пользователя
SPAM_WINDOW_SECONDS = 60  # Временное окно для проверки спама (1 минута)

# ============= РАСШИРЕНИЯ ФАЙЛОВ =============
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm', '.m3u8', '.ts'}
AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.wav', '.aac', '.opus', '.vorbis'}

# ============= YT-DLP ОПЦИИ =============
YT_DLP_VIDEO_OPTIONS = {
    'format': 'best[ext=mp4]/best',  # Лучшее качество в MP4
    'quiet': False,
    'no_warnings': False,
    'socket_timeout': 30,
}

YT_DLP_AUDIO_OPTIONS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': False,
    'no_warnings': False,
    'socket_timeout': 30,
}

# ============= СООБЩЕНИЯ И ЭМОДЗИ =============
EMOJI = {
    'start': '🎬',
    'help': '❓',
    'download': '📥',
    'success': '✅',
    'error': '❌',
    'info': 'ℹ️',
    'loading': '⏳',
    'search': '🔍',
    'music': '🎵',
    'video': '🎥',
    'file': '📁',
    'warning': '⚠️',
    'link': '🔗',
}

# ============= ЛИМИТЫ ТЕЛЕГРАМА =============
TELEGRAM_MAX_FILE_SIZE_MB = 2000  # Максимум для send_document (2000 МБ)
TELEGRAM_MAX_VIDEO_SIZE_MB = 50   # Максимум для send_video (50 МБ)

# ============= УРОВНИ ЛОГИРОВАНИЯ =============
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ============= ПОДДЕРЖИВАЕМЫЕ ПЛАТФОРМЫ =============
SUPPORTED_PLATFORMS = [
    '🔗 Instagram (instagram.com)',
    '🎵 TikTok (tiktok.com)',
    '▶️ YouTube (youtube.com)',
    '📺 YouTube Shorts (youtube.com/shorts)',
    '𝕏 Twitter/X (twitter.com, x.com)',
    '🎭 VK (vk.com)',
    '🎬 Rutube (rutube.ru)',
    '🎪 Dailymotion (dailymotion.com)',
    '🎨 Pinterest (pinterest.com)',
    '📹 Twitch Clips (twitch.tv)',
    'и многие другие...',
]
