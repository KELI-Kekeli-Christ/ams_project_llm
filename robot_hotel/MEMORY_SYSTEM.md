# Mémoire Conversationnelle - Pepper Chatbot

## Vue d'ensemble

Le système de mémoire conversationnelle permet à Pepper de se souvenir des échanges précédents avec un utilisateur, créant ainsi une expérience de chat plus naturelle et cohérente.

## Fonctionnement technique

### Stockage des conversations

- **Stockage en mémoire** : Utilise un dictionnaire Python thread-safe
- **Identification des sessions** : Basé sur l'IP client + identifiant unique
- **Durée de vie** : 1 heure d'inactivité avant suppression automatique

### Structure des données

```python
conversations = {
    "session_id": {
        "messages": [
            {"role": "user", "content": "Bonjour", "timestamp": datetime},
            {"role": "assistant", "content": "Bonjour !", "timestamp": datetime},
            # ... autres messages
        ],
        "created_at": datetime,
        "last_activity": datetime
    }
}
```

### Gestion de l'historique

- **Limite par session** : Maximum 10 paires question/réponse
- **Limite par appel API** : 8 messages récents envoyés au modèle
- **Nettoyage automatique** : Suppression des sessions inactives

## Avantages

### Pour l'utilisateur
- **Continuité** : Pepper se souvient des préférences et informations précédentes
- **Contexte** : Pas besoin de répéter les informations déjà données
- **Personnalisation** : Réponses adaptées à l'historique de la conversation

### Pour le système
- **Efficacité** : Moins de répétitions dans les réponses
- **Précision** : Contexte plus riche pour de meilleures réponses
- **Expérience** : Chat plus naturel et engageant

## Exemple de conversation

```
Utilisateur : Bonjour, je m'appelle Jean Dupont
Pepper : Bonjour Jean ! Enchanté de vous accueillir.

Utilisateur : Je voudrais réserver une chambre pour demain
Pepper : Bien sûr Jean, pour quelle date exactement ?

Utilisateur : Quel est mon nom déjà ?
Pepper : Vous êtes Jean Dupont, bien sûr !
```

## Configuration

### Paramètres modifiables

```python
MAX_CONVERSATION_LENGTH = 10  # Nombre max de paires Q/R
CONVERSATION_TIMEOUT = 3600   # Timeout en secondes (1h)
```

### Limites du modèle

- **Llama-3.1-8B** : Contexte maximum ~4096 tokens
- **Sécurité** : Limitation à 8 messages récents pour éviter dépassement
- **Performance** : Historique optimisé pour rapidité

## Tests

### Script de test automatique

```bash
python test_memory.py
```

### Test manuel

```bash
# Message 1
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Je m'\''appelle Alice"}'

# Message 2 (même session)
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Quel est mon nom ?"}'
```

## Sécurité et confidentialité

- **Anonymisation** : Pas de stockage des données personnelles
- **Expiration** : Suppression automatique après inactivité
- **Thread-safe** : Accès concurrent sécurisé
- **Limites** : Protection contre les abus de mémoire

## Améliorations futures

- **Persistance** : Stockage en base de données
- **Sessions nommées** : Authentification utilisateur
- **Résumé intelligent** : Condensation de longues conversations
- **Multi-modalité** : Mémoire pour images/audio

## Dépannage

### Problèmes courants

1. **Mémoire perdue** : Vérifier le timeout de session
2. **Limite dépassée** : Réduire `MAX_CONVERSATION_LENGTH`
3. **Performance lente** : Vérifier la taille de l'historique

### Debug

Activez les logs dans `services/chat.py` pour diagnostiquer :

```python
print(f"Session {session_id}: {len(conversation_history)} messages")
```