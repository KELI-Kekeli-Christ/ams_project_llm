# Tests - Robot Hotel

Structure de tests pour le projet Robot Hotel comprenant les tests unitaires, d'intégration et de sécurité.

## Structure des Tests

```
tests/
├── unit/              # Tests unitaires
│   ├── services/      # Tests des services (chat, whisper, face_detection, etc.)
│   ├── api/           # Tests des endpoints API
│   └── admin/         # Tests de l'interface admin
├── integration/       # Tests d'intégration
│   ├── api/           # Tests d'intégration API
│   └── workflows/     # Tests de workflows complets
├── security/          # Tests de sécurité
│   ├── authentication/    # Tests d'authentification
│   ├── authorization/     # Tests d'autorisation
│   └── data_protection/   # Tests de protection des données
├── fixtures/          # Données de test (images, audio, etc.)
└── utils/             # Utilitaires de test (helpers, mocks)
```

## Types de Tests

### Tests Unitaires
Testent les composants individuels isolément :
- Services (chat, transcription, reconnaissance faciale)
- Fonctions utilitaires
- Logique métier

**Exemple :** `tests/unit/services/test_chat.py`

### Tests d'Intégration
Testent l'interaction entre plusieurs composants :
- Flux API complets
- Workflows utilisateur (de la reconnaissance à la réservation)
- Intégration avec bases de données

**Exemple :** `tests/integration/workflows/test_reservation_workflow.py`

### Tests de Sécurité
Testent les aspects de sécurité :
- Authentification et autorisation
- Protection des données personnelles (RGPD)
- Validation des inputs
- Injection SQL, XSS, etc.

**Exemple :** `tests/security/data_protection/test_face_data_protection.py`

## Exécution des Tests

### Tous les tests
```bash
pytest tests/
```

### Tests unitaires uniquement
```bash
pytest tests/unit/
```

### Tests d'intégration uniquement
```bash
pytest tests/integration/
```

### Tests de sécurité uniquement
```bash
pytest tests/security/
```

### Avec couverture de code
```bash
pytest --cov=robot_hotel --cov-report=html tests/
```

## Fixtures

Les fichiers de test (images, audio, etc.) sont stockés dans `tests/fixtures/`.

## Utilitaires de Test

Les helpers et mocks communs sont dans `tests/utils/`.

## Configuration

Un fichier `pytest.ini` ou `conftest.py` peut être créé à la racine pour configurer pytest.

