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


class TelegramNotifierWithAccumulation(TelegramNotifier):
    """
    Extended Telegram notifier with result accumulation and consolidated summary.
    
    Accumulates application results during execution and sends a single
    consolidated notification at the end with statistics and manual review items.
    """
    
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        super().__init__(token, chat_id)
        self.results = []
        self.start_time = None
    
    def accumulate_result(self, job: dict, result: dict) -> None:
        """
        Accumulate a single application result.
        
        Args:
            job: Job data (title, company, url, etc.)
            result: Application result (status, cv_used, error, etc.)
        """
        if self.start_time is None:
            import datetime
            self.start_time = datetime.datetime.now()
        
        self.results.append({
            'job': job,
            'result': result
        })
    
    def send_summary(self) -> dict:
        """
        Send a single consolidated notification with all accumulated results.
        
        Returns:
            Response from Telegram API or error dict
        """
        if not self.results:
            return {'error': 'No results to send'}
        
        import datetime
        
        # Calculate statistics
        total = len(self.results)
        successful = sum(1 for r in self.results if r['result'].get('status') == 'APPLIED')
        manual = sum(1 for r in self.results if r['result'].get('status') == 'MANUAL')
        uncertain = sum(1 for r in self.results if r['result'].get('status') == 'INSEGURO')
        unavailable = sum(1 for r in self.results if r['result'].get('status') == 'NO_DISPONIBLE')
        errors = sum(1 for r in self.results if r['result'].get('status') == 'ERROR')
        
        # Calculate AI statistics
        total_questions = sum(len(r['result'].get('questions_answered', [])) for r in self.results)
        avg_confidence = 0.0
        if total_questions > 0:
            confidences = []
            for r in self.results:
                for qa in r['result'].get('questions_answered', []):
                    if 'confidence' in qa:
                        confidences.append(qa['confidence'])
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
        
        automation_rate = (successful / total * 100) if total > 0 else 0
        
        # Build message
        lines = [
            "<b>📊 Resumen de Postulaciones LinkedIn</b>",
            "",
            f"<b>Total procesados:</b> {total}",
            f"✅ Exitosos: {successful}",
            f"⚠️ Requieren revisión manual: {manual + uncertain}",
            f"❌ No disponibles: {unavailable}",
            f"🔴 Errores: {errors}",
            "",
            "<b>Estadísticas de IA:</b>",
            f"Preguntas respondidas: {total_questions}",
            f"Tasa de automatización: {automation_rate:.1f}%",
            f"Confianza promedio: {avg_confidence:.2f}" if avg_confidence > 0 else "Confianza promedio: N/A",
        ]
        
        # Add manual review items
        manual_items = [r for r in self.results if r['result'].get('status') in ['MANUAL', 'INSEGURO']]
        if manual_items:
            lines.append("")
            lines.append("<b>⚠️ Requieren atención manual:</b>")
            for item in manual_items[:5]:  # Limit to 5 items
                job = item['job']
                result = item['result']
                status = result.get('status', 'UNKNOWN')
                reason = result.get('error', 'Sin razón especificada')
                lines.append(f"• {job.get('title', 'Sin título')} - {job.get('company', 'Sin empresa')}")
                lines.append(f"  Estado: {status} - {reason}")
            
            if len(manual_items) > 5:
                lines.append(f"  ... y {len(manual_items) - 5} más")
        
        # Add execution time
        if self.start_time:
            end_time = datetime.datetime.now()
            duration = end_time - self.start_time
            minutes = int(duration.total_seconds() / 60)
            seconds = int(duration.total_seconds() % 60)
            lines.append("")
            lines.append(f"⏱️ Tiempo de ejecución: {minutes}m {seconds}s")
        
        message = "\n".join(lines)
        
        try:
            return self.send_message(message)
        except Exception as e:
            return {'error': str(e)}


if __name__ == '__main__':
    print('Telegram notifier helper. To test set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env or environment.')
