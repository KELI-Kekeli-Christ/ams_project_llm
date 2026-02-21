#!/usr/bin/env python3
"""
Script de test pour vérifier le flux de réservation via chatbot
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.chat import (
    init_reservation_db,
    handle_reservation_flow,
    is_reservation_request,
    get_reservation_session
)

def test_chatbot_reservation_flow():
    print("🤖 Test du flux de réservation via chatbot")
    print("=" * 60)

    # Initialiser la DB
    init_reservation_db()

    # Test de détection d'intention de réservation
    print("1. Test de détection d'intention de réservation...")
    test_messages = [
        "Je voudrais réserver une chambre",
        "Pouvez-vous me faire une réservation ?",
        "J'aimerais réserver pour ce weekend",
        "Bonjour, je cherche une chambre",
        "Au revoir"
    ]

    for msg in test_messages:
        is_reservation = is_reservation_request(msg)
        status = "✅ Réservation détectée" if is_reservation else "❌ Pas une réservation"
        print(f"   '{msg}' -> {status}")

    print("\n2. Test du flux de conversation de réservation...")

    # Simuler une conversation complète
    session_id = "test_chat_flow_456"
    conversation_steps = [
        ("Je voudrais réserver une chambre", "start"),
        ("Dupont", "ask_nom"),
        ("Jean", "ask_prenom"),
        ("jean.dupont@email.com", "ask_email"),
        ("double", "ask_room_type"),
        ("25/12/2025 - 30/12/2025", "ask_dates"),  # Format correct
        ("oui", "confirm")
    ]

    current_step = "start"
    user_data = {}

    for user_input, expected_step in conversation_steps:
        print(f"\n   Étape actuelle: {current_step}")
        print(f"   Input utilisateur: '{user_input}'")

        response, new_step, data = handle_reservation_flow(
            session_id, user_input, current_step, user_data
        )

        print(f"   Réponse: {response[:100]}...")
        print(f"   Nouvelle étape: {new_step}")
        print(f"   Données collectées: {len(data)} champs")

        current_step = new_step
        user_data = data

        if new_step == "complete":
            break

    # Vérifier que la session a été créée
    print("\n3. Vérification de la session créée...")
    retrieved_data, retrieved_step = get_reservation_session(session_id)

    if retrieved_data and retrieved_step == "complete":
        print("✅ Session de réservation créée avec succès")
        print(f"   Nom complet: {retrieved_data.get('prenom')} {retrieved_data.get('nom')}")
        print(f"   Email: {retrieved_data.get('email')}")
        print(f"   Chambre: {retrieved_data.get('type_chambre')}")
        print(f"   Dates: {retrieved_data.get('date_arrivee')} - {retrieved_data.get('date_depart')}")
    else:
        print("❌ Échec de la création de la session")
        return False

    print("\n" + "=" * 60)
    print("🎉 Test du flux chatbot réussi !")
    return True

if __name__ == "__main__":
    test_chatbot_reservation_flow()