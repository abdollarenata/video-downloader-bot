"""
🤖 MAIN.PY - Основной Telegram-бот
Обработчики команд, сообщений и функции отправки видео
"""

import telebot
import threading
import time
from pathlib import Path

from config import (
    BOT_TOKEN, EMOJI, SUPPORTED_PLATFORMS, DOWNLOADS_DIR,
    MAX_VIDEO_SIZE_MB, TELEGRAM_MAX_FILE_SIZE_MB, SPAM_LIMIT_PER_USER, SPAM_WINDOW_SECONDS
)
from utils import (
    logger, is_valid_url, extract_url_from_text, get_file_size_mb,
    remove_file, clean_downloads_dir, rate_limiter, format_file_size, sanitize_filename
)
from downloader import (
    download_video, get_video_info, is_playlist, get_playlist_info,
    get_estimated_quality_and_size, download_queue
)

# ============= ИНИЦИАЛИЗАЦИЯ БОТА =============

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# Хранилище временных сообщений для обновления статуса
user_messages = {}  # {user_id: message_id}

logger.info("🚀 Telegram-бот запущен!")


# ============= КОМАНДА /START =============

@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Обработчик команды /start
    """
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    logger.info(f"👤 Новый пользователь: {user_name} (ID: {user_id})")
    
    welcome_text = f"""
{EMOJI['start']} <b>Добро пожаловать в Video Downloader Bot!</b>

Привет, <b>{user_name}</b>! {EMOJI['video']}

Я помогу тебе скачивать видео с любимых платформ.

<b>Как использовать:</b>
{EMOJI['link']} Просто отправь мне ссылку на видео, и я скачаю его для тебя!

<b>Команды:</b>
/help - Детальная справка
/audio &lt;ссылка&gt; - Скачать только звук

<b>Поддерживаемые платформы:</b>
"""
    
    for platform in SUPPORTED_PLATFORMS:
        welcome_text += f"\n• {platform}"
    
    welcome_text += f"""

{EMOJI['warning']} <b>Ограничения:</b>
• Максимальный размер видео: {TELEGRAM_MAX_FILE_SIZE_MB} МБ
• Не более {SPAM_LIMIT_PER_USER} запросов в минуту
• Большие плейлисты не поддерживаются

{EMOJI['info']} <u>Важно:</u> Я скачиваю только публичный контент. Убедись, что у тебя есть право на скачивание видео!

Жду твою ссылку! {EMOJI['download']}
"""
    
    try:
        bot.send_message(message.chat.id, welcome_text)
    except Exception as e:
        logger.error(f"Ошибка при отправке приветствия: {e}")
        bot.send_message(message.chat.id, f"{EMOJI['error']} Произошла ошибка!")


# ============= КОМАНДА /HELP =============

@bot.message_handler(commands=['help'])
def handle_help(message):
    """
    Обработчик команды /help
    """
    help_text = f"""
{EMOJI['help']} <b>СПРАВКА - Как использовать бота</b>

<b>1️⃣ Скачивание видео:</b>
Просто отправь мне ссылку:
• instagram.com/...
• tiktok.com/...
• youtube.com/...
• twitter.com/...
• И многие другие!

<b>2️⃣ Скачивание только звука:</b>
Напиши команду с ссылкой:
<code>/audio https://youtube.com/watch?v=...</code>

{EMOJI['download']} <b>Процесс:</b>
1. Бот получает твою ссылку
2. Проверяет доступность видео
3. Скачивает видео в лучшем качестве
4. Отправляет тебе в Telegram
5. Удаляет временный файл

{EMOJI['warning']} <b>Важные ограничения:</b>
• <b>Размер:</b> До {TELEGRAM_MAX_FILE_SIZE_MB} МБ (как документ)
• <b>Спам-защита:</b> {SPAM_LIMIT_PER_USER} запросов в {SPAM_WINDOW_SECONDS}с
• <b>Плейлисты:</b> Большие плейлисты могут быть недоступны
• <b>Время:</b> Скачивание может занять до 10 минут

{EMOJI['info']} <b>Типы видео:</b>
• <b>До {MAX_VIDEO_SIZE_MB} МБ:</b> Отправляется как видео (быстро)
• <b>Свыше {MAX_VIDEO_SIZE_MB} МБ:</b> Отправляется как документ (безопаснее)

{EMOJI['error']} <b>Если что-то не работает:</b>
• Проверь ссылку - она должна быть правильной
• Убедись, что видео публичное
• Дождись завершения предыдущего скачивания
• Попробуй позже

<b>Примеры ссылок:</b>
✅ https://www.instagram.com/p/ABC123/
✅ https://www.tiktok.com/@user/video/123456
✅ https://www.youtube.com/watch?v=dQw4w9WgXcQ
✅ https://twitter.com/user/status/123456789

