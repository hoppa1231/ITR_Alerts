import datetime as dt
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from .clients import TelegramClient

from .parsing import load_user_map_full, save_user_map


def _user_keyboard() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "/start"}],
            [{"text": "/register email user@example.com"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def _admin_keyboard() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "/approve <chat_id> email user@example.com"}],
            [{"text": "/deny <chat_id>"}],
            [{"text": "/scan_now"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def _find_pending(pending: List[Dict[str, Any]], chat_id: str) -> Optional[Dict[str, Any]]:
    for item in pending:
        if str(item.get("telegram_chat_id")) == str(chat_id):
            return item
    return None


def _find_user(users: List[Dict[str, Any]], chat_id: str) -> Optional[Dict[str, Any]]:
    for item in users:
        if str(item.get("telegram_chat_id")) == str(chat_id):
            return item
    return None


def _parse_command(text: str) -> Tuple[str, List[str]]:
    parts = text.strip().split()
    if not parts:
        return "", []
    return parts[0].lower(), parts[1:]


def _build_user_entry(
    chat_id: str,
    meta: Dict[str, Any],
    mapping: Dict[str, Any],
) -> Dict[str, Any]:
    entry: Dict[str, Any] = {"telegram_chat_id": str(chat_id)}
    for key in ("snipeit_user_id", "snipeit_username", "snipeit_email"):
        if key in mapping and mapping[key]:
            entry[key] = mapping[key]
    for key in ("first_name", "last_name", "username"):
        if key in meta and meta[key]:
            entry[f"telegram_{key}"] = meta[key]
    return entry


def _collect_mapping_from_pending(pending_entry: Dict[str, Any]) -> Dict[str, Any]:
    mapping: Dict[str, Any] = {}
    if pending_entry.get("requested_email"):
        mapping["snipeit_email"] = pending_entry.get("requested_email")
    if pending_entry.get("requested_username"):
        mapping["snipeit_username"] = pending_entry.get("requested_username")
    if pending_entry.get("requested_user_id"):
        mapping["snipeit_user_id"] = pending_entry.get("requested_user_id")
    return mapping


def _parse_approve_args(args: List[str]) -> Tuple[Optional[str], Dict[str, Any]]:
    if not args:
        return None, {}
    chat_id = args[0]
    mapping: Dict[str, Any] = {}
    if len(args) >= 3:
        key = args[1].lower()
        value = args[2]
        if key == "email":
            mapping["snipeit_email"] = value
        elif key == "username":
            mapping["snipeit_username"] = value
        elif key in {"id", "user_id"}:
            mapping["snipeit_user_id"] = value
    return chat_id, mapping


def process_updates(
    telegram: TelegramClient,
    user_map_path: str,
    state_path: str,
    admin_chat_ids: List[str],
    long_poll_seconds: int,
) -> bool:
    state = _load_state(state_path)
    offset = state.get("telegram_offset")
    response = telegram.get_updates(offset=offset, timeout_seconds=long_poll_seconds)
    if not response.get("ok"):
        return False
    updates = response.get("result") or []
    if not updates:
        return False

    max_update_id: Optional[int] = None
    scan_requested = False

    data = load_user_map_full(user_map_path)
    users = data.get("users", [])
    pending = data.get("pending_users", [])

    for update in updates:
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            if max_update_id is None or update_id > max_update_id:
                max_update_id = update_id
        message = update.get("message") or {}
        text = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if not chat_id:
            continue
        command, args = _parse_command(text)

        if chat_id in admin_chat_ids and command in {"/approve", "/deny", "/scan_now"}:
            if command == "/scan_now":
                telegram.send_message(
                    chat_id, "Запрос на сканирование. Отправка уведомлений...", reply_markup=_admin_keyboard()
                )
                scan_requested = True
            elif command == "/deny":
                target_id = args[0] if args else None
                if not target_id:
                    telegram.send_message(
                        chat_id,
                        "Usage: /deny <chat_id>",
                        reply_markup=_admin_keyboard(),
                    )
                else:
                    pending_entry = _find_pending(pending, target_id)
                    if pending_entry:
                        pending.remove(pending_entry)
                        save_user_map(user_map_path, data)
                        telegram.send_message(chat_id, f"Denied {target_id}")
                    else:
                        telegram.send_message(chat_id, f"Not found: {target_id}")
            else:
                target_id, mapping = _parse_approve_args(args)
                if not target_id:
                    telegram.send_message(
                        chat_id,
                        "Используйте: /approve <chat_id> [email|username|id <value>]",
                        reply_markup=_admin_keyboard(),
                    )
                else:
                    pending_entry = _find_pending(pending, target_id)
                    if not pending_entry:
                        telegram.send_message(chat_id, f"Не найден: {target_id}")
                    else:
                        if not mapping:
                            mapping = _collect_mapping_from_pending(pending_entry)
                        if not mapping:
                            telegram.send_message(
                                chat_id,
                                "Предоставьте параметры: /approve <chat_id> email <x> or username <x> or id <x>",
                                reply_markup=_admin_keyboard(),
                            )
                        else:
                            user_entry = _build_user_entry(
                                target_id, pending_entry, mapping
                            )
                            users.append(user_entry)
                            pending.remove(pending_entry)
                            save_user_map(user_map_path, data)
                            telegram.send_message(chat_id, f"Одобрено {target_id}")
                            telegram.send_message(
                                target_id,
                                "Регистрация одобрена. Вы будете получать уведомления.",
                                reply_markup=_user_keyboard(),
                            )
        else:
            if command not in {"/start", "/register"}:
                continue
            if _find_user(users, chat_id):
                telegram.send_message(
                    chat_id, "Уже зарегистрирован.", reply_markup=_user_keyboard()
                )
                continue
            if _find_pending(pending, chat_id):
                telegram.send_message(
                    chat_id, "Ожидает подтверждения.", reply_markup=_user_keyboard()
                )
                continue

            requested_email = None
            requested_username = None
            requested_user_id = None
            if args:
                value = args[0]
                if "@" in value:
                    requested_email = value
                elif value.isdigit():
                    requested_user_id = value
                else:
                    requested_username = value

            pending_entry = {
                "telegram_chat_id": chat_id,
                "first_name": chat.get("first_name"),
                "last_name": chat.get("last_name"),
                "username": chat.get("username"),
                "requested_email": requested_email,
                "requested_username": requested_username,
                "requested_user_id": requested_user_id,
                "requested_at": dt.datetime.utcnow().isoformat() + "Z",
                "admin_notified_at": None,
            }
            pending.append(pending_entry)
            save_user_map(user_map_path, data)
            telegram.send_message(
                chat_id,
                "Регистрация запрошена. Ожидание подтверждения администратора.",
                reply_markup=_user_keyboard(),
            )
            for admin_id in admin_chat_ids:
                telegram.send_message(
                    admin_id,
                    f"Ожидающий пользователь: {chat_id}. Одобрить с помощью /approve {chat_id} email <x> or username <x> or id <x>",
                    reply_markup=_admin_keyboard(),
                )
            pending_entry["admin_notified_at"] = dt.datetime.utcnow().isoformat() + "Z"

    if max_update_id is not None:
        state["telegram_offset"] = max_update_id + 1
        _save_state(state_path, state)
    return scan_requested


def _load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError:
            return {}


def _save_state(path: str, state: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=True, indent=2)
