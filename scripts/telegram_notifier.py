import os
import requests
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class TelegramNotifier:
    """Simple Telegram Bot API helper using requests.

    Expects `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in environment or
    passed explicitly to the constructor.
    """

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        if not self.token or not self.chat_id:
            raise ValueError('TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set')
        self.base = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str, parse_mode: str = 'HTML') -> dict:
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True,
        }
        r = requests.post(f"{self.base}/sendMessage", json=payload, timeout=15)
        r.raise_for_status()
        return r.json()

    def send_photo(self, photo_url: str, caption: Optional[str] = None) -> dict:
        payload = {
            'chat_id': self.chat_id,
            'photo': photo_url,
            'caption': caption or '',
            'parse_mode': 'HTML'
        }
        r = requests.post(f"{self.base}/sendPhoto", json=payload, timeout=15)
        r.raise_for_status()
        return r.json()

    def format_application_message(self, job: dict, result: dict) -> str:
        # job: {'title','company','url','source','posted_date'}
        # result: {'status','method','notes'}
        title = job.get('title', '—')
        company = job.get('company', '—')
        url = job.get('url', '')
        status = result.get('status', '—')
        method = result.get('method', '—')
        notes = result.get('notes', '')
        lines = [f"<b>{title}</b>", f"Empresa: {company}", f"Estado: {status}", f"Método: {method}"]
        if notes:
            lines.append(f"Notas: {notes}")
        if url:
            lines.append(f"URL: {url}")
        return "\n".join(lines)


if __name__ == '__main__':
    print('Telegram notifier helper. To test set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env or environment.')
