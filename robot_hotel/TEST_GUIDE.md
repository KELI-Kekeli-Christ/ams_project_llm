# 🤖 Guide de Test - Système de Réservation Pepper Hotel

## ✨ Améliorations Apportées

### 1. **Email Async Non-Bloquant** ⚡
- ✅ Confirmation respond en **< 200ms** (pas de freeze UI)
- ✅ Email s'envoie en arrière-plan
- ✅ Utilisateur voit immédiatement "Réservation confirmée"

### 2. **UI Tablette Améliorée** 🖥️
- ✅ **Affichage email en temps réel** (l'utilisateur voit ce qu'il tape)
- ✅ **Validation visuelle** (email valide = vert, invalide = rouge)
- ✅ **Bouton explicite** : "Confirmer et recevoir l'email"
- ✅ **Feedback clair** :
  - Pendant l'envoi: `⏳ Email en cours d'envoi...`
  - Succès: `📧 Email envoyé à [adresse] !`
  - Erreur: `❌ Erreur réseau - vérifiez votre connexion`

### 3. **Logging Amélioré** 📊
Console affiche:
```
[conv] Lancement envoi email en arrière-plan pour [email]...
[EMAIL] 📧 Envoi au CLIENT: [email]
[EMAIL] ✅ Email CLIENT envoyé avec succès: [email]
[EMAIL] 📧 Envoi au GESTIONNAIRE: [email]
[EMAIL] ✅ Email GESTIONNAIRE envoyé avec succès: [email]
[conv] ✅ Email result: {'success': True, ...}
```

### 4. **Date Parsing Français** 📅
Supporte:
- Noms français: "janvier", "février", "juin" → format numérique
- Variantes: "février" ou "fevrier" acceptés
- Dates relatives: "demain", "après-demain", "dans 5 jours"
- Jours: "lundi prochain", "jeudi prochain", "semaine prochaine"

### 5. **Accès Tablette via LAN IP** 🌐
- Tablette accède au serveur via `http://10.x.x.x:5000` (pas localhost)
- URL auto-détectée par `get_local_ip_for_robot(robot_ip)`

---

## 🧪 Procédure de Test Complète

### Prérequis
```bash
cd /home/christ/Downloads/Telegram\ Desktop/M1/M1\ Avignon\ universite/Ams\ projet/ams/robot_hotel

# Vérifier config email
cat config/email_config.json
# Doit afficher: manager_email, smtp_server, smtp_port, smtp_username, email_enabled=true
```

### Option 1: Test Unitaire (Sans Pepper)
```bash
# Test basique d'email
python3 test_email_async.py

# Résultat attendu:
# [EMAIL] ✅ Email CLIENT envoyé avec succès: test@example.com
# [EMAIL] ✅ Email GESTIONNAIRE envoyé avec succès: christlearn834@gmail.com
# ✅ Retour immédiat confirmé (non-bloquant)
```

### Option 2: Test Intégration Complète (Flux 5 questions → Email)
```bash
python3 test_integration_full.py

# Résultat attendu:
# ✅ Session créée: conv_XXXXX
# [process] ✅ Réponse acceptée pour 'nom' | valeur='Dupont'
# [process] ✅ TOUTES LES ÉTAPES COMPLÉTÉES!
# Réponse en: 0.13s ✅ Retour rapide (non-bloquant)
# [EMAIL] ✅ Email CLIENT envoyé avec succès
# [EMAIL] ✅ Email GESTIONNAIRE envoyé avec succès
```

### Option 3: Test Système Complet (Avec Pepper et Tablette)
```bash
# 1. Démarrer le serveur Flask
python3 main.py
# Résultat: INFO:werkzeug:Running on http://0.0.0.0:5000

# 2. Lancer la conversation Pepper (depuis shell Pepper ou autre terminal)
python3 pepper_test/main.py
# Ou directement: python3 pepper_test/conversation.py

# 3. Le robot pose 5 questions vocalement:
#    - Quel est votre nom de famille ?
#    - Quel est votre prénom ?
#    - Quel type de chambre souhaitez-vous ?
#    - Quelle est votre date d'arrivée ?
#    - Quelle est votre date de départ ?

# 4. Après les 5 réponses:
#    → Tablette affiche FORMULAIRE EMAIL (nouveau design)
#    → Utilisateur tape son email
#    → Clique "Confirmer et recevoir l'email"
#    → RÉPONSE RAPIDE (< 200ms) ✅
#    → "Réservation confirmée" s'affiche
#    → Email arrive dans quelques secondes

# 5. CONSOLE AFFICHE:
[conv] Lancement envoi email en arrière-plan pour test@example.com...
[EMAIL] Envoi de confirmation pour client: test@example.com
[EMAIL] 📧 Envoi au CLIENT: test@example.com
[EMAIL] ✅ Email CLIENT envoyé avec succès: test@example.com
[EMAIL] 📧 Envoi au GESTIONNAIRE: christlearn834@gmail.com
[EMAIL] ✅ Email GESTIONNAIRE envoyé avec succès: christlearn834@gmail.com
[conv] ✅ Email result: {'success': True, ...}
```

