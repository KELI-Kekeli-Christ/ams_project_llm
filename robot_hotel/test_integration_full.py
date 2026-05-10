#!/usr/bin/env python3
"""
Test d'intégration: simule le flux complet de réservation
1. Démarrer conversation
2. Répondre aux 5 questions
3. Simuler email form + confirmation
"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.reservation_conversation import (
    start_conversation,
    process_answer,
    finalize_reservation
)

def test_full_flow():
    print("\n" + "="*70)
    print("🧪 TEST INTÉGRATION: FLUX COMPLET DE RÉSERVATION")
    print("="*70)
    
    # 1️⃣ Start conversation
    print("\n[1️⃣] Démarrage de la conversation...")
    conv = start_conversation()
    session_id = conv["session_id"]
    print(f"✅ Session créée: {session_id}")
    print(f"   Première question: {conv['question']}")
    
    # 2️⃣ Répondre aux 5 questions
    answers = [
        ("Dupont", "nom"),
        ("Jean", "prenom"),
        ("Chambre Standard", "type_chambre"),
        ("5 juin", "date_arrivee"),
        ("10 juin", "date_depart")
    ]
    
    for i, (text, field) in enumerate(answers, 1):
        print(f"\n[{i}️⃣+1] Réponse pour {field}: '{text}'")
        result = process_answer(session_id, text)
        print(f"   Status: {result['status']}")
        if "question" in result:
            print(f"   Prochaine question: {result['question']}")
        if "collected_data" in result:
            print(f"   Données collectées: {json.dumps(result['collected_data'], indent=6, ensure_ascii=False)}")
    
    # 3️⃣ Finalize avec email
    print(f"\n[📧] Finalisation avec email...")
    client_email = "test_integration@example.com"
    print(f"   Email client: {client_email}")
    
    start = time.time()
    result = finalize_reservation(session_id, client_email)
    elapsed = time.time() - start
    
    print(f"   Réponse en: {elapsed:.2f}s")
    print(f"   Résultat: {result}")
    
    if elapsed < 1.0:
        print(f"   ✅ Retour rapide (non-bloquant)")
    else:
        print(f"   ⚠️ Retour lent ({elapsed:.1f}s) - peut être bloquant")
    
    print("\n" + "="*70)
    print("✅ TEST TERMINÉ - Attendez 3s pour que les emails s'envoient...")
    print("="*70)
    time.sleep(3)

if __name__ == "__main__":
    test_full_flow()
