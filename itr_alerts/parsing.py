import datetime as dt
import json
import os
from typing import Any, Dict, List, Optional, Tuple


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
]


def load_user_map(path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    resolved = _resolve_user_map_path(path)
    if not os.path.exists(resolved):
        data = {"users": [], "default_chat_ids": [], "pending_users": []}
        save_user_map(resolved, data)
        return [], []
    with open(resolved, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        users = data
        fallback = []
    else:
        users = data.get("users", [])
        fallback = data.get("default_chat_ids", []) or []
    if not isinstance(users, list):
        raise ValueError("User map must be a list or have 'users' list")
    fallback_ids = [str(item) for item in fallback if str(item).strip()]
    return users, fallback_ids


def _resolve_user_map_path(path: str) -> str:
    if os.path.isdir(path):
        return os.path.join(path, "user_map.json")
    return path


def load_user_map_full(path: str) -> Dict[str, Any]:
    resolved = _resolve_user_map_path(path)
    if not os.path.exists(resolved):
        return {"users": [], "default_chat_ids": [], "pending_users": []}
    with open(resolved, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return {"users": data, "default_chat_ids": [], "pending_users": []}
    if "users" not in data:
        data["users"] = []
    if "default_chat_ids" not in data:
        data["default_chat_ids"] = []
    if "pending_users" not in data:
        data["pending_users"] = []
    return data


def save_user_map(path: str, data: Dict[str, Any]) -> None:
    resolved = _resolve_user_map_path(path)
    os.makedirs(os.path.dirname(resolved) or ".", exist_ok=True)
    with open(resolved, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=True, indent=2)


def parse_date(value: Any) -> Optional[dt.date]:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("datetime", "date", "formatted", "value"):
            if key in value:
                value = value.get(key)
                break
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None

    cleaned = raw.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(cleaned)
        return parsed.date()
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            parsed = dt.datetime.strptime(raw, fmt)
            return parsed.date()
        except ValueError:
            continue
    return None


def pick_license_name(license_row: Dict[str, Any]) -> str:
    for key in ("name", "license_name", "product", "product_key", "serial"):
        value = license_row.get(key)
        if value:
            return str(value)
    return f"license-{license_row.get('id', 'unknown')}"


def extract_expiration(license_row: Dict[str, Any]) -> Optional[dt.date]:
    for key in (
        "expiration_date",
        "expiry_date",
        "expires",
        "expires_on",
        "expiration",
        "end_date",
        "termination_date",
    ):
        if key in license_row:
            parsed = parse_date(license_row.get(key))
            if parsed:
                return parsed
    return None


def extract_assigned_user(seat_row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for key in ("assigned_user", "assigned_to", "user", "assigned", "assignee"):
        value = seat_row.get(key)
        if isinstance(value, dict):
            return value
    return None


def match_chat_ids(
    seat_user: Optional[Dict[str, Any]],
    user_map: List[Dict[str, Any]],
) -> List[str]:
    if not seat_user:
        return []
    user_id = seat_user.get("id")
    username = seat_user.get("username") or seat_user.get("name")
    email = seat_user.get("email")

    matched: List[str] = []
    for entry in user_map:
        if not isinstance(entry, dict):
            continue
        chat_id = entry.get("telegram_chat_id") or entry.get("chat_id")
        if not chat_id:
            continue
        chat_id = str(chat_id)
        if entry.get("snipeit_user_id") and user_id is not None:
            if str(entry.get("snipeit_user_id")) == str(user_id):
                matched.append(chat_id)
                continue
        if entry.get("snipeit_username") and username:
            if str(entry.get("snipeit_username")).lower() == str(username).lower():
                matched.append(chat_id)
                continue
        if entry.get("snipeit_email") and email:
            if str(entry.get("snipeit_email")).lower() == str(email).lower():
                matched.append(chat_id)
                continue
    return list(dict.fromkeys(matched))
