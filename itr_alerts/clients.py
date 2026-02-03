import logging
from typing import Any, Dict, Iterable, List, Optional

import requests


class SnipeItClient:
    def __init__(self, base_url: str, token: str, timeout_seconds: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )
        self.timeout_seconds = timeout_seconds

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        resp = self.session.get(url, params=params or {}, timeout=self.timeout_seconds)
        resp.raise_for_status()
        return resp.json()

    def get_paginated(self, endpoint: str, page_size: int = 100) -> Iterable[Dict[str, Any]]:
        offset = 0
        while True:
            params = {"limit": page_size, "offset": offset}
            payload = self.get(endpoint, params=params)
            rows = payload.get("rows") or []
            if not isinstance(rows, list):
                rows = []
            for row in rows:
                yield row
            total = payload.get("total")
            if total is None:
                if len(rows) < page_size:
                    break
                offset += page_size
                continue
            if offset + page_size >= int(total):
                break
            offset += page_size

    def list_licenses(self, page_size: int = 100) -> List[Dict[str, Any]]:
        return list(self.get_paginated("/licenses", page_size=page_size))

    def list_license_seats(self, license_id: int, page_size: int = 100) -> List[Dict[str, Any]]:
        return list(self.get_paginated(f"/licenses/{license_id}/seats", page_size=page_size))


class TelegramClient:
    def __init__(self, token: str, timeout_seconds: int = 30, dry_run: bool = False) -> None:
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()
        self.timeout_seconds = timeout_seconds
        self.dry_run = dry_run

    def send_message(self, chat_id: str, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> None:
        if self.dry_run:
            logging.info("DRY_RUN: would send to %s: %s", chat_id, text)
            return
        payload: Dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        resp = self.session.post(
            f"{self.base_url}/sendMessage",
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()

    def get_updates(self, offset: Optional[int], timeout_seconds: int) -> Dict[str, Any]:
        params: Dict[str, Any] = {"timeout": timeout_seconds}
        if offset is not None:
            params["offset"] = offset
        resp = self.session.get(
            f"{self.base_url}/getUpdates", params=params, timeout=timeout_seconds + 5
        )
        resp.raise_for_status()
        return resp.json()
