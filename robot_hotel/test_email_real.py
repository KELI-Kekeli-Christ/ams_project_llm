#!/usr/bin/env python3
"""
Test email avec une vraie adresse pour vérifier la livraison
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.email import send_reservation_confirmation

# Test avec email real - modifier cette valeur pour un vrai compte
TEST_EMAIL = "christlearn834@gmail.com"

test_user = {
    "nom": "Test-Robot",
    "prenom": "Hôtel",
    "type_chambre": "Chambre Standard",
    "date_arrivee": "2024-01-15",
    "date_depart": "2024-01-20",
    "email": TEST_EMAIL
}

print(f"\n🧪 Test d'email vers {TEST_EMAIL}")
print("="*60)

result = send_reservation_confirmation(test_user)

print(f"\n{'✅' if result.get('success') else '❌'} Résultat: {result}")
print("\nVérifiez dans votre Gmail (christlearn834@gmail.com):")
print("- Dossier 'Inbox' pour l'email de confirmation")
print("- Dossier 'Spam' si pas trouvé en inbox")
print("="*60)
