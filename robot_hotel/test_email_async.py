#!/usr/bin/env python3
"""
Test script pour valider l'envoi asynchrone d'emails
Utilise le nouveau logging pour tracer l'exécution
"""
import sys
import time
import threading
from pathlib import Path

# Ajouter le repo root au path
sys.path.insert(0, str(Path(__file__).parent))

from services.email import send_reservation_confirmation

def test_sync_email():
    """Test l'envoi synchrone d'email pour validation rapide"""
    print("\n" + "="*60)
    print("TEST ENVOI EMAIL SYNCHRONE")
    print("="*60)
    
    test_user = {
        "nom": "Dupont",
        "prenom": "Jean",
        "type_chambre": "Chambre Standard",
        "date_arrivee": "2024-01-15",
        "date_depart": "2024-01-20",
        "email": "test@example.com"
    }
    
    print(f"\n📧 Envoi en cours...")
    print(f"Client email: {test_user['email']}")
    print(f"Manager email: christlearn834@gmail.com")
    
    start = time.time()
    result = send_reservation_confirmation(test_user)
    elapsed = time.time() - start
    
    print(f"\n⏱️  Temps écoulé: {elapsed:.1f}s")
    print(f"Résultat: {result}")
    
    if result.get("success"):
        print("\n✅ TEST RÉUSSI: Email(s) envoyé(s) avec succès")
    else:
        print(f"\n❌ TEST ÉCHOUÉ: {result.get('error')}")
    
    return result.get("success", False)


def test_async_email():
    """Test l'envoi asynchrone d'email en arrière-plan"""
    print("\n" + "="*60)
    print("TEST ENVOI EMAIL ASYNCHRONE (ARRIÈRE-PLAN)")
    print("="*60)
    
    test_user = {
        "nom": "Martin",
        "prenom": "Sophie",
        "type_chambre": "Chambre Deluxe",
        "date_arrivee": "2024-02-01",
        "date_depart": "2024-02-05",
        "email": "sophie.martin@example.com"
    }
    
    print(f"\n📧 Lancement en arrière-plan...")
    print(f"Client email: {test_user['email']}")
    
    start = time.time()
    
    # Simuler le même modèle que finalize_reservation
    def _send_email_async(payload):
        try:
            print(f"[ASYNC] Début envoi en arrière-plan...")
            result = send_reservation_confirmation(payload)
            print(f"[ASYNC] ✅ Résultat: {result}")
        except Exception as e:
            print(f"[ASYNC] ❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    
    thread = threading.Thread(target=_send_email_async, args=(test_user.copy(),), daemon=True)
    thread.start()
    
    print(f"[MAIN] Thread lancé (retour immédiat)")
    elapsed_immediate = time.time() - start
    print(f"[MAIN] Temps avant retour: {elapsed_immediate:.3f}s (devrait être < 0.1s)")
    
    if elapsed_immediate < 0.1:
        print("✅ Retour immédiat confirmé (non-bloquant)")
    else:
        print("⚠️ Retour trop lent (peut être bloquant)")
    
    print(f"[MAIN] Attente de 3s pour que le thread se termine...")
    time.sleep(3)
    
    print(f"\n✅ TEST ASYNCHRONE TERMINÉ")


if __name__ == "__main__":
    print("\n🧪 TESTS D'ENVOI EMAIL\n")
    
    # Test sync d'abord
    sync_ok = test_sync_email()
    
    # Test async
    test_async_email()
    
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)
    if sync_ok:
        print("✅ Envoi synchrone: OK")
        print("📧 Les emails devraient arriver dans quelques secondes")
        print("🔍 Vérifiez:")
        print("  1. Gmail inbox pour christlearn834@gmail.com (manager)")
        print("  2. Gmail inbox pour test@example.com (client - check spam)")
    else:
        print("❌ Envoi synchrone: ÉCHEC - vérifiez la configuration SMTP")
    print("="*60 + "\n")
