# -*- coding: utf-8 -*-
"""
Configuration de l'environnement Choregraphe pour l'import du module qi

Note: Le SDK NAOqi/Choregraphe utilise Python 2.7. Si vous exécutez avec Python 3,
le module qi peut ne pas être disponible. Utilisez Python 2.7 avec Choregraphe
pour une compatibilité complète.
"""
import os
import sys
from config import CHOREGRAPHE_PATH


def setup_choreographe_environment():
    """Configure LD_LIBRARY_PATH et sys.path pour Choregraphe."""
    choregraph_lib_path = os.path.join(CHOREGRAPHE_PATH, "lib")
    if os.path.exists(choregraph_lib_path):
        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        if choregraph_lib_path not in current_ld_path:
            os.environ["LD_LIBRARY_PATH"] = "{}:{}".format(
                choregraph_lib_path,
                current_ld_path
            ) if current_ld_path else choregraph_lib_path
    # Chemins Python : privilégier python2.7 pour Choregraphe (SDK NAOqi)
    choregraph_python_paths = [
        os.path.join(CHOREGRAPHE_PATH, "lib", "python2.7", "site-packages"),
        os.path.join(CHOREGRAPHE_PATH, "lib", "python", "site-packages"),
        os.path.join(CHOREGRAPHE_PATH, "pynaoqi"),
    ]
    for python_path in choregraph_python_paths:
        if os.path.exists(python_path) and python_path not in sys.path:
            sys.path.insert(0, python_path)


# Exécuter au chargement du module
setup_choreographe_environment()
