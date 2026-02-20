#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask server check and start utilities for pepper_test module.
"""

import os
import sys
import time
import socket
import requests
import subprocess


# Configuration de l'API Flask (pour enregistrement, transcription et chat)
# Le serveur Flask est bindé sur 0.0.0.0 mais on doit se connecter via l'IP locale
import os

def get_flask_url():
    """Obtient l'URL du serveur Flask pour les connexions clientes"""
    # Pour les connexions depuis le robot/tablette, on utilise localhost
    # car le serveur Flask et le robot sont sur le même réseau ou le robot accède au serveur
    flask_host = os.environ.get("FLASK_HOST", "localhost")
    flask_port = os.environ.get("FLASK_PORT", "5000")
    # Python 2.7 compatible
    return "http://%s:%s" % (flask_host, flask_port)

API_CONFIG = {
    "base_url": get_flask_url(),  # URL de base de l'API Flask
    "timeout": 60,                        # Timeout pour les requêtes (secondes)
    "record_timeout": 120,                # Timeout spécifique pour l'enregistrement
}


def check_flask_server():
    """
    Vérifie si le serveur Flask est en cours d'exécution
    
    Returns:
        bool: True si Flask est accessible, False sinon
    """
    # Méthode 1: Vérifier si le port est ouvert (plus rapide et fiable)
    try:
        host = API_CONFIG["base_url"].replace("http://", "").replace("https://", "").split(":")[0]
        port = int(API_CONFIG["base_url"].split(":")[-1].split("/")[0]) if ":" in API_CONFIG["base_url"] else 5000
        
        # Créer un socket et essayer de se connecter
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # Timeout très court pour éviter le blocage
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            # Le port est ouvert, Flask est probablement en cours d'exécution
            # Maintenant vérifier avec une requête HTTP rapide
            try:
                response = requests.get(
                    "{}/".format(API_CONFIG["base_url"]),
                    timeout=1  # Timeout très court
                )
                if response.status_code == 200:
                    print("Flask detecte et accessible")
                    return True
            except:
                # Même si la requête HTTP échoue, le port est ouvert donc Flask tourne probablement
                print("Port Flask ouvert (port {}), serveur probablement en cours d'execution".format(port))
                return True
        else:
            return False
    except socket.timeout:
        return False
    except Exception:
        # Si la vérification de port échoue, essayer avec une requête HTTP simple
        pass
    
    # Méthode 2: Fallback avec requête HTTP (si la vérification de port échoue)
    try:
        response = requests.get(
            "{}/".format(API_CONFIG["base_url"]),
            timeout=1  # Timeout très court pour éviter le blocage
        )
        if response.status_code == 200:
            print("Flask detecte via requete HTTP")
            return True
    except requests.exceptions.ConnectionError:
        # Connexion refusée = Flask n'est pas démarré
        return False
    except requests.exceptions.Timeout:
        # Timeout = Flask ne répond pas assez vite
        return False
    except Exception:
        # Autre erreur
        return False
    
    return False


def start_flask_server_background():
    """
    Démarre le serveur Flask en arrière-plan dans un processus séparé
    
    Returns:
        bool: True si le démarrage a réussi, False sinon
    """
    try:
        # Obtenir le chemin du répertoire robot_hotel
        script_dir = os.path.dirname(os.path.abspath(__file__))
        robot_hotel_dir = os.path.dirname(script_dir)
        flask_main = os.path.join(robot_hotel_dir, "main.py")
        
        if not os.path.exists(flask_main):
            print("Fichier Flask non trouve: {}".format(flask_main))
            return False
        
        print("🚀 Démarrage du serveur Flask en arrière-plan...")
        
        # Préparer les arguments pour le démarrage
        if sys.platform == "win32":
            # Windows: utiliser CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                [sys.executable, flask_main],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=robot_hotel_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:
            # Linux/Unix: utiliser nohup et setsid pour isoler le processus
            process = subprocess.Popen(
                ["nohup", sys.executable, flask_main],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=robot_hotel_dir,
                preexec_fn=os.setsid  # Créer un nouveau groupe de processus pour isoler Flask
            )
        
        # Attendre un peu pour que Flask démarre
        print("Attente du demarrage de Flask...")
        for i in range(10):  # Attendre jusqu'à 10 secondes
            time.sleep(1)
            if check_flask_server():
                print("Serveur Flask demarre avec succes (PID: {})".format(process.pid))
                print("   Le serveur continuera de tourner même après l'arrêt du robot.")
                return True
        
        print("Flask semble avoir demarre mais n'est pas encore accessible")
        return False
    except Exception as e:
        print("Erreur lors du demarrage de Flask: {}".format(e))
        import traceback
        traceback.print_exc()
        return False


def post_file_with_retries(url, files, attempts=3, timeout=None):
    """
    Post a file with simple retry logic on timeout/connection errors.
    Returns the `requests.Response` or `None` if all attempts fail.
    """
    import time
    if timeout is None:
        timeout = API_CONFIG.get("timeout", 60)

    for i in range(attempts):
        try:
            return requests.post(url, files=files, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if i < attempts - 1:
                backoff = 1 + i * 2
                time.sleep(backoff)
                continue
            return None
    return None

