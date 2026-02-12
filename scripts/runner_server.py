from flask import Flask, jsonify, request
import subprocess
import threading
import shlex
import os
import sys
from datetime import datetime
from pathlib import Path

# Agregar scripts a path para imports
scripts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

app = Flask(__name__)

# Setup logging
log_file = '/app/data/logs/runner_server.log'
os.makedirs(os.path.dirname(log_file), exist_ok=True)

def log_message(msg):
    """Log message to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    sys.stdout.flush()
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(full_msg + "\n")
    except Exception as e:
        print(f"Error writing to log: {e}")


def run_command(cmd):
    try:
        log_message(f"Ejecutando comando: {cmd}")
        # Run command and capture output
        completed = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='/app')
        log_message(f"Comando completado: returncode={completed.returncode}")
        if completed.stdout:
            log_message(f"STDOUT: {completed.stdout[:500]}")  # Limitar a 500 chars
        if completed.stderr:
            log_message(f"STDERR: {completed.stderr[:500]}")
        return {
            'returncode': completed.returncode,
            'stdout': completed.stdout,
            'stderr': completed.stderr
        }
    except Exception as e:
        log_message(f"Error ejecutando comando: {str(e)}")
        return {'returncode': 1, 'stdout': '', 'stderr': str(e)}


@app.route('/run/<name>', methods=['POST', 'GET'])
def run(name):
    log_message(f"Recibido request /run/{name}")
    # Map friendly names to scripts
    mapping = {
        'scraper': 'python scripts/linkedin_scraper.py',
        'applier': 'python scripts/linkedin_applier.py',
        'sync': 'python scripts/google_sheets_manager.py'
    }

    if name not in mapping:
        log_message(f"Error: job desconocido '{name}'")
        return jsonify({'error': 'unknown job'}), 404

    cmd = mapping[name]

    # Optionally run asynchronously if requested
    if request.args.get('async', 'false').lower() in ('1', 'true', 'yes'):
        log_message(f"Iniciando ejecución asincrónica: {cmd}")
        thread = threading.Thread(target=run_command, args=(cmd,))
        thread.start()
        return jsonify({'status': 'started', 'cmd': cmd}), 202

    result = run_command(cmd)
    return jsonify(result)


@app.route('/notify/telegram', methods=['POST', 'GET'])
def notify_telegram():
    """Send a Telegram message with LinkedIn automation statistics.
    
    Reads result files and Google Sheets ID from env to build detailed message.
    """
    log_message("Iniciando /notify/telegram")
    try:
        import json
        from pathlib import Path
        
        # Read configuration
        from utils import Config
        config = Config()
        sheets_id = config.get_env_var('GOOGLE_SHEETS_ID')
        log_message(f"Google Sheets ID: {sheets_id[:20] if sheets_id else 'NO CONFIGURADO'}")
        
        # Read results files
        jobs_found_file = Path('/app/data/logs/jobs_found.json')
        results_file = Path('/app/data/logs/application_results.json')
        
        log_message(f"Buscando jobs_found.json en: {jobs_found_file}")
        log_message(f"Archivo existe: {jobs_found_file.exists()}")
        log_message(f"Buscando application_results.json en: {results_file}")
        log_message(f"Archivo existe: {results_file.exists()}")
        
        jobs_found = []
        results = []
        
        if jobs_found_file.exists():
            with open(jobs_found_file, 'r', encoding='utf-8') as f:
                jobs_found = json.load(f)
            log_message(f"Jobs encontrados: {len(jobs_found)}")
        else:
            log_message("jobs_found.json no encontrado")
        
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            log_message(f"Resultados de postulaciones: {len(results)}")
        else:
            log_message("application_results.json no encontrado")
        
        # Calculate statistics
        total_jobs = len(jobs_found)
        total_attempts = len(results)
        successful = sum(1 for r in results if r.get('status') == 'APPLIED')
        manual = sum(1 for r in results if r.get('status') == 'MANUAL')
        failed = sum(1 for r in results if r.get('status') not in ['APPLIED', 'MANUAL', 'PENDING'])
        
        log_message(f"Estadísticas: {total_jobs} jobs, {total_attempts} intentos, {successful} exitosos, {manual} manuales, {failed} fallidos")
        
        # Build message
        message_lines = [
            "<b>🎯 LinkedIn Job Automator - Ciclo Completado</b>",
            "",
            "<b>📊 Estadísticas:</b>",
            f"  • Trabajos encontrados: <b>{total_jobs}</b>",
            f"  • Intentos de postulación: <b>{total_attempts}</b>",
            f"  • ✅ Exitosas: <b>{successful}</b>",
            f"  • ⚠️ Manuales: <b>{manual}</b>",
            f"  • ❌ Fallidas: <b>{failed}</b>",
            ""
        ]
        
        # Add success rate
        if total_attempts > 0:
            rate = (successful / total_attempts) * 100
            message_lines.append(f"<b>📈 Tasa de automatización: {rate:.1f}%</b>")
            message_lines.append("")
        
        # Add Google Sheets link
        if sheets_id:
            sheets_url = f"https://docs.google.com/spreadsheets/d/{sheets_id}/edit"
            message_lines.append(f"<a href=\"{sheets_url}\">📋 Ver resultados en Google Sheets</a>")
            message_lines.append("")
        
        message_lines.append("✨ Próxima ejecución: Mañana a las 9:00 AM")
        
        message = "\n".join(message_lines)
        log_message(f"Mensaje construido ({len(message)} caracteres)")
        
        # Send via Telegram
        from telegram_notifier import TelegramNotifier
        
        log_message("Intentando enviar mensaje por Telegram...")
        try:
            notifier = TelegramNotifier()
            log_message("TelegramNotifier creado exitosamente")
            resp = notifier.send_message(message)
            log_message(f"Mensaje enviado a Telegram: {resp}")
            return jsonify({'status': 'sent', 'stats': {
                'total_jobs': total_jobs,
                'total_attempts': total_attempts,
                'successful': successful,
                'manual': manual,
                'failed': failed
            }, 'message': 'Telegram message sent successfully'}), 200
        except ValueError as e:
            # Telegram not configured
            log_message(f"Telegram no configurado: {str(e)}")
            return jsonify({'status': 'skipped', 'reason': 'Telegram not configured', 'message': str(e)}), 200
        except Exception as e:
            log_message(f"Error enviando a Telegram: {str(e)}")
            import traceback
            log_message(traceback.format_exc())
            raise
        
    except Exception as e:
        log_message(f"Error en /notify/telegram: {str(e)}")
        import traceback
        log_message(traceback.format_exc())
        # Don't fail the workflow
        return jsonify({'status': 'error', 'message': str(e)}), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    log_message("Health check request")
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()}), 200


if __name__ == '__main__':
    log_message("Iniciando Flask runner server en 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
