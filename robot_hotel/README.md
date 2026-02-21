# 🤖 Système Robot Hôtel Pepper

## ✨ Nouvelles fonctionnalités

### 💬 Bouton "Chatter avec Pepper"

Le robot Pepper affiche maintenant un bouton **"Chatter avec Pepper"** sur sa tablette. Quand l'utilisateur clique dessus, un QR code apparaît permettant d'accéder à une interface de chat web.

#### Fonctionnement :
1. **Sur la tablette** : Bouton orange "💬 Chatter avec Pepper"
2. **Au clic** : Affichage d'un QR code
3. **Scan du QR code** : Redirection vers `http://[IP_ROBOT]:5000/chat`
4. **Interface web** : Chat en temps réel avec l'IA de Pepper

#### URLs disponibles :
- **Interface de chat** : `http://localhost:5000/chat` (pour développement)
- **API de chat** : `POST http://localhost:5000/chat` avec `{"message": "votre message"}`

#### Micro (message vocal / appel) :
- **Sur le même ordinateur** : ouvrez `http://localhost:5000/chat` — le micro est autorisé par le navigateur.
- **Depuis le téléphone** (ex. `http://192.168.x.x:5000`) : le navigateur exige HTTPS pour le micro. Options :
  - Utiliser le **chat texte** (pas de micro).
  - Ou exposer en HTTPS avec un tunnel : `npx localtunnel --port 5000` puis ouvrir l’URL `https://xxx.loca.lt` sur le téléphone.

#### Exemple d'utilisation :
```bash
# Démarrer le serveur
python main.py

# Tester l'interface de chat
curl http://localhost:5000/chat

# Tester l'API de chat
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bonjour Pepper !"}'
```

## 🚀 Démarrage rapide</content>
<parameter name="filePath">/home/christ/Downloads/Telegram Desktop/M1/M1 Avignon universite/Ams projet/ams/robot_hotel/README.md