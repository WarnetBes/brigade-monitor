# media_handler.py — OCR обработка фото листов заказов
import os
import logging
import re
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

OCR_UPLOAD_DIR = Path(os.getenv('OCR_UPLOAD_DIR', './ocr_uploads'))


def ensure_upload_dir():
    OCR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def ocr_image(image_path: str) -> str:
    """Распознаёт текст на изображении. Использует PaddleOCR или Tesseract"""
    # Попытка 1: PaddleOCR
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='ru', show_log=False)
        result = ocr.ocr(image_path, cls=True)
        lines = []
        for block in result:
            if block:
                for line in block:
                    lines.append(line[1][0])
        text = '\n'.join(lines)
        logger.info(f"PaddleOCR: распознано {len(lines)} строк")
        return text
    except ImportError:
        logger.warning("PaddleOCR не установлен, пробуем Tesseract")
    except Exception as e:
        logger.error(f"PaddleOCR ошибка: {e}")

    # Попытка 2: Tesseract
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='rus+eng')
        logger.info(f"Tesseract: распознан {len(text)} символов")
        return text
    except ImportError:
        logger.error("Tesseract не установлен!")
    except Exception as e:
        logger.error(f"Tesseract ошибка: {e}")

    return ''


def parse_order_sheet(image_path: str) -> list:
    """Парсит лист заказов: фото → список записей"""
    text = ocr_image(image_path)
    if not text:
        return []

    rows = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Ищем строки с числовыми данными (позиция, количество)
        numbers = re.findall(r'\d+[.,]?\d*', line)
        if numbers:
            rows.append({
                'raw_line': line,
                'numbers': numbers,
                'source': 'ocr',
                'timestamp': datetime.now().isoformat()
            })

    logger.info(f"Парсинг OCR: {len(rows)} строк с данными")
    return rows


def save_uploaded_file(file_bytes: bytes, filename: str) -> str:
    """Сохраняет загруженный файл"""
    ensure_upload_dir()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = re.sub(r'[^\w.-]', '_', filename)
    path = OCR_UPLOAD_DIR / f"{ts}_{safe_name}"
    path.write_bytes(file_bytes)
    logger.info(f"Файл сохранён: {path}")
    return str(path)


def process_telegram_photo(bot, file_id: str) -> list:
    """Скачивает фото из Telegram бота и обрабатывает OCR"""
    try:
        import requests
        tg_token = os.getenv('TG_BOT_TOKEN', '')
        # Получаем URL файла
        resp = requests.get(
            f"https://api.telegram.org/bot{tg_token}/getFile",
            params={'file_id': file_id},
            timeout=10
        )
        file_path = resp.json()['result']['file_path']
        file_url = f"https://api.telegram.org/file/bot{tg_token}/{file_path}"
        # Скачиваем
        file_bytes = requests.get(file_url, timeout=30).content
        saved_path = save_uploaded_file(file_bytes, file_path.split('/')[-1])
        return parse_order_sheet(saved_path)
    except Exception as e:
        logger.error(f"Ошибка обработки фото Telegram: {e}")
        return []
