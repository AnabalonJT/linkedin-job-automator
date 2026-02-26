#!/usr/bin/env python3
"""
Script para sincronizar trabajos nuevos de jobs_found.json a new_jobs_to_apply.json

Este script:
1. Lee jobs_found.json
2. Filtra trabajos con is_new: true
3. Guarda en new_jobs_to_apply.json
"""

import json
from pathlib import Path


def sync_new_jobs():
    """Sincroniza trabajos nuevos de jobs_found.json a new_jobs_to_apply.json"""
    
    # Archivos
    jobs_found_file = Path("data/logs/jobs_found.json")
    new_jobs_file = Path("data/logs/new_jobs_to_apply.json")
    
    # Verificar que jobs_found.json existe
    if not jobs_found_file.exists():
        print("❌ Error: jobs_found.json no existe")
        return
    
    # Leer jobs_found.json
    with open(jobs_found_file, 'r', encoding='utf-8') as f:
        all_jobs = json.load(f)
    
    print(f"📂 Cargados {len(all_jobs)} trabajos de jobs_found.json")
    
    # Filtrar trabajos con is_new: true
    new_jobs = [job for job in all_jobs if job.get('is_new') == True]
    
    print(f"🆕 Encontrados {len(new_jobs)} trabajos con is_new: true")
    
    # Guardar en new_jobs_to_apply.json
    new_jobs_file.parent.mkdir(parents=True, exist_ok=True)
    with open(new_jobs_file, 'w', encoding='utf-8') as f:
        json.dump(new_jobs, f, indent=2, ensure_ascii=False)
    
    print(f"✅ new_jobs_to_apply.json actualizado con {len(new_jobs)} trabajos")
    
    # Mostrar resumen
    if new_jobs:
        print("\n📋 Trabajos sincronizados:")
        for i, job in enumerate(new_jobs, 1):
            easy_apply = "✓" if job.get('has_easy_apply') else "✗"
            print(f"  {i}. {job['title']} - {job['company']} (Easy Apply: {easy_apply})")
    else:
        print("\n⚠️  No hay trabajos nuevos para sincronizar")


if __name__ == "__main__":
    print("🔄 Sincronizando trabajos nuevos...")
    print("=" * 60)
    sync_new_jobs()
    print("=" * 60)
    print("✨ Sincronización completada")
