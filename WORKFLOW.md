# Workflow Système Robot Hotel

## Vue d'ensemble

Le système Robot Hotel comprend 3 workflows principaux qui couvrent les interactions utilisateur de bout en bout.

---

## Workflow 1 : Reconnaissance Faciale et Accueil Personnalisé

```mermaid
flowchart TD
    A[Client arrive] --> B[Robot Pepper / Caméra]
    B --> C[API Flask /face/detect]
    C --> D[Service Reconnaissance Faciale]
    D --> E[Base de Données Visages<br/>friends.pkl]
    E -->|Recherche match| D
    D -->|Identité client| C
    C -->|Résultat| B
    B -->|Accueil personnalisé| A
    
    style A fill:#3498db,stroke:#2980b9,color:#fff
    style B fill:#e74c3c,stroke:#c0392b,color:#fff
    style C fill:#2ecc71,stroke:#27ae60,color:#fff
    style D fill:#9b59b6,stroke:#8e44ad,color:#fff
    style E fill:#f39c12,stroke:#e67e22,color:#fff
```

### Étapes détaillées :
1. **Client arrive** → Se place devant le robot ou la caméra
2. **Photo capturée** → Image envoyée à l'API Flask
3. **Détection faciale** → Utilisation de YOLOv8 + face_recognition
4. **Recherche en base** → Comparaison avec encodages stockés
5. **Match trouvé** → Identité du client récupérée
6. **Accueil personnalisé** → Message adapté au client reconnu

---

## Workflow 2 : Interaction avec le Chatbot

```mermaid
flowchart TD
    A[Client pose question] --> B[Robot/Streamlit Interface]
    B --> C[API Flask /chat]
    C --> D[Service Chat Llama 3.1]
    D --> E[Système RAG]
    E --> F[Documentation Hôtel<br/>Vector Store]
    F -->|Contexte pertinent| E
    E -->|Contexte enrichi| D
    D -->|Réponse contextuelle| C
    C -->|Réponse| B
    B -->|Affichage réponse| A
    
    style A fill:#3498db,stroke:#2980b9,color:#fff
    style B fill:#e74c3c,stroke:#c0392b,color:#fff
    style C fill:#2ecc71,stroke:#27ae60,color:#fff
    style D fill:#9b59b6,stroke:#8e44ad,color:#fff
    style E fill:#9b59b6,stroke:#8e44ad,color:#fff
    style F fill:#f39c12,stroke:#e67e22,color:#fff
```

### Étapes détaillées :
1. **Question utilisateur** → Texte ou audio
2. **Envoi à l'API** → Endpoint `/chat` de Flask
3. **Recherche RAG** → Recherche sémantique dans documentation
4. **Contexte récupéré** → Informations pertinentes extraites
5. **Génération réponse** → Llama 3.1 avec contexte temporel (date/heure)
6. **Réponse affichée** → Réponse contextuelle à l'utilisateur

---

## Workflow 3 : Création de Réservation par Voix

```mermaid
flowchart TD
    A[Client enregistre audio] --> B[API Flask /record]
    B --> C[Service Whisper<br/>Transcription]
    C --> D[Service Llama 3.1<br/>Extraction Info]
    D --> E[API FastAPI<br/>/create_reservation]
    E --> F[(SQLite<br/>Réservations)]
    F --> G[Génération QR Code]
    G --> H[Notification Email]
    H -->|Email + QR en PJ| I[Gestionnaire]
    
    E -->|ID Réservation| G
    G -->|QR Code PNG| H
    
    style A fill:#3498db,stroke:#2980b9,color:#fff
    style B fill:#e74c3c,stroke:#c0392b,color:#fff
    style C fill:#9b59b6,stroke:#8e44ad,color:#fff
    style D fill:#9b59b6,stroke:#8e44ad,color:#fff
    style E fill:#2ecc71,stroke:#27ae60,color:#fff
    style F fill:#f39c12,stroke:#e67e22,color:#fff
    style G fill:#9b59b6,stroke:#8e44ad,color:#fff
    style H fill:#1abc9c,stroke:#16a085,color:#fff
    style I fill:#3498db,stroke:#2980b9,color:#fff
```

### Étapes détaillées :
1. **Enregistrement audio** → Client parle sa demande de réservation
2. **Transcription Whisper** → Audio converti en texte
3. **Extraction informations** → Llama 3.1 extrait :
   - Nom et prénom
   - Dates (convertit dates relatives → absolues)
   - Type de chambre
4. **Création client** → Si client n'existe pas, création automatique
5. **Création réservation** → Sauvegarde dans SQLite via FastAPI
6. **Génération QR code** → QR code PNG généré et stocké
7. **Notification email** → Email envoyé au gestionnaire avec :
   - Détails de la réservation
   - QR code en pièce jointe

---

## Workflow 4 : Vérification QR Code (Check-in)

