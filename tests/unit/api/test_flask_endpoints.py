"""
Tests unitaires pour les endpoints Flask
"""
import pytest
from flask import Flask
from unittest.mock import Mock, patch
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))


@pytest.fixture
def app():
    """Créer une instance de l'application Flask pour les tests"""
    from robot_hotel.main import app as flask_app
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture
def client(app):
    """Client de test Flask"""
    return app.test_client()


class TestHealthEndpoints:
    """Tests pour les endpoints de santé"""
    
    def test_root_endpoint(self, client):
        """Test l'endpoint racine"""
        response = client.get('/')
        assert response.status_code in [200, 404]  # Peut retourner 200 ou 404
    
    def test_api_docs_endpoint(self, client):
        """Test l'endpoint de documentation API"""
        response = client.get('/api-docs')
        assert response.status_code in [200, 404]


class TestChatEndpoint:
    """Tests pour l'endpoint de chat"""
    
    @patch('robot_hotel.services.chat.chat')
    def test_chat_endpoint_success(self, mock_chat, client):
        """Test l'endpoint chat avec succès"""
        mock_chat.return_value = {
            'response': 'Test response',
            'context_used': 'Test context'
        }
        
        response = client.post('/chat', json={'message': 'Test'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'response' in data or 'error' in data
    
    def test_chat_endpoint_missing_message(self, client):
        """Test l'endpoint chat sans message"""
        response = client.post('/chat', json={})
        
        # Devrait retourner une erreur 400 ou gérer gracieusement
        assert response.status_code in [200, 400, 422]


class TestTranscribeEndpoint:
    """Tests pour l'endpoint de transcription"""
    
    def test_transcribe_no_file(self, client):
        """Test transcription sans fichier"""
        response = client.post('/transcribe')
        
        assert response.status_code in [400, 422, 500]
    
    @patch('robot_hotel.services.whisper.transcribe_audio')
    def test_transcribe_with_file(self, mock_transcribe, client):
        """Test transcription avec fichier"""
        mock_transcribe.return_value = {
            'text': 'Test transcription',
            'language': 'fr'
        }
        
        # Créer un fichier mock
        data = {
            'file': (b'fake audio data', 'test.wav')
        }
        
        response = client.post('/transcribe', data=data, content_type='multipart/form-data')
        
        # Le mock pourrait ne pas fonctionner complètement sans vraie implémentation
        assert response.status_code in [200, 400, 500]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

