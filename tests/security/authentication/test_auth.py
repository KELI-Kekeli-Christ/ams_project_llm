"""
Tests d'authentification
"""
import pytest


class TestAuthentication:
    """Tests pour l'authentification"""
    
    def test_valid_credentials(self):
        """Test avec des identifiants valides"""
        pytest.skip("À implémenter quand authentification sera ajoutée")
    
    def test_invalid_credentials(self):
        """Test avec des identifiants invalides"""
        pytest.skip("À implémenter")
    
    def test_token_expiration(self):
        """Test expiration des tokens JWT"""
        pytest.skip("À implémenter")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

