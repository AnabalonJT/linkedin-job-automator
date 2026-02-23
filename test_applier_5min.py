#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test del LinkedIn Applier por 5 minutos
"""

import sys
import subprocess
import time
import signal
import os

def run_applier_with_timeout():
    """Ejecuta el applier por máximo 5 minutos"""
    
    print("="*80)
    print("INICIANDO TEST DEL LINKEDIN APPLIER (5 minutos máximo)")
    print("="*80)
    print()
    
    # Comando para ejecutar
    cmd = [sys.executable, "scripts/linkedin_applier.py"]
    
    # Iniciar proceso
    print(f"Ejecutando: {' '.join(cmd)}")
    print(f"Timeout: 5 minutos (300 segundos)")
    print()
    
    try:
        # Ejecutar con timeout de 5 minutos
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        start_time = time.time()
        timeout = 300  # 5 minutos
        
        # Leer output en tiempo real
        while True:
            # Verificar timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"\n⏱️  TIMEOUT alcanzado ({timeout}s). Terminando proceso...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                break
            
            # Leer línea de output
            line = process.stdout.readline()
            if line:
                print(line, end='')
            
            # Verificar si el proceso terminó
            if process.poll() is not None:
                # Leer cualquier output restante
                for line in process.stdout:
                    print(line, end='')
                break
            
            time.sleep(0.1)
        
        print()
        print("="*80)
        print("TEST COMPLETADO")
        print("="*80)
        print()
        
        # Mostrar ubicación del log
        import glob
        logs = sorted(glob.glob("data/logs/execution_*.log"), reverse=True)
        if logs:
            latest_log = logs[0]
            print(f"📄 Log más reciente: {latest_log}")
            print()
            print("Para ver el log completo:")
            print(f"  cat {latest_log}")
            print()
            print("Para ver últimas 50 líneas:")
            print(f"  tail -n 50 {latest_log}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrumpido por usuario (Ctrl+C)")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_applier_with_timeout()
