import logging
import os
import time

from .clients import SnipeItClient, TelegramClient
from .config import Config
from .notifications import build_license_items, build_message, build_notifications
from .parsing import load_user_map
from .registration import process_updates


def run_once(config: Config) -> int:
    client = SnipeItClient(config.base_url, config.api_token, config.timeout_seconds)
    telegram = TelegramClient(config.telegram_token, config.timeout_seconds, config.dry_run)

    user_map, fallback = load_user_map(config.user_map_path)
    if config.fallback_chat_id:
        fallback.append(str(config.fallback_chat_id))
        fallback = list(dict.fromkeys(fallback))

    licenses = client.list_licenses(page_size=config.page_size)
    logging.info("Loaded %s licenses", len(licenses))

    notify_only_on_day = (
        int(config.notify_only_on_day) if config.notify_only_on_day else None
    )

    items = build_license_items(
        licenses=licenses,
        notify_days=config.notify_days,
        include_expired=config.include_expired,
        notify_only_on_day=notify_only_on_day,
    )

    if not items:
        logging.info("No notifications to send")
        return 0

    recipients = [str(entry.get("telegram_chat_id")) for entry in user_map if entry.get("telegram_chat_id")]
    recipients.extend(fallback)
    recipients.extend(config.admin_chat_ids)
    recipients = list(dict.fromkeys([r for r in recipients if r]))

    for chat_id in recipients:
        message = build_message(items, config.notify_days)
        telegram.send_message(chat_id, message)
        logging.info("Sent %s items to chat %s", len(items), chat_id)

    return 0


def run_schedule(config: Config) -> int:
    try:
        import schedule  # type: ignore
    except ImportError as exc:
        raise RuntimeError("schedule package not installed. pip install schedule") from exc

    schedule.every().day.at(config.schedule_time).do(run_once, config)
    if config.enable_registration:
        schedule.every(config.poll_seconds).seconds.do(_poll_updates_and_scan, config)
    logging.info("Scheduler started: daily at %s", config.schedule_time)
    while True:
        schedule.run_pending()
        time.sleep(1)


def _poll_updates_and_scan(config: Config) -> None:
    telegram = TelegramClient(
        config.telegram_token, config.timeout_seconds, config.dry_run
    )
    scan_requested = process_updates(
        telegram=telegram,
        user_map_path=config.user_map_path,
        state_path=config.state_path,
        admin_chat_ids=config.admin_chat_ids,
        long_poll_seconds=config.poll_seconds,
    )
    if scan_requested:
        run_once(config)


def setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )
