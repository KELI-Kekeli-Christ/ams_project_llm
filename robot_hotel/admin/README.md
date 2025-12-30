# 🤖 Robot Hotel - Interface d'Administration

Interface Streamlit complète pour gérer et tester toutes les fonctionnalités du système Robot Hotel.

## 📋 Fonctionnalités

### 👤 Gestion des Visages
- Enregistrer de nouvelles personnes dans la base de données
- Lister toutes les personnes enregistrées
- Supprimer des personnes
- Tester la détection et reconnaissance faciale

### 📹 Streaming Vidéo
- Démarrer/arrêter le streaming vidéo en temps réel
- Monitoring des détections en direct
- Support pour webcam locale et robot Pepper
- Actualisation automatique des détections

### 💬 Chat et Audio
- Interface de chat avec le modèle Llama 3
- Transcription de fichiers audio avec Whisper
- Enregistrement audio avec détection de silence
- Récupération de l'heure et date actuelles

### 📅 Réservations
- Création de réservations depuis fichiers audio
- Transcription automatique
- Extraction intelligente des informations (nom, dates, type de chambre)
- Envoi à l'API de réservation

## 🚀 Installation

1. **Installer les dépendances:**
```bash
pip install streamlit requests
```

2. **Vérifier que le serveur Flask est démarré:**
```bash
cd ../  # Revenir au dossier principal
python main.py
```

Le serveur doit être accessible sur `http://localhost:5000`

## 🏃 Démarrage

Dans le dossier `admin`, lancer:

```bash
streamlit run app.py
```

L'interface sera accessible sur `http://localhost:8501`

## 📁 Structure

```
admin/
├── app.py                    # Application principale Streamlit
├── utils.py                  # Module utilitaire pour les appels API
├── pages/
│   ├── 1_👤_Gestion_Visages.py
│   ├── 2_📹_Streaming_Vidéo.py
│   ├── 3_💬_Chat_et_Audio.py
│   └── 4_📅_Réservations.py
└── README.md
```

## ⚙️ Configuration

Par défaut, l'API est configurée pour `http://localhost:5000`. 

Pour changer l'URL de l'API, définir la variable d'environnement:
```bash
export API_BASE_URL=http://votre-serveur:5000
```

Ou modifier directement dans `utils.py`:
```python
API_BASE_URL = "http://votre-serveur:5000"
```

## 📖 Utilisation

1. **Page principale (app.py)**
   - Aperçu général du système
   - Statut de l'API
   - Accès rapide à toutes les fonctionnalités

2. **Gestion des Visages**
   - Onglet "Liste": Voir toutes les personnes enregistrées
   - Onglet "Enregistrer": Ajouter une nouvelle personne
   - Onglet "Supprimer": Retirer une personne
   - Onglet "Tester": Tester la détection sur une image

3. **Streaming Vidéo**
   - Configurer la source vidéo (webcam ou URL)
   - Démarrer le stream
   - Observer les détections en temps réel
   - Voir les personnes reconnues

4. **Chat et Audio**
   - Chat: Discuter avec le chatbot
   - Transcription: Transcrire un fichier audio
   - Enregistrement: Enregistrer depuis le microphone
   - Heure/Lieu: Récupérer l'heure actuelle

5. **Réservations**
   - Télécharger un fichier audio avec demande de réservation
   - Voir la transcription
   - Voir les informations extraites
   - Voir la réponse de l'API

## 🔧 Dépendances

- `streamlit` - Interface utilisateur
- `requests` - Appels API HTTP
- API Flask du projet principal (doit être démarrée)

## 📝 Notes

- Le serveur Flask doit être démarré avant d'utiliser l'interface
- Les fichiers audio/images sont traités en mémoire (pas de stockage local)
- L'interface utilise des sessions Streamlit pour maintenir l'état
- Le streaming vidéo peut être gourmand en ressources CPU

## 🐛 Dépannage

**Erreur: "Impossible de se connecter à l'API"**
- Vérifiez que le serveur Flask est démarré
- Vérifiez l'URL dans `utils.py`
- Vérifiez qu'il n'y a pas de firewall bloquant

**Erreur: "Module not found"**
- Vérifiez que vous êtes dans le bon environnement virtuel
- Installez les dépendances: `pip install -r requirements.txt`

**Stream vidéo ne démarre pas**
- Vérifiez que la webcam est accessible
- Vérifiez l'index de la caméra (généralement 0)
- Pour Pepper, vérifiez l'URL du flux vidéo

