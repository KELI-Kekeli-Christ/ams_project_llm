"""
Configuration pytest pour les tests Robot Hotel
"""
import pytest
import sys
import os
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "robot_hotel"))

@pytest.fixture
def test_data_dir():
    """Répertoire des données de test"""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def sample_image_path(test_data_dir):
    """Chemin vers une image de test"""
    image_path = test_data_dir / "test_face.jpg"
    if image_path.exists():
        return str(image_path)
    return None

@pytest.fixture
def sample_audio_path(test_data_dir):
    """Chemin vers un fichier audio de test"""
    audio_path = test_data_dir / "test_audio.wav"
    if audio_path.exists():
        return str(audio_path)
    return None

@pytest.fixture
def mock_flask_app():
    """Mock de l'application Flask pour les tests"""
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    return app

@pytest.fixture
def client(mock_flask_app):
    """Client de test Flask"""
    return mock_flask_app.test_client()

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock des variables d'environnement pour les tests"""
    monkeypatch.setenv("API_BASE_URL", "http://localhost:5000")
    monkeypatch.setenv("FASTAPI_BASE_URL", "http://localhost:8000")

