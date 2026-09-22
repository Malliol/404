"""
Телеграм-бот для изменения процентной ставки.
Работает без выделенного сервера: запускается по расписанию через
GitHub Actions, забирает новые сообщения, обрабатывает их, сохраняет
состояние обратно в репозиторий и завершается.

Источники изменения ставки:
  - команда /setrate <значение>
  - слайдер в Telegram Mini App (данные приходят как web_app_data)

Переменные окружения:
  BOT_TOKEN         — обязателен, токен бота
  ALLOWED_CHAT_IDS  — опционально, список chat_id через запятую.
                       Если не задан — менять ставку может кто угодно.
  MINIAPP_URL       — опционально, HTTPS-адрес страницы мини-аппа
                       (нужен, чтобы бот присылал кнопку для его открытия)
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import requests

BASE_DIR = Path(__file__).resolve().parent
RATES_PATH = BASE_DIR / "rates.json"
OFFSET_PATH = BASE_DIR / "offset.json"

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_CHAT_IDS = {
    c.strip() for c in os.environ.get("ALLOWED_CHAT_IDS", "").split(",") if c.strip()
}
MINIAPP_URL = os.environ.get("MINIAPP_URL", "").strip()

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def load_json(path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def is_allowed(chat_id):
    if not ALLOWED_CHAT_IDS:
        return True
    return str(chat_id) in ALLOWED_CHAT_IDS


def send_message(chat_id, text, with_miniapp_button=False):
    payload = {"chat_id": chat_id, "text": text}
    if with_miniapp_button and MINIAPP_URL:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": [[
                {"text": "Открыть шкалу ставки", "web_app": {"url": MINIAPP_URL}}
            ]]
        })
    try:
        requests.post(f"{API_URL}/sendMessage", data=payload, timeout=10)
    except requests.RequestException as e:
        print(f"[warn] send_message failed: {e}", file=sys.stderr)


def set_rate(new_rate, rates):
    new_rate = max(0, min(100, new_rate))
    rates["rate"] = new_rate
    rates["updated_at"] = datetime.now(timezone.utc).isoformat()
    return rates


def handle_update(update, rates):
    """Возвращает True, если состояние (rates) изменилось."""
    message = update.get("message")
    if not message:
        return False

    chat_id = message["chat"]["id"]
    changed = False

    web_app_data = message.get("web_app_data")
    if web_app_data:
        try:
            payload = json.loads(web_app_data["data"])
            value = int(payload["rate"])
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            send_message(chat_id, "Не удалось прочитать значение со шкалы.")
            return False

        if not is_allowed(chat_id):
            send_message(chat_id, "У вас нет прав менять ставку.")
            return False

        set_rate(value, rates)
        changed = True
        send_message(chat_id, f"Ставка обновлена: {rates['rate']}%")
        return changed

    text = (message.get("text") or "").strip()

    if text.startswith("/setrate"):
        parts = text.split()
        if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
            send_message(chat_id, "Формат: /setrate 46")
            return False
        if not is_allowed(chat_id):
            send_message(chat_id, "У вас нет прав менять ставку.")
            return False
        set_rate(int(parts[1]), rates)
        changed = True
        send_message(chat_id, f"Ставка обновлена: {rates['rate']}%")

    elif text == "/rate":
        send_message(chat_id, f"Текущая ставка: {rates.get('rate', 0)}%",
                      with_miniapp_button=True)

    elif text == "/start":
        send_message(
            chat_id,
            "Привет! /rate — посмотреть текущую ставку,\n"
            "/setrate <значение> — задать вручную,\n"
            "или открой шкалу ниже, чтобы задать ставку слайдером.",
            with_miniapp_button=True,
        )

    return changed


def main():
    if not BOT_TOKEN:
        print("[error] BOT_TOKEN is not set", file=sys.stderr)
        sys.exit(1)

    rates = load_json(RATES_PATH, {"rate": 0, "updated_at": None})
    offset_state = load_json(OFFSET_PATH, {"offset": 0})
    offset = offset_state.get("offset", 0)

    resp = requests.get(
        f"{API_URL}/getUpdates",
        params={"offset": offset, "timeout": 0},
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()

    if not result.get("ok"):
        print(f"[error] getUpdates failed: {result}", file=sys.stderr)
        sys.exit(1)

    updates = result.get("result", [])
    rates_changed = False
    max_update_id = offset - 1

    for update in updates:
        max_update_id = max(max_update_id, update["update_id"])
        if handle_update(update, rates):
            rates_changed = True

    new_offset = max_update_id + 1
    if new_offset != offset:
        save_json(OFFSET_PATH, {"offset": new_offset})

    if rates_changed:
        save_json(RATES_PATH, rates)

    print(f"Processed {len(updates)} update(s). rates_changed={rates_changed}")


if __name__ == "__main__":
    main()
