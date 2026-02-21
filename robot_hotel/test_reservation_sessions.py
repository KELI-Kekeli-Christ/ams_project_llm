#!/usr/bin/env python3
"""
Script de test pour vérifier la gestion des sessions de réservation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.chat import (
    init_reservation_db,
    save_reservation_session,
    get_reservation_session,
    delete_reservation_session,
    generate_validation_link
)

def test_reservation_sessions():
    print("🧪 Test de la gestion des sessions de réservation")
    print("=" * 60)

    # Initialiser la DB
    print("1. Initialisation de la base de données...")
    init_reservation_db()
    print("✅ Base de données initialisée")

    # Test données de session
    session_id = "test_session_chat_123"
    user_data = {
        "nom": "Dupont",
        "prenom": "Jean",
        "email": "jean.dupont@email.com",
        "type_chambre": "double",
        "date_arrivee": "2025-12-25",
        "date_depart": "2025-12-30"
    }
    current_step = "confirm"

    print("\n2. Test sauvegarde de session...")
    success = save_reservation_session(session_id, user_data, current_step)
    if success:
        print("✅ Session sauvegardée avec succès")
    else:
        print("❌ Échec de la sauvegarde de session")
        return False

    print("\n3. Test récupération de session...")
    retrieved_data, retrieved_step = get_reservation_session(session_id)
    if retrieved_data and retrieved_step == current_step:
        print("✅ Session récupérée avec succès")
        print(f"   Étape: {retrieved_step}")
        print(f"   Nom: {retrieved_data['nom']}")
        print(f"   Email: {retrieved_data['email']}")
    else:
        print("❌ Échec de la récupération de session")
        return False

    print("\n4. Test génération de lien de validation...")
    validation_link = generate_validation_link(session_id)
    print(f"✅ Lien généré: {validation_link}")

    print("\n5. Test suppression de session...")
    delete_reservation_session(session_id)

    # Vérifier que la session a été supprimée
    check_data, check_step = get_reservation_session(session_id)
    if check_data is None and check_step is None:
        print("✅ Session supprimée avec succès")
    else:
        print("❌ Échec de la suppression de session")
        return False

    print("\n" + "=" * 60)
    print("🎉 Tous les tests de session sont passés avec succès !")
    return True

if __name__ == "__main__":
    test_reservation_sessions()