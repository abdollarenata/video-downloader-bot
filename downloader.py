"""
📥 DOWNLOADER.PY - Модуль скачивания видео
Управление скачиванием видео, обработка ошибок, работа с yt-dlp
"""

import yt_dlp
import threading
import queue
from pathlib import Path
from datetime import datetime
from config import (
    DOWNLOADS_DIR, MAX_CONCURRENT_DOWNLOADS, DOWNLOAD_TIMEOUT,
    YT_DLP_VIDEO_OPTIONS, YT_DLP_AUDIO_OPTIONS, SUPPORTED_PLATFORMS
)
from utils import logger, get_file_size_mb, sanitize_filename, remove_file


# ============= ГЛОБАЛЬНАЯ ОЧЕРЕДЬ СКАЧИВАНИЙ =============

class DownloadQueue:
    """
    Управляет очередью скачиваний и ограничением одновременных задач
    """
    
    def __init__(self, max_concurrent=MAX_CONCURRENT_DOWNLOADS):
        self.max_concurrent = max_concurrent
        self.active_downloads = {}  # {task_id: download_info}
        self.queue = queue.Queue()
        self.lock = threading.Lock()
    
    def add_download(self, task_id, user_id, url, is_audio=False):
        """
        Добавляет задачу скачивания в очередь
        """
        with self.lock:
            if len(self.active_downloads) >= self.max_concurrent:
                return False
            
            download_info = {
                'task_id': task_id,
                'user_id': user_id,
                'url': url,
                'is_audio': is_audio,
                'status': 'queued',
                'progress': 0,
                'start_time': datetime.now(),
            }
            
            self.active_downloads[task_id] = download_info
            self.queue.put(task_id)
            return True
    
    def remove_download(self, task_id):
        """
        Удаляет задачу из активных скачиваний
        """
        with self.lock:
            if task_id in self.active_downloads:
                del self.active_downloads[task_id]
    
    def get_active_downloads_count(self):
        """Возвращает количество активных скачиваний"""
        with self.lock:
            return len(self.active_downloads)
    
    def get_download_info(self, task_id):
        """
        Получает информацию о скачивании
        """
        with self.lock:
            return self.active_downloads.get(task_id)
    
    def update_progress(self, task_id, progress):
        """
        Обновляет прогресс скачивания
        """
        with self.lock:
            if task_id in self.active_downloads:
                self.active_downloads[task_id]['progress'] = progress


# Глобальный экземпляр очереди
download_queue = DownloadQueue()


# ============= ФУНКЦИИ СКАЧИВАНИЯ =============

def create_yt_dlp_options(is_audio=False, progress_callback=None):
    """
    Создаёт опции для yt-dlp
    """
    if is_audio:
        options = YT_DLP_AUDIO_OPTIONS.copy()
    else:
        options = YT_DLP_VIDEO_OPTIONS.copy()
    
    # Путь для сохранения
    options['outtmpl'] = str(DOWNLOADS_DIR / '%(title)s.%(ext)s')
    options['socket_timeout'] = DOWNLOAD_TIMEOUT
    
    # Добавляем куки для обхода блокировок социальных сетей
    options['cookiefile'] = 'cookies.txt'
    
    # Добавляем callback прогресса если нужен
    if progress_callback:
        options['progress_hooks'] = [progress_callback]
    
    return options


def get_video_info(url):
    """
    Получает информацию о видео без скачивания
    """
    try:
        options = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'cookiefile': 'cookies.txt',  # Добавляем куки для проверки инфо
        }
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    
    except Exception as e:
        logger.error(f"Ошибка при получении информации о видео {url}: {e}")
        return None


def is_playlist(url):
    """
    Проверяет, является ли URL плейлистом
    """
    try:
        info = get_video_info(url)
        if info and '_type' in info:
            return info['_type'] == 'playlist'
    except:
        pass
    return False


def get_playlist_info(url):
    """
    Получает информацию о плейлисте
    """
    try:
        options = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'cookiefile': 'cookies.txt',  # Добавляем куки для проверки плейлиста
        }
        
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    
    except Exception as e:
        logger.error(f"Ошибка при получении информации о плейлисте: {e}")
        return None


def download_video(url, task_id=None, is_audio=False, progress_callback=None):
    """
    Скачивает видео или аудио с помощью yt-dlp
    """
    result = {
        'success': False,
        'file': None,
        'title': None,
        'error': None,
        'size_mb': 0,
    }
    
    try:
        logger.info(f"Начало скачивания: {url} (Audio={is_audio})")
        
        # Создаём опции
        options = create_yt_dlp_options(is_audio=is_audio, progress_callback=progress_callback)
        
        # Скачиваем
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Получаем имя файла
            filename = ydl.prepare_filename(info)
            file_path = DOWNLOADS_DIR / Path(filename).name
            
            # Проверяем существование файла
            if not file_path.exists():
                # Пробуем найти скачанный файл
                for file in DOWNLOADS_DIR.glob('*'):
                    if file.is_file():
                        if file.stat().st_mtime > (datetime.now().timestamp() - 60):
                            file_path = file
                            break
            
            if file_path.exists():
                result['success'] = True
                result['file'] = str(file_path)
                result['title'] = sanitize_filename(info.get('title', 'video'))
                result['size_mb'] = get_file_size_mb(file_path)
                
                logger.info(f"✅ Видео скачано: {result['title']} ({result['size_mb']:.1f} МБ)")
            else:
                result['error'] = 'Файл не был создан'
                logger.error(f"❌ Файл не найден после скачивания: {url}")
        
    except yt_dlp.utils.DownloadError as e:
        result['error'] = f'Ошибка при скачивании: {str(e)[:100]}'
        logger.error(f"❌ Ошибка yt-dlp: {e}")
    
    except Exception as e:
        result['error'] = f'Неожиданная ошибка: {str(e)[:100]}'
        logger.error(f"❌ Неожиданная ошибка: {e}")
    
    finally:
        # Обновляем статус
        if task_id:
            download_queue.remove_download(task_id)
    
    return result


def get_estimated_quality_and_size(url):
    """
    Возвращает примерный размер и качество видео для интерфейса main.py
    """
    info = get_video_info(url)
    if not info:
        return "Неизвестно", 0
    
    # Извлекаем форматы или берем дефолтные значения
    quality = info.get('format_note', '720p')
    filesize = info.get('filesize_approx', 0) or info.get('filesize', 0)
    size_mb = round(filesize / (1024 * 1024), 1) if filesize else 0
    
    return quality, size_mb


def download_video_threaded(url, task_id, is_audio=False, progress_callback=None):
    """
    Скачивает видео в отдельном потоке (неблокирующий вызов)
    """
    thread = threading.Thread(
        target=download_video,
        args=(url, task_id, is_audio, progress_callback),
        daemon=True
    )
    thread.start()
    return thread
