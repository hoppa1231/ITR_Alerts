import os


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class Config:
    def __init__(self) -> None:
        self.base_url = os.getenv("SNIPEIT_BASE_URL", "").strip()
        self.api_token = os.getenv("SNIPEIT_API_TOKEN", "").strip()
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.user_map_path = os.getenv("USER_CHAT_MAP_PATH", "user_map.json").strip()
        self.notify_days = int(os.getenv("NOTIFY_DAYS", "14"))
        self.notify_only_on_day = os.getenv("NOTIFY_ONLY_ON_DAY", "").strip()
        self.include_expired = _to_bool(os.getenv("INCLUDE_EXPIRED", "false"))
        self.run_mode = os.getenv("RUN_MODE", "once").strip().lower()
        self.schedule_time = os.getenv("SCHEDULE_TIME", "12:00").strip()
        self.page_size = int(os.getenv("PAGE_SIZE", "100"))
        self.timeout_seconds = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.dry_run = _to_bool(os.getenv("DRY_RUN", "false"))
        self.fallback_chat_id = os.getenv("FALLBACK_CHAT_ID", "").strip()
        self.enable_registration = _to_bool(os.getenv("ENABLE_REGISTRATION", "false"))
        self.admin_chat_ids = [
            item.strip()
            for item in os.getenv("ADMIN_CHAT_IDS", "").split(",")
            if item.strip()
        ]
        self.poll_seconds = int(os.getenv("POLL_SECONDS", "30"))
        self.state_path = os.getenv("STATE_PATH", "state.json").strip()

    def normalize(self) -> None:
        if not self.base_url:
            return
        url = self.base_url.rstrip("/")
        if url.endswith("/api/v1"):
            self.base_url = url
        elif url.endswith("/api"):
            self.base_url = f"{url}/v1"
        else:
            self.base_url = f"{url}/api/v1"

    def validate(self) -> None:
        missing = []
        if not self.base_url:
            missing.append("SNIPEIT_BASE_URL")
        if not self.api_token:
            missing.append("SNIPEIT_API_TOKEN")
        if not self.telegram_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if missing:
            raise ValueError("Missing required env vars: " + ", ".join(missing))

        if self.notify_only_on_day:
            try:
                int(self.notify_only_on_day)
            except ValueError as exc:
                raise ValueError("NOTIFY_ONLY_ON_DAY must be integer") from exc

        if self.enable_registration and not self.admin_chat_ids:
            raise ValueError("ENABLE_REGISTRATION requires ADMIN_CHAT_IDS")
