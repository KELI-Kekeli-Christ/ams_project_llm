# Cahier des Charges - Robot Hotel

## 📋 Contexte et Objectifs

### Contexte
- Système intelligent d'accueil et de gestion hôtelière
- Basé sur robot humanoïde Pepper (SoftBank Robotics)
- Améliorer l'expérience client et automatiser les tâches
- Service d'information 24/7 sur les services hôteliers

### Objectifs Fonctionnels
- Reconnaissance faciale pour personnaliser l'accueil
- Chatbot intelligent (Llama 3.1) avec contexte RAG
- Transcription et traitement de la parole (Whisper)
- API REST complète (Flask)
- Interface d'administration web (Streamlit)
- Gestion de réservations automatique

### Objectifs Techniques
- Architecture modulaire
- Performances temps réel
- Compatibilité Robot Pepper
- Documentation API complète (Swagger)

---

## 🎯 Périmètre du Projet

### Fonctionnalités de Reconnaissance Faciale
- Enregistrement de personnes via upload d'image
- Détection en temps réel dans images/flux vidéo
- Reconnaissance avec niveau de confiance
- Gestion de la base de données (liste, modification, suppression)
- Streaming vidéo depuis webcam ou robot Pepper

### Fonctionnalités de Chat Intelligent
- Chatbot conversationnel (Llama 3.1-8B-Instruct)
- Contexte RAG pour réponses précises
- Connaissance temporelle (date/heure actuelles)
- Support multilingue (français, anglais, etc.)
- Réponses contextuelles sur services hôteliers

### Fonctionnalités Audio et Transcription
- Transcription automatique (WAV, MP3, OGG, M4A, FLAC)
- Détection automatique de langue
- Enregistrement vocal depuis microphone
- Détection automatique de silence (2 secondes)

### Fonctionnalités de Gestion de Réservations
- Création depuis audio (parole)
- Extraction intelligente (nom, prénom, dates, type de chambre)
- Conversion dates relatives → dates absolues
- Intégration API FastAPI
- Génération automatique de QR codes

### Fonctionnalités d'Administration
- Interface web Streamlit complète
- 5 onglets principaux
- Gestion des visages
- Monitoring en temps réel
- Outils de test intégrés

---

## 🛠️ Technologies Utilisées