{EMOJI['success']} Готов помочь! Отправь ссылку сейчас!
"""
    
    try:
        bot.send_message(message.chat.id, help_text)
    except Exception as e:
        logger.error(f"Ошибка при отправке справки: {e}")


# ============= КОМАНДА /AUDIO =============

@bot.message_handler(commands=['audio'])
def handle_audio(message):
    """
    Обработчик команды /audio <ссылка>
    Скачивает только звук из видео
    """
    user_id = message.from_user.id
    
    # Проверяем спам
    if not rate_limiter.is_allowed(user_id, SPAM_LIMIT_PER_USER, SPAM_WINDOW_SECONDS):
        remaining = rate_limiter.get_remaining_time(user_id, SPAM_WINDOW_SECONDS)
        error_msg = f"{EMOJI['warning']} Слишком много запросов! Подожди {remaining} секунд."
        bot.send_message(message.chat.id, error_msg)
        logger.warning(f"Спам от пользователя {user_id}")
        return
    
    # Извлекаем ссылку
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(
            message.chat.id,
            f"{EMOJI['error']} Использование: /audio &lt;ссылка&gt;\n\n"
            f"Пример: /audio https://youtube.com/watch?v=..."
        )
        return
    
    url = args[1]
    
    if not is_valid_url(url):
        bot.send_message(
            message.chat.id,
            f"{EMOJI['error']} Некорректная ссылка! Она должна начинаться с http:// или https://"
        )
        return
    
    # Обработка скачивания аудио
    process_audio_download(message, url)


# ============= ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ (ССЫЛКИ) =============

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_message(message):
    """
    Обработчик текстовых сообщений (ищет ссылки)
    """
    user_id = message.from_user.id
    text = message.text
    
    # Пропускаем если это команда
    if text.startswith('/'):
        return
    
    # Проверяем спам
    if not rate_limiter.is_allowed(user_id, SPAM_LIMIT_PER_USER, SPAM_WINDOW_SECONDS):
        remaining = rate_limiter.get_remaining_time(user_id, SPAM_WINDOW_SECONDS)
        error_msg = (
            f"{EMOJI['warning']} <b>Слишком много запросов!</b>\n\n"
            f"Подожди ещё <b>{remaining}</b> секунд."
        )
        bot.send_message(message.chat.id, error_msg)
        logger.warning(f"Спам от пользователя {user_id}: {text[:50]}")
        return
    
    # Ищем ссылку в тексте
    url = extract_url_from_text(text)
    
    if not url:
        bot.send_message(
            message.chat.id,
            f"{EMOJI['info']} Я не нашёл ссылку в твоём сообщении.\n\n"
            f"Пожалуйста, отправь мне ссылку на видео (начинающуюся с http или https).\n\n"
            f"Напишите /help для справки."
        )
        return
    
    # Обработка скачивания видео
    process_video_download(message, url)


# ============= ОСНОВНЫЕ ФУНКЦИИ ОБРАБОТКИ =============

def process_video_download(message, url):
    """
    Основная функция обработки скачивания видео
    
    Args:
        message: Объект сообщения Telegram
        url: URL видео
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    try:
        # Отправляем статус "Проверка"
        status_msg = bot.send_message(
            chat_id,
            f"{EMOJI['search']} <b>Проверяю ссылку...</b>\n\n"
            f"🔗 {url[:50]}..."
        )
        user_messages[user_id] = status_msg.message_id
        
        logger.info(f"👤 {user_id} запросил: {url}")
        
        # Получаем информацию о видео
        video_info = get_video_info(url)
        if not video_info:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"{EMOJI['error']} <b>Ошибка!</b>\n\n"
                f"Не удалось получить информацию о видео.\n\n"
                f"Возможные причины:\n"
                f"• Ссылка неправильная\n"
                f"• Видео было удалено\n"
                f"• Видео недоступно"
            )
            return
        
        # Проверяем плейлист
        if '_type' in video_info and video_info['_type'] == 'playlist':
            entries = video_info.get('entries', [])
            if len(entries) > 5:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=f"{EMOJI['warning']} <b>Плейлист содержит {len(entries)} видео</b>\n\n"
                    f"К сожалению, я не могу скачать такой большой плейлист.\n\n"
                    f"Пожалуйста, отправь ссылку на отдельное видео."
                )
                return
        
        # Обновляем статус
        title = video_info.get('title', 'Video')[:50]
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"{EMOJI['download']} <b>Скачиваю видео...</b>\n\n"
            f"📌 <b>{title}</b>\n\n"
            f"{EMOJI['loading']} Это может занять некоторое время..."
        )
        
        # Скачиваем видео
        task_id = f"{user_id}_{int(time.time())}"
        result = download_video(url, task_id=task_id)
        
        if not result['success']:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"{EMOJI['error']} <b>Ошибка при скачивании</b>\n\n"
                f"<code>{result['error']}</code>"
            )
            logger.error(f"Ошибка скачивания для {user_id}: {result['error']}")
            return
        
        # Файл успешно скачан
        file_path = result['file']
        file_size_mb = result['size_mb']
        
        logger.info(f"✅ Видео скачано: {file_path} ({file_size_mb:.1f} МБ)")
        
        # Обновляем статус
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"{EMOJI['success']} <b>Видео готово!</b>\n\n"
            f"📌 {result['title']}\n"
            f"📊 Размер: {format_file_size(file_size_mb * 1024 * 1024)}\n\n"
            f"{EMOJI['loading']} Отправляю файл..."
        )
        
        # Отправляем видео
        send_video_to_user(chat_id, file_path, result['title'])
        
        # Обновляем финальный статус
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"{EMOJI['success']} <b>Готово!</b>\n\n"
            f"Видео успешно отправлено! {EMOJI['video']}"
        )
        
        # Удаляем файл
        remove_file(file_path)
        
    except Exception as e:
        logger.error(f"Критическая ошибка при скачивании: {e}")
        bot.send_message(
            chat_id,
            f"{EMOJI['error']} <b>Критическая ошибка!</b>\n\n"
            f"Что-то пошло не так. Попробуй позже."
        )


