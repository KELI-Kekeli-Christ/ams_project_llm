# Fixtures de Test

Ce dossier contient les fichiers de test utilisés par les tests unitaires, d'intégration et de sécurité.

## Structure

- **Images** : Images de test pour la reconnaissance faciale
  - `test_face.jpg` : Image de visage pour tests
  - `test_multiple_faces.jpg` : Image avec plusieurs visages
  
- **Audio** : Fichiers audio pour tests de transcription
  - `test_audio.wav` : Audio de test pour transcription
  - `test_reservation_audio.wav` : Audio avec demande de réservation

- **QR Codes** : Images de QR codes pour tests
  - `test_qr_code.png` : QR code de test

## Note

Les fichiers réels ne sont pas versionnés dans Git (ajoutés au .gitignore) car ils peuvent être volumineux.
Créer les fichiers nécessaires manuellement ou utiliser des générateurs pour les créer à la volée dans les tests.

