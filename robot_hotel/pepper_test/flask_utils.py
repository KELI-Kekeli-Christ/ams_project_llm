# -*- coding: utf-8 -*-
"""
Utilitaires Flask : vérification et démarrage du serveur
"""
import os
import sys
import time
import socket
import requests
from config import API_CONFIG


def check_flask_server():
    """Vérifie si le serveur Flask est accessible."""
    try:
        host = API_CONFIG["base_url"].replace("http://", "").replace("https://", "").split(":")[0]
        port = int(API_CONFIG["base_url"].split(":")[-1].split("/")[0]) if ":" in API_CONFIG["base_url"] else 5000
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            try:
                response = requests.get("{}/".format(API_CONFIG["base_url"]), timeout=1)
                if response.status_code == 200:
                    print("Flask detecte et accessible")
                    return True
            except Exception:
                print("Port Flask ouvert (port {}), serveur probablement en cours d'execution".format(port))
                return True
        return False
    except socket.timeout:
        return False
    except Exception:
        pass
    try:
        response = requests.get("{}/".format(API_CONFIG["base_url"]), timeout=1)
        if response.status_code == 200:
            print("Flask detecte via requete HTTP")
            return True
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False
    except Exception:
        pass
    return False


def start_flask_server_background():
    """Démarre le serveur Flask en arrière-plan."""
    import subprocess
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        robot_hotel_dir = os.path.dirname(script_dir)
        flask_main = os.path.join(robot_hotel_dir, "main.py")
        if not os.path.exists(flask_main):
            print("Fichier Flask non trouve: {}".format(flask_main))
            return False
        print("🚀 Démarrage du serveur Flask en arrière-plan...")
        if sys.platform == "win32":
            process = subprocess.Popen(
                [sys.executable, flask_main],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=robot_hotel_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        else:
            process = subprocess.Popen(
                ["nohup", sys.executable, flask_main],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=robot_hotel_dir,
                preexec_fn=os.setsid
            )
        print("Attente du demarrage de Flask...")
        for i in range(10):
            time.sleep(1)
            if check_flask_server():
                print("Serveur Flask demarre avec succes (PID: {})".format(process.pid))
                return True
        print("Flask semble avoir demarre mais n'est pas encore accessible")
        return False
    except Exception as e:
        print("Erreur lors du demarrage de Flask: {}".format(e))
        import traceback
        traceback.print_exc()
        return False


def post_file_with_retries(url, files, attempts=3, timeout=None):
    """Post a file with retry logic. Returns requests.Response or None."""
    if timeout is None:
        timeout = API_CONFIG.get("timeout", 60)
    for i in range(attempts):
        try:
            return requests.post(url, files=files, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if i < attempts - 1:
                time.sleep(1 + i * 2)
                continue
            return None
        except Exception as e:
            print("❌ Erreur post_file: {}".format(e))
            import traceback
            traceback.print_exc()
            return None
    return None
