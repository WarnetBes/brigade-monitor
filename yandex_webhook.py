# yandex_webhook.py — обработка вебхуков от Яндекс Мессенджера
import os
import json
import logging
from flask import Blueprint, request, jsonify
from keyword_filter import classify_message
from datetime import datetime

logger = logging.getLogger(__name__)

yandex_bp = Blueprint('yandex', __name__)

# Хранилище задач (общее с server.py через импорт)
tasks = []

YANDEX_BOT_TOKEN = os.getenv('YANDEX_BOT_TOKEN', '')


def get_tasks():
    return tasks


@yandex_bp.route('/yandex/webhook', methods=['POST'])
def yandex_webhook():
    """Принимает вебхук от Яндекс Мессенджера"""
    try:
        data = request.get_json(force=True)
        logger.info(f"Yandex webhook: {json.dumps(data, ensure_ascii=False)[:200]}")

        # Структура события Яндекс Мессенджера
        event_type = data.get('type', '')
        if event_type == 'message_created':
            _handle_message(data)
        return jsonify({'ok': True}), 200
    except Exception as e:
        logger.error(f"Ошибка вебхука Яндекс: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


def _handle_message(data):
    """Обрабатывает входящее сообщение"""
    try:
        message = data.get('message', {})
        text = message.get('text', '') or ''
        chat_id = message.get('chat', {}).get('id', 'unknown')
        sender = message.get('from', {}).get('display_name', 'unknown')
        msg_id = message.get('message_id', '')

        if not text.strip():
            return

        result = classify_message(text)
        if not result['direction']:
            return

        task = {
            'id': msg_id or f"y_{datetime.now().timestamp()}",
            'source': 'yandex',
            'chat_id': str(chat_id),
            'sender': sender,
            'text': text,
            'direction': result['direction'],
            'status': result['status'],
            'urgent': result['urgent'],
            'timestamp': datetime.now().isoformat(),
            'raw': data
        }
        tasks.append(task)
        logger.info(f"[Яндекс] Задача: {task['direction']} | {task['status']} | urgent={task['urgent']}")

        # Срочное уведомление
        if result['urgent']:
            _send_urgent_alert(task)
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения Яндекс: {e}")


def _send_urgent_alert(task):
    """Отправляет срочное уведомление в Telegram"""
    try:
        import requests
        tg_token = os.getenv('TG_BOT_TOKEN', '')
        tg_chat = os.getenv('TG_ALERT_CHAT_ID', '')
        if not tg_token or not tg_chat:
            return
        text = (
            f"🚨 СРОЧНО [Яндекс]\n"
            f"Направление: {task['direction']}\n"
            f"Статус: {task['status']}\n"
            f"От: {task['sender']}\n"
            f"Сообщение: {task['text'][:200]}"
        )
        requests.post(
            f"https://api.telegram.org/bot{tg_token}/sendMessage",
            json={'chat_id': tg_chat, 'text': text, 'parse_mode': 'HTML'},
            timeout=5
        )
    except Exception as e:
        logger.error(f"Ошибка отправки алерта: {e}")
