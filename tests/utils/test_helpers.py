"""
Helpers pour les tests
"""
import io
import os
from pathlib import Path


def create_test_image(width=100, height=100):
    """Créer une image de test en mémoire"""
    from PIL import Image
    img = Image.new('RGB', (width, height), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes


def create_test_audio(duration=1.0, sample_rate=16000):
    """Créer un fichier audio de test en mémoire"""
    import numpy as np
    from scipy.io.wavfile import write as write_wav
    import io
    
    # Générer un signal sinusoïdal simple
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    
    audio_bytes = io.BytesIO()
    write_wav(audio_bytes, sample_rate, audio_data)
    audio_bytes.seek(0)
    
    return audio_bytes


def get_fixture_path(filename):
    """Retourner le chemin complet vers un fichier fixture"""
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    return fixtures_dir / filename


def mock_api_response(status_code=200, json_data=None):
    """Créer un mock de réponse API"""
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data
        
        def json(self):
            return self._json_data or {}
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    return MockResponse(status_code, json_data)

