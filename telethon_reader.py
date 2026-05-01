"""
telethon_reader.py
Чтение Telegram-групп от вашего аккаунта (не бот!)
Работает даже если вы не админ группы
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from keyword_filter import classify

load_dotenv()
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# ── Конфиг ───────────────────────────────────────────────
API_ID   = int(os.getenv("TG_API_ID", 0))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION  = os.getenv("TG_SESSION_STRING", "")
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
LEADER_ID = int(os.getenv("BRIGADE_LEADER_ID", 0))
TASKS_FILE = Path("tasks.json")
MEDIA_DIR  = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)

# ID групп для мониторинга (заполнить в .env)
raw_chats = os.getenv("TG_CHATS", "")
MONITORED_CHATS = [
    int(c.strip()) for c in raw_chats.split(",") if c.strip()
]


# ── Хранение задач ─────────────────────────────────────────
def load_tasks() -> list:
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    return []


def save_task(task: dict) -> None:
    tasks = load_tasks()
    task["id"] = str(uuid.uuid4())[:8]
    tasks.insert(0, task)
    tasks = tasks[:500]  # храним не больше 500 последних
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"✅ Задача сохранена: [{task['direction']}] [{task['status']}] {task['text'][:60]}")


# ── Отправка срочного алерта бригадиру ──────────────────
async def send_urgent_alert(bot_client, task: dict) -> None:
    if not LEADER_ID:
        return
    msg = (
        f"🚨 СРОЧНО!\n"
        f"━" * 30 + "\n"
        f"📍 Чат: {task['group']}\n"
        f"📂 Направление: {task['direction']}\n"
        f"📌 Статус: {task['status']}\n"
        f"━" * 30 + "\n"
        f"💬 {task['text'][:200]}"
    )
    try:
        await bot_client.send_message(LEADER_ID, msg)
    except Exception as e:
        log.error(f"Алерт не отправлен: {e}")


# ── Главная функция ─────────────────────────────────────────
async def main():
    # User-client для чтения групп
    user_client = TelegramClient(
        StringSession(SESSION), API_ID, API_HASH
    )
    # Bot-client для отправки алертов
    bot_client = TelegramClient("bot_session", API_ID, API_HASH)

    await user_client.start()
    await bot_client.start(bot_token=BOT_TOKEN)
    log.info("✅ Telethon запущен, слушаю группы...")

    @user_client.on(events.NewMessage(chats=MONITORED_CHATS or None))
    async def handler(event):
        msg = event.message
        text = msg.text or ""
        group = ""
        try:
            chat = await event.get_chat()
            group = getattr(chat, "title", str(chat.id))
        except Exception:
            pass

        # Фото или документ — сохраняем медиа
        media_path = None
        if msg.photo or msg.document:
            try:
                media_path = str(
                    await msg.download_media(file=str(MEDIA_DIR))
                )
                log.info(f"🖼 Медиа сохранено: {media_path}")
            except Exception as e:
                log.warning(f"Медиа не сохранено: {e}")

        if not text and not media_path:
            return  # игнорируем пустые

        task = classify(text, group=group, source="telegram")
        if media_path:
            task["media_path"] = media_path

        save_task(task)

        if task["urgent"]:
            await send_urgent_alert(bot_client, task)

    await user_client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
