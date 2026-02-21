#!/usr/bin/env python3
"""
Script de test pour vérifier que toutes les routes Flask fonctionnent
"""
import requests
import time
import subprocess
import signal
import os

def test_routes():
    print("🧪 Test des routes Flask")
    print("=" * 50)

    # Démarrer le serveur en arrière-plan
    print("1. Démarrage du serveur...")
    server_process = subprocess.Popen(
        ['bash', '-c', 'source env/bin/activate && python main.py'],
        cwd='/home/christ/Downloads/Telegram Desktop/M1/M1 Avignon universite/Ams projet/ams/robot_hotel',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Attendre que le serveur démarre
    time.sleep(5)
    
    # Vérifier si le serveur fonctionne
    if server_process.poll() is not None:
        stdout, stderr = server_process.communicate()
        print(f"❌ Le serveur s'est arrêté prématurément")
        print(f"STDOUT: {stdout.decode()}")
        print(f"STDERR: {stderr.decode()}")
        return False

    base_url = "http://localhost:5000"

    routes_to_test = [
        ("/", "Page d'accueil"),
        ("/chat", "Page de chat"),
        ("/validate?session_id=test", "Page de validation"),
        ("/reservation_success", "Page de succès"),
    ]

    success_count = 0

    print("\n2. Test des routes GET...")
    for route, description in routes_to_test:
        try:
            response = requests.get(f"{base_url}{route}", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {description}: {response.status_code}")
                success_count += 1
            else:
                print(f"   ❌ {description}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {description}: Erreur - {e}")

    print("\n3. Test de l'API chat...")
    try:
        response = requests.post(
            f"{base_url}/chat",
            json={"message": "Bonjour"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if "response" in data and "session_id" in data:
                print("   ✅ API Chat: Fonctionnelle")
                success_count += 1
            else:
                print("   ❌ API Chat: Réponse invalide")
        else:
            print(f"   ❌ API Chat: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API Chat: Erreur - {e}")

    # Arrêter le serveur
    print("\n4. Arrêt du serveur...")
    server_process.terminate()
    server_process.wait(timeout=5)

    print("\n" + "=" * 50)
    print(f"📊 Résultats: {success_count}/{len(routes_to_test) + 1} tests réussis")

    if success_count == len(routes_to_test) + 1:
        print("🎉 Toutes les routes fonctionnent correctement !")
        return True
    else:
        print("⚠️ Certaines routes ont des problèmes.")
        return False

if __name__ == "__main__":
    test_routes()