### Langages
- Python 3.12+
- Bash (scripts d'automatisation)

### Frameworks
- Flask (API REST principale)
- FastAPI (API réservations)
- Streamlit (Interface admin)
- Uvicorn (Serveur ASGI)
- Flasgger (Documentation Swagger)

### Intelligence Artificielle
- Llama 3.1-8B-Instruct (Chatbot)
- Whisper Medium (Transcription audio)
- YOLOv8 (Détection d'objets/personnes)
- face_recognition (Reconnaissance faciale)
- OpenCV (Traitement images/vidéo)

### RAG (Retrieval-Augmented Generation)
- LlamaIndex (Indices vectoriels)
- HuggingFace Embeddings (sentence-transformers)
- Vector Store (Recherche sémantique)

### Bases de Données
- Pickle (Base visages)
- SQLite (Réservations via FastAPI)
- SQLAlchemy (ORM)

---

## 👥 Public Cible

### Utilisateurs Finaux (Clients)
- Âge : 25-65 ans
- Profil : Voyageurs d'affaires, touristes, familles
- Compétences : Faibles à moyennes
- Langues : Français, anglais, espagnol, allemand

### Utilisateurs Administrateurs
- Profil : Personnel réception, gestionnaires
- Compétences : Moyennes à élevées
- Rôle : Configuration, gestion, maintenance

---

## 📝 Scénarios de Tests

### Scénario 1 : Reconnaissance et Accueil
- Enregistrer son visage
- Se placer devant robot/caméra
- Vérifier identification
- Recevoir accueil personnalisé

**Critères** : 80% précision, < 3s détection

### Scénario 2 : Interaction Conversationnelle
- Poser questions sur services
- Questions sur équipements
- Questions complexes multi-informations
- Questions temporelles (date/heure)
- Questions en anglais

**Critères** : > 85% pertinence, < 5s réponse

### Scénario 3 : Création Réservation par Voix
- Enregistrer demande vocale
- Date absolue ou relative
- Vérifier transcription
- Vérifier extraction informations
- Confirmer création réservation
- Vérifier QR code généré

**Critères** : > 90% transcription, > 85% extraction

### Scénario 4 : Gestion Administrative
- Accéder interface admin
- Enregistrer nouvelle personne
- Lister personnes enregistrées
- Tester détection faciale
- Démarrer/arrêter streaming

**Critères** : Navigation intuitive, < 2min par opération

### Scénario 5 : Intégration Robot Pepper
- Démarrer système complet
- Reconnaissance via Pepper
- Interaction vocale
- Créer réservation via Pepper
- Vérifier synchronisation

**Critères** : Pas de latence excessive, communication fiable

---

## ✅ Fonctionnalités Implémentées

### Architecture Multi-Services
- ✅ API Flask (port 5000) avec Swagger
- ✅ API FastAPI (port 8000) pour réservations
- ✅ Interface Streamlit (port 8501)
- ✅ Script bash de lancement unifié
- ✅ Gestion environnements virtuels séparés

### Reconnaissance Faciale
- ✅ Enregistrement personnes via upload
- ✅ Détection temps réel (YOLOv8 + face_recognition)
- ✅ Streaming vidéo (webcam/URL)
- ✅ Gestion base de données complète
- ✅ Interface admin dédiée

### Chat Intelligent
- ✅ Chatbot Llama 3.1-8B-Instruct
- ✅ Système RAG opérationnel (LlamaIndex)
- ✅ Contexte temporel intégré
- ✅ Réponses contextuelles
- ✅ Interface chat avec historique
- ✅ Support multilingue

### Transcription Audio
- ✅ Transcription Whisper Medium
- ✅ Support multiples formats (WAV, MP3, OGG, etc.)
- ✅ Détection langue automatique
- ✅ Enregistrement vocal avec détection silence
- ✅ Interface admin dédiée

### Gestion Réservations
- ✅ Création depuis audio
- ✅ Extraction intelligente (Llama 3.1)
- ✅ Conversion dates relatives → absolues
- ✅ API FastAPI complète
- ✅ Génération QR codes automatique
- ✅ Vérification QR codes
- ✅ Confirmation d'arrivée

### Scan QR Codes
- ✅ Scan depuis image
- ✅ Scan depuis caméra Streamlit
- ✅ Streaming backend temps réel
- ✅ Auto-détection (arrêt si trouvé)
- ✅ Interface vérification complète

### Notifications Email
- ✅ Envoi automatique lors création réservation
- ✅ Configuration SMTP flexible
- ✅ Email HTML formaté
- ✅ QR code en pièce jointe
- ✅ Support Gmail, Outlook, autres SMTP
- ✅ Activation/désactivation

### Interface Streamlit
- ✅ 5 onglets organisés
  - Gestion Visages
  - Streaming Vidéo
  - Chat et Audio
  - Réservations
  - Configuration Email
- ✅ Test connexion API
- ✅ Gestion erreurs complète
- ✅ Feedback utilisateur

### Intégration Pepper
- ✅ Script principal complet
- ✅ Enregistrement audio robot
- ✅ Transcription + Chat + Réponse vocale
- ✅ Création réservations
- ✅ Scan QR codes
- ✅ Interface tablette HTML

---

## 🚀 Améliorations Futures

### Court Terme (3-6 mois)
- 📊 Dashboard analytics
- 🔐 Authentification multi-utilisateurs
- 🎯 Amélioration précision reconnaissance
- 📧 Templates emails personnalisables
- 🐳 Dockerisation complète

### Moyen Terme (6-12 mois)
- 📱 Application mobile clients
- 🧠 Fine-tuning chatbot
- 💳 Système de paiement
- 📲 Notifications SMS/WhatsApp
- 🗄️ Migration PostgreSQL
- 📈 Monitoring et alertes

### Long Terme (12+ mois)
- 🤖 IA avancée (sentiment, recommandations)
- 👥 Support multi-robots
- 🔗 Intégrations externes (PMS, CRM)
- 📊 Analytics prédictifs
- 🌐 Extension autres secteurs

### Améliorations Interface
- Dashboard avec statistiques
- Thème sombre/clair
- Export données (CSV/Excel)
- Notifications temps réel
- Multi-utilisateurs avec rôles

### Améliorations IA
- Fine-tuning modèles
- Mémoire conversationnelle
- Personnalisation par client
- Support multimodal (images)
- Analyse de sentiment

### Améliorations Techniques
- Cache intelligent
- Load balancing
- Base données optimisée
- Chiffrement données
- HTTPS obligatoire
- Conformité RGPD
- Audit trail complet

---

## 📊 Critères de Réussite

### Performances Techniques
- Taux reconnaissance faciale : ≥ 85%
- Temps détection : ≤ 3 secondes
- Taux transcription : ≥ 90% (WER)
- Temps réponse API : ≤ 2s (95% requêtes)
- Disponibilité : ≥ 95%

### Performances Utilisateur
- Taux réussite tâches : ≥ 80%
- Temps accomplissement :
  - Reconnaissance : ≤ 10s
  - Réservation : ≤ 2min
  - Question chatbot : ≤ 30s
- Taux abandon : ≤ 15%
- Erreurs par session : ≤ 2

### Satisfaction Utilisateur
- Score global : ≥ 4.0/5.0
- Net Promoter Score : ≥ 50
- Intention utilisation future : ≥ 70%
- Recommandation : ≥ 75%

---

## ⚠️ Contraintes et Risques

### Contraintes Techniques
- Disponibilité Robot Pepper limitée
- Ressources computationnelles importantes
- Stockage modèles ML (plusieurs Go)
- Connexion réseau stable nécessaire
- Compatibilité Python 3.12+
- Multiples environnements virtuels

### Risques
- Performance modèles IA
- Intégration Pepper
- Bugs critiques
- Problèmes déploiement
- Acceptabilité utilisateurs
- Complexité perçue
- Fiabilité perçue

### Mesures d'Atténuation
- Tests approfondis
- Documentation complète
- Système logs détaillé
- Mode dégradé (fallback)
- Tests utilisateurs précoces
- Design simple et intuitif
- Messages erreurs clairs

---

## 📅 Planning Prévisionnel

### Phase 1 : Conception (4 semaines)
- Analyse besoins
- Design architecture
- Choix technologies
- Environnement développement

### Phase 2 : Développement Core (6 semaines)
- API Flask
- Reconnaissance faciale
- Chatbot + RAG
- Transcription audio
- Interface Streamlit

### Phase 3 : Fonctionnalités Avancées (4 semaines)
- Système réservations
- Intégration FastAPI
- Optimisation performances
- Gestion erreurs

### Phase 4 : Tests et Intégration (3 semaines)
- Tests unitaires/intégration
- Intégration Pepper
- Tests charge/performance
- Correction bugs

### Phase 5 : Tests Utilisateurs (4 semaines)
- Tests exploratoires (10-15 users)
- Tests fonctionnels (20-30 users)
- Analyse retours
- Identification améliorations

### Phase 6 : Finalisation (3 semaines)
- Implémentation corrections
- Améliorations utilisateurs
- Tests validation
- Documentation finale

**Durée totale** : 24 semaines (6 mois)

---

## 👨‍💻 Équipe Projet

### Rôles
- Chef de projet
- Développeurs Backend
- Développeur Frontend/Interface
- Spécialiste IA/ML
- Intégrateur Robot Pepper
- Testeurs/UX Researchers

### Communication
- Réunion hebdomadaire équipe
- Revue sprint (toutes les 2 semaines)
- Rétrospective
- Outils collaboratifs (Git, docs partagées)

---

## 📚 Documentation

### Documents Disponibles
- Cahier des charges (LaTeX)
- Documentation API (Swagger)
- Guide installation/déploiement
- Guide utilisation interface admin
- Procédures maintenance
- Documentation modèles IA

### Outils de Test
- Enregistrement vidéo sessions
- Logs système intégrés
- Métriques performance
- Questionnaires (pré/post-test)
- Analyse comportementale

---

## 🎯 Conclusion

Système intelligent d'accueil et gestion hôtelière combinant :
- Intelligence artificielle (chatbot, transcription, reconnaissance)
- Robotique (Pepper)
- Interfaces modernes (Streamlit, APIs REST)
- Gestion automatisée (réservations, notifications)

Objectif : Améliorer expérience client tout en validant acceptabilité technologies innovantes en contexte hôtelier réel.

**Version document** : 1.0
**Date** : Janvier 2025

