"""
server.py
Flask API — принимает вебхуки Telegram и Яндекс
Отдаёт задачи для дашборда
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from dotenv import load_dotenv

from keyword_filter import classify

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "brigade-secret")

TASKS_FILE = Path("tasks.json")
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))
EXPORT_DIR.mkdir(exist_ok=True)


def load_tasks():
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    return []


def save_tasks(tasks):
    TASKS_FILE.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── REST API ──────────────────────────────────────────
@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    tasks = load_tasks()
    # Фильтры
    source    = request.args.get("source")
    direction = request.args.get("direction")
    status    = request.args.get("status")
    urgent    = request.args.get("urgent")
    if source:    tasks = [t for t in tasks if t.get("source") == source]
    if direction: tasks = [t for t in tasks if t.get("direction") == direction]
    if status:    tasks = [t for t in tasks if t.get("status") == status]
    if urgent:    tasks = [t for t in tasks if t.get("urgent") == (urgent == "true")]
    return jsonify(tasks)


@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.json or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "text required"}), 400
    task = classify(text,
                    group=data.get("group", "Ручной ввод"),
                    source=data.get("source", "manual"))
    task["id"] = str(uuid.uuid4())[:8]
    tasks = load_tasks()
    tasks.insert(0, task)
    save_tasks(tasks[:500])
    return jsonify(task), 201


@app.route("/api/tasks/<task_id>", methods=["PATCH"])
def update_task(task_id):
    data = request.json or {}
    tasks = load_tasks()
    for t in tasks:
        if t.get("id") == task_id:
            t.update({k: v for k, v in data.items() if k in ("status", "direction", "comment")})
            t["updated_at"] = datetime.now().isoformat()
            save_tasks(tasks)
            return jsonify(t)
    return jsonify({"error": "not found"}), 404


@app.route("/api/stats", methods=["GET"])
def get_stats():
    tasks = load_tasks()
    total = len(tasks)
    done  = sum(1 for t in tasks if t.get("status") == "Выполнено")
    urgent = sum(1 for t in tasks if t.get("urgent"))
    in_work = sum(1 for t in tasks if t.get("status") == "В работе")
    problems = sum(1 for t in tasks if t.get("status") in ("Проблема", "Задержка"))
    return jsonify({
        "total": total, "done": done, "urgent": urgent,
        "in_work": in_work, "problems": problems,
        "done_pct": round(done / total * 100) if total else 0
    })


# ── Telegram webhook ─────────────────────────────────
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.json or {}
    msg  = data.get("message", {})
    text = msg.get("text", "")
    if not text:
        return "ok"
    group = msg.get("chat", {}).get("title", "Telegram Bot")
    task  = classify(text, group=group, source="telegram_bot")
    task["id"] = str(uuid.uuid4())[:8]
    tasks = load_tasks()
    tasks.insert(0, task)
    save_tasks(tasks[:500])
    return "ok"


# ── Дашборд ────────────────────────────────────────
@app.route("/")
def dashboard():
    return send_file("dashboard.html")


@app.route("/api/export/download")
def download_latest():
    files = sorted(EXPORT_DIR.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return jsonify({"error": "No exports yet"}), 404
    return send_file(files[0], as_attachment=True)


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=False)