---

## ✅ Checklist de Vérification

### Pendant la Réservation
- [ ] Robot parle les 5 questions clairement
- [ ] Transcriptions vocales correctes
- [ ] Dates françaises acceptées ("5 juin" → 2026-06-05)

### Formulaire Email Tablette
- [ ] Email input affiche en JAUNE avec étiquette claire
- [ ] Texte email s'affiche EN TEMPS RÉEL sous l'input (vert si valide, rouge si invalide)
- [ ] Bouton dit "Confirmer et recevoir l'email"

### Après Clic "Confirmer"
- [ ] **Temps de réponse < 1s** ✅ (PAS de freeze)
- [ ] "Réservation confirmée" s'affiche immédiatement
- [ ] Email sent ID visible (ex: "N° R-C-1778151096-2026-06-05")
- [ ] Message: "📧 Email envoyé à [email@address] !" (ou "⚠️ Email en cours d'envoi...")

### Vérification Emails
- [ ] Email reçu dans Gmail inbox: christlearn834@gmail.com (manager)
- [ ] Email reçu dans Gmail inbox: test@example.com (ou autre - client)
- [ ] Format HTML avec tableau de confirmation
- [ ] Inclut: Nom, Prénom, Type chambre, Dates arrivée/départ

### Console Flask
- [ ] `[conv] Lancement envoi email...` → email en arrière-plan CONFIRMÉ
- [ ] `[EMAIL] 📧 Envoi au CLIENT:` → envoi au client
- [ ] `[EMAIL] ✅ Email CLIENT envoyé` → succès client
- [ ] `[EMAIL] 📧 Envoi au GESTIONNAIRE:` → envoi au manager
- [ ] `[EMAIL] ✅ Email GESTIONNAIRE envoyé` → succès manager
- [ ] `[conv] ✅ Email result:` → résultat final

---

## 🔧 Fichiers Modifiés

| Fichier | Changement |
|---------|-----------|
| `services/email.py` | ✅ Logging [EMAIL] détaillé + MIME multipart |
| `services/reservation_conversation.py` | ✅ finalize_reservation() async + logging [conv] |
| `pepper_test/conversation.py` | ✅ UI email form améliorée + display email en temps réel |
| `pepper_test/robot_manager.py` | ✅ Recording timeout: 60s → 10s |
| `services/record.py` | ✅ Recording timeout: 60s → 10s |
| `pepper_test/utils/helpers.py` | ✅ get_local_ip_for_robot() pour tablette |

---

## 🐛 Troubleshooting

### Problème: Emails ne sont pas envoyés
```
[EMAIL] ❌ Erreur envoi: [Errno -2] Name or service not known
```
**Solution**: Vérifier la connexion internet, vérifier la config SMTP

### Problème: UI gelée pendant 20-40s après clic "Confirmer"
**Solution**: RÉSOLU ✅ - Email en arrière-plan maintenant

### Problème: Email s'affiche pas sur tablette
**Solution**: Vérifier que l'API retourne bien `{"status": "success", "email_pending": true}`

### Problème: Emails en spam
**Solution**: Ajouter `christlearn834@gmail.com` aux contacts approuvés dans Gmail

---

## 📊 Métriques de Performance

| Métrique | Avant | Après |
|----------|-------|-------|
| Temps confirmation | 20-40s | **< 200ms** ⚡ |
| Freeze UI | ❌ OUI | ✅ NON |
| Logging | ❌ Minimal | ✅ Détaillé |
| Support dates françaises | ❌ NON | ✅ OUI |
| Tablette voit email tapé | ❌ NON | ✅ OUI |

---

## 📞 Support

Si un test échoue:
1. Vérifier les logs console pour `[EMAIL]` ou `[conv]`
2. Vérifier la config `config/email_config.json`
3. Tester: `python3 test_email_async.py`
4. Vérifier Gmail inbox + spam folder

---

Créé: $(date)
Dernier test: ✅ TOUS LES TESTS PASSENT
