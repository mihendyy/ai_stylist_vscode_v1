# MVP Bot Overview

This package contains a minimal implementation of the AI stylist flow focused on
validating the end-to-end experience:

- `config/settings.py` — loads environment-aware configuration.
- `storage/repository.py` — stores user data as JSON files in `storage/users/`.
- `api/aitunnel_client.py` — asynchronous wrapper around AITunnel OpenAI- and Google-compatible endpoints.
- `imggen/prompt_builder.py` — builds textual prompts for the image generator.
- `imggen/image_gen.py` — communicates with `gemini-2.5-flash-image` through AITunnel.
- `logic.py` — orchestrates preference extraction, outfit planning, and image generation.
- `bot_service/state_machine.py` — finite state machine describing conversation stages.
- `bot_service/voice_processor.py` — sends voice notes to Whisper STT via AITunnel.
- `bot_service/handlers/` — command/message handlers grouped by responsibility.
- `bot_service/bot.py` — wires Aiogram, storage, logic, and handlers together.

The legacy codebase remains untouched; the MVP can be launched via:

```bash
python -m mvp.bot_service.bot
```

Environment variables (or entries in `.env`) should define at least the bot token
and AITunnel credentials.
