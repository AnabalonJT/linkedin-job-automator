# Telegram integration

Steps to enable Telegram notifications for this project:

1. Create a bot with BotFather and obtain the `BOT_TOKEN`.
2. Obtain a chat id (your user id or a group id) — easiest: send a message to your bot and query `getUpdates`, or use tools like @userinfobot.
3. In the project `.env` file add:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=987654321
```

4. Install dependencies if not present:

```bash
pip install -r requirements.txt
```

5. Test the notifier from the repo root:

```bash
python -c "from scripts.telegram_notifier import TelegramNotifier; TelegramNotifier().send_message('Test desde linkedin-job-automator')"
```

6. Integration points:
- Call `TelegramNotifier().send_message(...)` from `scripts/linkedin_applier.py` after each application attempt.
- Use `format_application_message(job, result)` to format the message.

7. n8n: the workflow at `n8n/workflows/linkedin_automation.json` is a starter skeleton. Replace placeholders with real credentials and use the `HTTP Request` node to call Telegram (or run the Python scripts as shown).
