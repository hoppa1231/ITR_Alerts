import datetime as dt
from typing import Any, Dict, List, Optional

from .clients import SnipeItClient
from .parsing import extract_assigned_user, extract_expiration, match_chat_ids, pick_license_name


def build_notifications(
    licenses: List[Dict[str, Any]],
    client: SnipeItClient,
    user_map: List[Dict[str, Any]],
    fallback_chat_ids: List[str],
    notify_days: int,
    include_expired: bool,
    notify_only_on_day: Optional[int],
) -> Dict[str, List[Dict[str, Any]]]:
    today = dt.date.today()
    notifications: Dict[str, List[Dict[str, Any]]] = {}

    for license_row in licenses:
        exp_date = extract_expiration(license_row)
        if not exp_date:
            continue

        days_remaining = (exp_date - today).days
        if notify_only_on_day is not None and days_remaining != notify_only_on_day:
            continue
        if days_remaining < 0 and not include_expired:
            continue
        if days_remaining > notify_days:
            continue

        license_id = license_row.get("id")
        license_name = pick_license_name(license_row)

        assigned_chat_ids: List[str] = []
        if license_id is not None:
            seats = client.list_license_seats(int(license_id))
            for seat in seats:
                seat_user = extract_assigned_user(seat)
                assigned_chat_ids.extend(match_chat_ids(seat_user, user_map))

        if not assigned_chat_ids and fallback_chat_ids:
            assigned_chat_ids = fallback_chat_ids[:]

        for chat_id in dict.fromkeys(assigned_chat_ids):
            notifications.setdefault(chat_id, []).append(
                {
                    "license_id": license_id,
                    "license_name": license_name,
                    "expires": exp_date,
                    "days_remaining": days_remaining,
                }
            )

    return notifications


def build_license_items(
    licenses: List[Dict[str, Any]],
    notify_days: int,
    include_expired: bool,
    notify_only_on_day: Optional[int],
) -> List[Dict[str, Any]]:
    today = dt.date.today()
    items: List[Dict[str, Any]] = []
    for license_row in licenses:
        exp_date = extract_expiration(license_row)
        if not exp_date:
            continue

        days_remaining = (exp_date - today).days
        if notify_only_on_day is not None and days_remaining != notify_only_on_day:
            continue
        if days_remaining < 0 and not include_expired:
            continue
        if days_remaining > notify_days:
            continue

        license_id = license_row.get("id")
        license_name = pick_license_name(license_row)
        items.append(
            {
                "license_id": license_id,
                "license_name": license_name,
                "expires": exp_date,
                "days_remaining": days_remaining,
            }
        )
    return items


def _format_days_label(days_remaining: int) -> str:
    if days_remaining < 0:
        return f"{abs(days_remaining)} дней просрочки"
    if days_remaining == 0:
        return "истекает сегодня"
    if days_remaining == 1:
        return "1 осталось дней"
    return f"{days_remaining} осталось дней"


def build_message(items: List[Dict[str, Any]], notify_days: int) -> str:
    lines = [f"Напоминание об истечении срока действия лицензии (<= {notify_days} дней):"]
    for item in sorted(items, key=lambda x: x["expires"]):
        date_str = item["expires"].strftime("%Y-%m-%d")
        label = _format_days_label(item["days_remaining"])
        license_id = item.get("license_id")
        if license_id is None:
            lines.append(f"- {item['license_name']} - {date_str} ({label})")
        else:
            lines.append(
                f"- {item['license_name']} (id {license_id}) - {date_str} ({label})"
            )
    return "\n".join(lines)
