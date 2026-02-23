#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de extracción de descripción y clasificación IA
"""

import os
import sys
from pathlib import Path

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

# Configurar DEBUG para ver logs detallados
os.environ['DEBUG'] = 'True'

# Agregar scripts al path
sys.path.insert(0, 'scripts')

from ia_classifier import AIClassifier
from openrouter_client import OpenRouterClient

def test_ia_classification():
    """Prueba la clasificación de IA con diferentes descripciones"""
    
    print("\n" + "="*80)
    print("TEST 1: Clasificación con descripción LIMPIA (sin metadata)")
    print("="*80)
    
    # Descripción limpia (sin header de LinkedIn)
    clean_description = """
We are seeking a highly technical Full Stack Engineer to join our team.

About the Role:
- Design and develop scalable web applications
- Work with React, Node.js, and PostgreSQL
- Collaborate with cross-functional teams
- Write clean, maintainable code

Requirements:
- 5+ years of experience with JavaScript/TypeScript
- Strong knowledge of React and Node.js
- Experience with SQL databases
- Excellent problem-solving skills

What We Offer:
- Competitive salary in USD
- 100% remote work
- Health insurance
- Professional development opportunities
"""
    
    classifier = AIClassifier(confidence_threshold=0.85)
    
    result = classifier.classify_job(
        job_title="Full Stack Engineer",
        job_description=clean_description,
        job_requirements="React, Node.js, PostgreSQL, 5+ years experience"
    )
    
    print(f"\n✅ RESULTADO:")
    print(f"   job_type: {result.get('job_type')}")
    print(f"   match_percentage: {result.get('match_percentage')}%")
    print(f"   confidence: {result.get('confidence'):.2f}")
    print(f"   recommended_cv: {result.get('recommended_cv')}")
    print(f"   reasoning: {result.get('reasoning', '')[:200]}")
    
    # Verificar si la confianza es razonable
    if result.get('confidence', 0) < 0.5:
        print(f"\n⚠️  PROBLEMA: Confianza muy baja ({result.get('confidence'):.2f}) para un trabajo obvio de software")
    else:
        print(f"\n✅ Confianza OK: {result.get('confidence'):.2f}")
    
    print("\n" + "="*80)
    print("TEST 2: Clasificación con descripción SUCIA (con metadata de LinkedIn)")
    print("="*80)
    
    # Descripción con metadata (como se estaba extrayendo antes)
    dirty_description = """
Kajae
Full Stack Engineer
América Latina  · hace 1 día · 96 solicitudes
Promocionado por técnico de selección · Evaluando solicitudes de forma activa
Mira una comparación con los otros 96 candidatos

We are seeking a highly technical Full Stack Engineer to join our team.

About the Role:
- Design and develop scalable web applications
"""
    
    result2 = classifier.classify_job(
        job_title="Full Stack Engineer",
        job_description=dirty_description,
        job_requirements="React, Node.js, PostgreSQL"
    )
    
    print(f"\n✅ RESULTADO:")
    print(f"   job_type: {result2.get('job_type')}")
    print(f"   match_percentage: {result2.get('match_percentage')}%")
    print(f"   confidence: {result2.get('confidence'):.2f}")
    print(f"   recommended_cv: {result2.get('recommended_cv')}")
    
    if result2.get('confidence', 0) < 0.5:
        print(f"\n⚠️  PROBLEMA: La metadata de LinkedIn está afectando la clasificación")
    
    print("\n" + "="*80)
    print("TEST 3: Verificar CV Context")
    print("="*80)
    
    cv_context = classifier.get_current_cv_context()
    print(f"\nCV Context cargado: {len(cv_context)} caracteres")
    print(f"Primeros 300 chars:\n{cv_context[:300]}")
    
    if len(cv_context) < 500:
        print(f"\n⚠️  PROBLEMA: CV Context muy corto ({len(cv_context)} chars)")
    else:
        print(f"\n✅ CV Context OK: {len(cv_context)} chars")

if __name__ == "__main__":
    try:
        test_ia_classification()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
