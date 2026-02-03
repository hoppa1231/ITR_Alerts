# ITR_Alerts — уведомления об истечении лицензий Snipe-IT

Простой Python-бот, который проверяет лицензии в Snipe-IT и отправляет уведомления соответствующим пользователям через Telegram.

---

## Быстрый старт

1. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```
2. Создайте файл `.env` на основе `.env.example` и заполните значения.
3. Создайте `user_map.json` на основе `user_map.example.json`.
4. Запустите один раз:

   ```bash
   python main.py --once
   ```

---

## Как это работает

* Получает список лицензий из Snipe-IT через `/licenses` и назначения лицензий через `/licenses/{id}/seats`.
* Фильтрует лицензии по дате окончания (по умолчанию: ≤ 14 дней).
* Отправляет **одно сообщение в Telegram на каждый чат**, содержащее все релевантные лицензии.

---

## Планировщик

Два варианта запуска:

### Встроенный планировщик

```bash
RUN_MODE=schedule
SCHEDULE_TIME=12:00
python main.py --schedule
```

### Внешний планировщик

Либо запускайте `python main.py --once` ежедневно через **Task Scheduler** (Windows) или **cron** (Linux).

---

## Сопоставление пользователей

Файл `user_map.json` связывает пользователей Snipe-IT с chat ID Telegram:

```json
{
  "users": [
    { "snipeit_user_id": 123, "telegram_chat_id": 123456789 },
    { "snipeit_email": "user@example.com", "telegram_chat_id": 987654321 }
  ],
  "default_chat_ids": []
}
```

### Порядок сопоставления:

1. `snipeit_user_id`
2. `snipeit_username`
3. `snipeit_email`

Если пользователь не найден и указан `default_chat_ids`, уведомление отправляется туда.

---

## Регистрация пользователей с подтверждением администратором

Можно включить саморегистрацию пользователей через Telegram.

### 1) Укажите в `.env`:

```ini
ENABLE_REGISTRATION=true
ADMIN_CHAT_IDS=123456789,987654321
RUN_MODE=schedule
POLL_SECONDS=30
```

### 2) Запустите:

```bash
python main.py --schedule
```

### Команды пользователей:

* `/start`
* `/register <email|username|id>`

### Команды администраторов для подтверждения:

```text
/approve <chat_id> email user@x
/approve <chat_id> username user
/approve <chat_id> id 123
```

### Для отклонения:

```text
/deny <chat_id>
```

### Дополнительно

Администраторы могут вручную запустить проверку лицензий:

```text
/scan_now
```

---

## Важные переменные окружения

* `SNIPEIT_BASE_URL` — базовый URL экземпляра Snipe-IT (указывать `/api/v1` не обязательно)
* `SNIPEIT_API_TOKEN` — API-токен Snipe-IT
* `TELEGRAM_BOT_TOKEN` — токен Telegram-бота от BotFather
* `NOTIFY_DAYS` — количество дней до окончания лицензии (по умолчанию 14)
* `NOTIFY_ONLY_ON_DAY` — например, `14`, чтобы уведомлять **только ровно за 14 дней**
* `INCLUDE_EXPIRED` — включать уже истёкшие лицензии
* `DRY_RUN` — только логирование, без отправки сообщений
* `FALLBACK_CHAT_ID` — резервный chat ID, если пользователь не найден


---

## Docker

Build and run:

```bash
docker compose up -d --build
```

Stop:

```bash
docker compose down
```
