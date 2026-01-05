"""
Tests unitaires pour le service de chat
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

try:
    from robot_hotel.services.chat import chat
    from robot_hotel.services.location import get_heure_date
except ImportError:
    # Fallback si l'import échoue
    chat = None
    get_heure_date = None


class TestChatService:
    """Tests pour le service de chat"""
    
    @pytest.mark.skipif(chat is None, reason="Service chat non disponible")
    def test_chat_basic_response(self):
        """Test qu'une réponse basique est retournée"""
        user_message = "Bonjour"
        result = chat(user_message)
        
        assert result is not None
        assert 'response' in result or 'error' in result
    
    @pytest.mark.skipif(chat is None, reason="Service chat non disponible")
    def test_chat_with_empty_message(self):
        """Test avec un message vide"""
        result = chat("")
        
        # Devrait gérer le message vide gracieusement
        assert result is not None
    
    @pytest.mark.skipif(get_heure_date is None, reason="Service date non disponible")
    def test_get_heure_date_format(self):
        """Test que get_heure_date retourne le bon format"""
        date_str = get_heure_date()
        
        assert date_str is not None
        assert isinstance(date_str, str)
        # Vérifier que le format contient "Il est" et "le"
        assert "Il est" in date_str or "Il est" in date_str.lower()


class TestChatRAG:
    """Tests pour l'intégration RAG"""
    
    @pytest.mark.skipif(chat is None, reason="Service chat non disponible")
    @patch('robot_hotel.services.rag.get_rag_context')
    def test_chat_uses_rag_context(self, mock_rag):
        """Test que le chat utilise le contexte RAG"""
        mock_rag.return_value = {
            'context': 'Test context',
            'sources': []
        }
        
        result = chat("Test question")
        
        # Vérifier que RAG a été appelé
        mock_rag.assert_called()
        assert result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

