"""
keyword_filter.py
Классификатор сообщений для бригадира — Партия Еды
5 направлений, 5 статусов, срочные алерты
"""

import re
from datetime import datetime

# ── Направления цехов ─────────────────────────────────
DIRECTION_KEYWORDS = {
    "Перемещение": [
        "перемещ", "перевоз", "транспорт", "погруз", "разгруз",
        "доставк", "привез", "вывоз"
    ],
    "Растарка": [
        "растарк", "распаков", "тара", "вскрыт", "разбор",
        "склад", "сырьё"
    ],
    "Доделки": [
        "доделк", "доработ", "докомплект",
        "доделать", "дошить", "докласт", "допар"
    ],
    "Готовая продукция": [
        "готовая", "готов прод", "гп ", " гп",
        "фасовк", "упаков", "отгруз", "выставл", "finished"
    ],
    "Сборочная": [
        "сборк", "сборочн", "комплект", "набор",
        "assembly", "линия", "участок"
    ],
}

# ── Статусы ──────────────────────────────────────────
STATUS_KEYWORDS = {
    "Выполнено": [
        "готово", "сделано", "выполнен", "закрыто",
        "завершен", "исполнен", "готов", "done", "ready"
    ],
    "В работе": [
        "в работе", "делается", "начало", "запустили",
        "работаем", "идёт", "in progress"
    ],
    "Проблема": [
        "проблем", "нет людей", "нет материал",
        "брак", "поломк", "авария", "неисправн"
    ],
    "Задержка": [
        "задержк", "запоздан", "не успел",
        "перенос", "отложен", "позже"
    ],
    "Не начато": [
        "не начал", "ещё не", "ждём",
        "план", "по плану", "скоро"
    ],
}

# ── Стоп-слова (мгновенный алерт бригадиру) ─────────
URGENT_KEYWORDS = [
    "срочно", "срочная", "срочный",
    "стоп", "стоим", "встали", "не работает",
    "авария", "аварийная",
    "необходимо срочно", "нужны люди",
    "!срочно", "urgent", "asap",
]


def find_directions(text: str) -> list[str]:
    """Returns list of matched directions."""
    text_l = text.lower()
    return [
        direction
        for direction, keywords in DIRECTION_KEYWORDS.items()
        if any(kw in text_l for kw in keywords)
    ]


def find_status(text: str) -> str:
    """Returns most relevant status string."""
    text_l = text.lower()
    for status, keywords in STATUS_KEYWORDS.items():
        if any(kw in text_l for kw in keywords):
            return status
    return "Не начато"


def is_urgent(text: str) -> bool:
    """Returns True if message contains urgent stop-words."""
    text_l = text.lower()
    return any(kw in text_l for kw in URGENT_KEYWORDS)


def classify(text: str, group: str = "", source: str = "telegram") -> dict:
    """
    Полная классификация сообщения.
    Возвращает dict со всеми полями для tasks.json
    """
    directions = find_directions(text)
    status = find_status(text)
    urgent = is_urgent(text)

    # Если есть стоп-слова — статус авто — Проблема
    if urgent and status == "Не начато":
        status = "Проблема"

    return {
        "text": text,
        "directions": directions if directions else ["Не определено"],
        "direction": directions[0] if directions else "Не определено",
        "status": status,
        "urgent": urgent,
        "source": source,
        "group": group,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    tests = [
        "Растарка по складу А завершена",
        "Срочно! Сборочная линия 2 встала, нужен человек",
        "Доделки по заказу 1542 ещё не начали",
        "Готовая продукция выставлена на отгрузку",
        "Перемещение по цеху 3 задержка",
    ]
    for t in tests:
        r = classify(t)
        print(f"[{r['direction']}] [{r['status']}] urgent={r['urgent']} | {t[:50]}")
