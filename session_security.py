# session_security.py — безопасное хранение Telegram сессии
import os
import stat
import logging
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

SESSION_DIR = Path(os.getenv('SESSION_DIR', './sessions'))


def ensure_session_dir():
    """Создаёт директорию для сессий с безопасными правами"""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    # Только владелец может читать/писать
    os.chmod(SESSION_DIR, stat.S_IRWXU)
    logger.info(f"Директория сессий: {SESSION_DIR} (chmod 700)")


def get_session_path(name: str = 'brigade') -> str:
    """Возвращает путь к файлу сессии"""
    ensure_session_dir()
    return str(SESSION_DIR / name)


def protect_session_file(session_path: str):
    """Устанавливает chmod 600 на файл сессии"""
    path = Path(session_path + '.session')
    if path.exists():
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        logger.info(f"Сессия защищена: {path} (chmod 600)")


def check_session_integrity(session_path: str) -> bool:
    """Проверяет целостность сессии по хешу"""
    path = Path(session_path + '.session')
    checksum_path = Path(session_path + '.sha256')

    if not path.exists():
        return False

    current_hash = hashlib.sha256(path.read_bytes()).hexdigest()

    if checksum_path.exists():
        saved_hash = checksum_path.read_text().strip()
        if current_hash != saved_hash:
            logger.warning("Сессия изменена внешне! Возможно нарушение безопасности.")
            return False
        return True
    else:
        # Сохраняем первоначальный хеш
        checksum_path.write_text(current_hash)
        logger.info("Контрольная сумма сессии сохранена.")
        return True


def save_session_checksum(session_path: str):
    """Сохраняет хеш после обновления сессии"""
    path = Path(session_path + '.session')
    checksum_path = Path(session_path + '.sha256')
    if path.exists():
        current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        checksum_path.write_text(current_hash)
        protect_session_file(session_path)
        logger.info("Контрольная сумма обновлена.")


def validate_env_secrets():
    """Проверяет наличие обязательных переменных среды"""
    required = [
        'TG_API_ID', 'TG_API_HASH', 'TG_BOT_TOKEN',
        'TG_ALERT_CHAT_ID', 'YANDEX_BOT_TOKEN'
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        logger.error(f"Отсутствуют переменные среды: {missing}")
        return False
    logger.info("Все переменные среды найдены.")
    return True