def process_audio_download(message, url):
    """
    Функция обработки скачивания только звука
    
    Args:
        message: Объект сообщения Telegram
        url: URL видео
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    try:
        # Отправляем статус
        status_msg = bot.send_message(
            chat_id,
            f"{EMOJI['music']} <b>Скачиваю звук...</b>\n\n"
            f"🔗 {url[:50]}...\n\n"
            f"{EMOJI['loading']} Преобразую видео в аудио..."
        )
        user_messages[user_id] = status_msg.message_id
        
        logger.info(f"👤 {user_id} запросил аудио: {url}")
        
        # Скачиваем аудио
        task_id = f"{user_id}_audio_{int(time.time())}"
        result = download_video(url, task_id=task_id, is_audio=True)
        
        if not result['success']:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"{EMOJI['error']} <b>Ошибка при скачивании</b>\n\n"
                f"<code>{result['error']}</code>"
            )
            return
        
        # Файл успешно скачан
        file_path = result['file']
        file_size_mb = result['size_mb']
        
        logger.info(f"✅ Аудио скачано: {file_path} ({file_size_mb:.1f} МБ)")
        
        # Обновляем статус
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"{EMOJI['success']} <b>Готово!</b>\n\n"
            f"🎵 {result['title']}\n"
            f"📊 Размер: {format_file_size(file_size_mb * 1024 * 1024)}\n\n"
            f"{EMOJI['loading']} Отправляю файл..."
        )
        
        # Отправляем аудиофайл
        with open(file_path, 'rb') as audio_file:
            bot.send_audio(
                chat_id,
                audio_file,
                title=result['title'],
                caption=f"🎵 {result['title']}"
            )
        
        # Удаляем файл
        remove_file(file_path)
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"{EMOJI['success']} <b>Готово!</b>\n\nАудио успешно отправлено! 🎵"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при скачивании аудио: {e}")
        bot.send_message(
            chat_id,
            f"{EMOJI['error']} <b>Ошибка!</b>\n\nНе удалось скачать аудио."
        )


def send_video_to_user(chat_id, file_path, title):
    """
    Отправляет видео пользователю в зависимости от размера
    
    Args:
        chat_id: ID чата
        file_path: Путь к файлу видео
        title: Название видео
    """
    try:
        file_size_mb = get_file_size_mb(file_path)
        
        with open(file_path, 'rb') as video_file:
            if file_size_mb < MAX_VIDEO_SIZE_MB:
                # Отправляем как видео
                bot.send_video(
                    chat_id,
                    video_file,
                    caption=f"🎬 <b>{title}</b>\n\n"
                            f"📊 Размер: {format_file_size(file_size_mb * 1024 * 1024)}\n"
                            f"✅ Готово к просмотру!",
                    supports_streaming=True
                )
                logger.info(f"✅ Видео отправлено как send_video ({file_size_mb:.1f} МБ)")
            else:
                # Отправляем как документ
                bot.send_document(
                    chat_id,
                    video_file,
                    caption=f"🎬 <b>{title}</b>\n\n"
                            f"📊 Размер: {format_file_size(file_size_mb * 1024 * 1024)}\n"
                            f"ℹ️ Отправлено как документ (файл слишком большой для видео)"
                )
                logger.info(f"✅ Видео отправлено как send_document ({file_size_mb:.1f} МБ)")
    
    except Exception as e:
        logger.error(f"Ошибка при отправке видео: {e}")
        bot.send_message(
            chat_id,
            f"{EMOJI['error']} <b>Ошибка при отправке видео</b>\n\n"
            f"Пожалуйста, попробуй позже."
        )


# ============= ОЧИСТКА И ОБСЛУЖИВАНИЕ =============

def cleanup_thread():
    """
    Фоновый поток для периодической очистки старых файлов
    """
    while True:
        try:
            clean_downloads_dir()
            time.sleep(300)  # Очищаем каждые 5 минут
        except Exception as e:
            logger.error(f"Ошибка при очистке: {e}")


# ============= ЗАПУСК БОТА =============

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("🤖 Telegram Video Downloader Bot")
    logger.info("=" * 50)
    
    # Запускаем поток очистки
    cleanup = threading.Thread(target=cleanup_thread, daemon=True)
    cleanup.start()
    logger.info("✅ Поток очистки запущен")
    
    # Запускаем бота
    logger.info("🚀 Бот готов к работе! Полинг сообщений...")
    
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=30)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
