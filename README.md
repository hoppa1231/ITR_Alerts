# ITR_Alerts - Snipe-IT license expiry notifier

Simple Python bot that checks Snipe-IT licenses and notifies mapped users via Telegram.

## Quick start

1. Install deps:
   ```
   pip install -r requirements.txt
   ```
2. Create `.env` from `.env.example` and fill values.
3. Create `user_map.json` from `user_map.example.json`.
4. Run once:
   ```
   python main.py --once
   ```

## How it works

- Reads licenses from Snipe-IT `/licenses` and seat assignments from `/licenses/{id}/seats`.
- Filters by expiration date (default: <= 14 days).
- Sends one Telegram message per chat with all relevant licenses.

## Scheduling

Two options:

- Built-in scheduler:
  ```
  RUN_MODE=schedule
  SCHEDULE_TIME=12:00
  python main.py --schedule
  ```
- Or run `python main.py --once` daily via Task Scheduler/cron.

## User mapping

`user_map.json` ties Snipe-IT users to Telegram chat IDs:

```
{
  "users": [
    { "snipeit_user_id": 123, "telegram_chat_id": 123456789 },
    { "snipeit_email": "user@example.com", "telegram_chat_id": 987654321 }
  ],
  "default_chat_ids": []
}
```

Match order:
1) `snipeit_user_id`
2) `snipeit_username`
3) `snipeit_email`

If no user matches and `default_chat_ids` is set, the message goes there.

## Registration with admin approval

Enable user self-registration via Telegram:

1) Set in `.env`:
   ```
   ENABLE_REGISTRATION=true
   ADMIN_CHAT_IDS=123456789,987654321
   RUN_MODE=schedule
   POLL_SECONDS=30
   ```
2) Run:
   ```
   python main.py --schedule
   ```

Users can send `/start` or `/register <email|username|id>`.
Admins approve with:
```
/approve <chat_id> email user@x
/approve <chat_id> username user
/approve <chat_id> id 123
```
To reject:
```
/deny <chat_id>
```

Admins can also request an immediate scan:
```
/scan_now
```

## Important env vars

- `SNIPEIT_BASE_URL` - base URL of your Snipe-IT instance (without `/api/v1` is OK)
- `SNIPEIT_API_TOKEN` - API token
- `TELEGRAM_BOT_TOKEN` - bot token from BotFather
- `NOTIFY_DAYS` - number of days before expiration (default 14)
- `NOTIFY_ONLY_ON_DAY` - set to `14` to send only exactly 14 days before
- `INCLUDE_EXPIRED` - include already expired licenses
- `DRY_RUN` - log messages without sending
- `FALLBACK_CHAT_ID` - optional fallback chat ID if no user match