```mermaid
flowchart TD
    A[Client présente QR code] --> B[Scan QR Code<br/>Camera/Image]
    B --> C[API Flask /scan_qr]
    C --> D[Décodage QR<br/>OpenCV]
    D --> E[API FastAPI<br/>/verify_qr]
    E --> F[(SQLite<br/>Réservations)]
    F -->|Vérification| E
    E -->|Informations réservation| C
    C -->|Affichage détails| B
    B --> G[Confirmation arrivée<br/>/confirm_arrival]
    G --> E
    E -->|Statut mis à jour| F
    
    style A fill:#3498db,stroke:#2980b9,color:#fff
    style B fill:#e74c3c,stroke:#c0392b,color:#fff
    style C fill:#2ecc71,stroke:#27ae60,color:#fff
    style D fill:#9b59b6,stroke:#8e44ad,color:#fff
    style E fill:#2ecc71,stroke:#27ae60,color:#fff
    style F fill:#f39c12,stroke:#e67e22,color:#fff
    style G fill:#1abc9c,stroke:#16a085,color:#fff
```

### Étapes détaillées :
1. **Scan QR code** → Via caméra Streamlit ou upload image
2. **Décodage** → OpenCV décode le QR code (récupère ID réservation)
3. **Vérification** → Appel API FastAPI pour récupérer les détails
4. **Affichage informations** → Réservation + Client affichés
5. **Confirmation arrivée** → Statut mis à jour en "arrivé"

---

## Architecture Système

```mermaid
graph TB
    subgraph "Clients"
        A1[Robot Pepper]
        A2[Interface Streamlit]
        A3[API Clients]
    end
    
    subgraph "API Flask - Port 5000"
        B1[Endpoints Chat]
        B2[Endpoints Face Detection]
        B3[Endpoints Audio]
        B4[Endpoints QR Code]
    end
    
    subgraph "Services IA"
        C1[Service Chat + RAG]
        C2[Service Reconnaissance]
        C3[Service Whisper]
        C4[Service Réservation]
    end
    
    subgraph "API FastAPI - Port 8000"
        D1[Gestion Réservations]
        D2[Gestion Clients]
        D3[QR Codes]
    end
    
    subgraph "Stockage"
        E1[(SQLite<br/>Réservations)]
        E2[(Pickle<br/>Visages)]
        E3[Documentation<br/>RAG]
        E4[QR Codes<br/>PNG]
    end
    
    subgraph "Notifications"
        F1[Service Email]
        F2[SMTP Server]
    end
    
    A1 --> B2
    A1 --> B1
    A1 --> B3
    A2 --> B1
    A2 --> B2
    A2 --> B4
    
    B1 --> C1
    B2 --> C2
    B3 --> C3
    B4 --> C4
    
    C1 --> E3
    C2 --> E2
    C4 --> D1
    
    D1 --> E1
    D1 --> D3
    D3 --> E4
    D1 --> F1
    F1 --> F2
    
    style A1 fill:#e74c3c
    style A2 fill:#3498db
    style B1 fill:#2ecc71
    style B2 fill:#2ecc71
    style B3 fill:#2ecc71
    style B4 fill:#2ecc71
    style C1 fill:#9b59b6
    style C2 fill:#9b59b6
    style C3 fill:#9b59b6
    style C4 fill:#9b59b6
    style D1 fill:#2ecc71
    style E1 fill:#f39c12
    style E2 fill:#f39c12
    style F1 fill:#1abc9c
```

---

## Flux de Données

### Reconnaissance Faciale
```
Image → YOLOv8 → face_recognition → Encodage → Comparaison → Match/Non-match
```

### Chatbot avec RAG
```
Question → Embedding → Recherche Vectorielle → Contexte → Llama 3.1 → Réponse
```

### Réservation
```
Audio → Whisper → Texte → Llama 3.1 Extraction → FastAPI → SQLite → QR Code → Email
```

---

## Technologies Utilisées par Workflow

### Workflow 1 (Reconnaissance)
- **YOLOv8** : Détection de visages
- **face_recognition** : Encodage et reconnaissance
- **Pickle** : Stockage encodages

### Workflow 2 (Chat)
- **Llama 3.1-8B-Instruct** : Modèle de langage
- **LlamaIndex** : Indexation vectorielle
- **HuggingFace Embeddings** : Embeddings sémantiques

### Workflow 3 (Réservation)
- **Whisper Medium** : Transcription audio
- **Llama 3.1** : Extraction d'informations
- **FastAPI** : API réservations
- **SQLite + SQLAlchemy** : Base de données
- **qrcode** : Génération QR codes
- **smtplib** : Envoi emails

### Workflow 4 (QR Code)
- **OpenCV** : Décodage QR codes
- **FastAPI** : Vérification réservations

---

## Gestion des Erreurs

Chaque workflow inclut :
- **Validation des inputs** : Vérification données entrantes
- **Gestion d'erreurs** : Messages clairs en cas d'échec
- **Fallback** : Solutions de secours (ex: CPU si GPU saturé)
- **Logs** : Traçabilité complète des opérations

---

## Performances

### Temps de réponse attendus :
- **Reconnaissance faciale** : < 3 secondes
- **Réponse chatbot** : < 5 secondes
- **Transcription audio** : < 10 secondes (selon longueur)
- **Création réservation** : < 30 secondes (workflow complet)

---

## Diagramme Image

Un diagramme visuel détaillé est disponible dans :
- `workflow_robot_hotel.png` (image haute résolution)
- `workflow_robot_hotel.pdf` (format vectoriel)

Pour régénérer le diagramme :
```bash
python3 generate_workflow_diagram.py
```

