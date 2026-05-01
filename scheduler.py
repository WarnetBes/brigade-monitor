"""
scheduler.py
Автоэкспорт Excel каждые 2 часа + итоговый отчёт в 23:30
APШедулер запускается внутри Flask
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from export_to_excel import export_tasks_to_excel

load_dotenv()
log = logging.getLogger(__name__)

EXPORT_DIR   = Path(os.getenv("EXPORT_DIR", "exports"))
KEEP_FILES   = int(os.getenv("EXPORT_KEEP_FILES", 48))
TZ           = os.getenv("TZ", "Europe/Moscow")


def run_export(label: str = "") -> str:
    """Run Excel export and cleanup old files."""
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    name = f"brigade_{label}_{ts}.xlsx" if label else f"brigade_{ts}.xlsx"
    out  = str(EXPORT_DIR / name)
    try:
        export_tasks_to_excel(output_path=out)
        log.info(f"✅ Экспорт: {out}")
        # Удаляем старые файлы
        files = sorted(EXPORT_DIR.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
        for old in files[KEEP_FILES:]:
            old.unlink()
            log.info(f"Удалён старый файл: {old}")
    except Exception as e:
        log.error(f"Экспорт не удался: {e}")
    return out


def start_scheduler():
    """Start background scheduler."""
    scheduler = BackgroundScheduler(timezone=TZ)

    # Экспорт каждые 2 часа (6,8,10,12,14,16,18,20,22)
    scheduler.add_job(
        lambda: run_export("auto"),
        CronTrigger(hour="6,8,10,12,14,16,18,20,22", minute=0, timezone=TZ),
        id="auto_export"
    )
    # Итоговый отчёт в 23:30
    scheduler.add_job(
        lambda: run_export("итог_смены"),
        CronTrigger(hour=23, minute=30, timezone=TZ),
        id="daily_report"
    )

    scheduler.start()
    log.info("✅ Планировщик запущен: экспорт каждые 2ч, итог в 23:30")
    return scheduler


if __name__ == "__main__":
    s = start_scheduler()
    print("Планировщик работает. Ctrl+C для остановки.")
    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        s.shutdown()
