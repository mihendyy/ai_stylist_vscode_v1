# ai_stylist_vscode_v1

Telegram stylist bot that orchestrates multiple AI services and deploys via Yandex Cloud.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Populate the `.env` file with the required API keys (Telegram bot token, AITunnel key). The values stay local because `.env` is ignored by git.

## Project layout

- `app/api/` — FastAPI application (`/health` endpoint ready for probes).
- `app/bot_service/` — Telegram bot wrapper and voice processor.
- `app/config/` — environment-aware settings loader.
- `app/catalog/`, `app/imgproc/`, `app/imggen/`, `app/recommender/` — building blocks for the outfit pipeline.
- `app/workers/` — Celery tasks for asynchronous generation and maintenance.
- `app/db/` — SQLAlchemy models for users, garments and feedback.
- `tests/` — pytest suite (currently contains API health check).

## Running FastAPI locally

```bash
uvicorn app.api.main:app --reload
```

After launch try the health endpoint: `curl http://127.0.0.1:8000/health`.

## Running the Telegram bot

```bash
python -m app.bot_service.runner
```

The bot relies on the tokens stored in `.env`, saves media to `data/media/`, and persists wardrobe metadata in `data/app.db` (SQLite).

User flow inside Telegram:

1. `/start` — бот рассказывает о возможностях и просит селфи в полный рост.
2. После селфи отправляйте вещи по одной фотографии; бот попросит выбрать категорию каждой (верх/низ/обувь/аксессуар/верхняя одежда).
3. Напишите «готово», когда все вещи загружены, затем опишите любимые стили или референсы.
4. Когда готовы, спросите «что надеть сегодня?» — бот вызовет AITunnel (модель gpt-5-mini для текста и gemini-2.5-flash-image для визуализации) и пришлёт рекомендацию вместе с изображением.

## Connectivity checks

Чтобы убедиться, что AITunnel доступен и отвечает, выполните:

```bash
python scripts/check_integrations.py
```

Скрипт выполнит проверку текстового и визуального API и выведет статус (требуется корректный AITunnel ключ).
