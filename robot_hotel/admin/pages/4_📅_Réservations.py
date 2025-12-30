"""
Page de gestion des réservations
"""
import streamlit as st
import sys
import os
import json

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    make_reservation,
    test_api_connection,
    API_BASE_URL
)

st.set_page_config(page_title="Réservations", page_icon="📅", layout="wide")

st.title("📅 Gestion des Réservations")

# Vérifier la connexion API
if not test_api_connection():
    st.error(f"❌ Impossible de se connecter à l'API. Vérifiez que le serveur Flask est démarré sur {API_BASE_URL}")
    st.info(f"💡 URL testée: {API_BASE_URL}/")
    st.stop()

st.header("🎤 Créer une Réservation depuis un Audio")

st.info("""
💡 **Instructions:** 
- Téléchargez un fichier audio contenant une demande de réservation
- L'audio sera automatiquement transcrit
- Les informations seront extraites et envoyées à l'API de réservation
- Le système détectera: nom, prénom, type de chambre, dates d'arrivée et de départ
""")

uploaded_audio = st.file_uploader(
    "Choisir un fichier audio avec la demande de réservation",
    type=['mp3', 'wav', 'ogg', 'm4a', 'flac'],
    help="L'audio doit contenir les informations de réservation (nom, prénom, dates, type de chambre)"
)

if uploaded_audio is not None:
    st.audio(uploaded_audio, format='audio/wav')
    
    # Aperçu des informations attendues
    with st.expander("ℹ️ Informations à mentionner dans l'audio"):
        st.markdown("""
        Pour créer une réservation, mentionnez dans l'audio:
        
        - **Nom du client**
        - **Prénom du client**
        - **ID client** (optionnel)
        - **Type de chambre:** simple, double, ou suite
        - **Date d'arrivée** (format: JJ/MM/AAAA ou JJ-MM-AAAA)
        - **Date de départ** (format: JJ/MM/AAAA ou JJ-MM-AAAA)
        
        **Exemple:** "Bonjour, je souhaite réserver une chambre double pour Jean Dupont, 
        arrivée le 25 décembre 2025, départ le 30 décembre 2025."
        """)
    
    if st.button("📅 Créer la Réservation", type="primary", use_container_width=True):
        with st.spinner("⏳ Traitement en cours... Transcription de l'audio, extraction des informations et création de la réservation."):
            uploaded_audio.seek(0)
            result = make_reservation(uploaded_audio)
        
        # Afficher les résultats
        status = result.get('status', 'error')
        
        if status == 'error' or 'error' in result:
            st.error(f"❌ Erreur: {result.get('error', 'Erreur inconnue')}")
        elif status == 'success':
            st.success("✅ Réservation créée avec succès!")
            st.balloons()
            
            # Afficher la transcription
            transcript = result.get('transcript', '')
            language = result.get('language', '')
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🌐 Langue détectée", language.upper() if language else "N/A")
            with col2:
                st.metric("📏 Longueur du transcript", f"{len(transcript)} caractères")
            
            # Transcription
            st.subheader("📄 Transcription de l'audio")
            st.text_area("", value=transcript, height=100, label_visibility="collapsed", disabled=True)
            
            # Données extraites
            reservation_data = result.get('reservation_data', {})
            if reservation_data:
                st.subheader("📋 Données de Réservation Extraites")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    **👤 Client:**
                    - Nom: {reservation_data.get('nom', 'N/A')}
                    - Prénom: {reservation_data.get('prenom', 'N/A')}
                    - ID Client: {reservation_data.get('id_client', 'N/A')}
                    """)
                
                with col2:
                    st.markdown(f"""
                    **🏨 Chambre:**
                    - Type: {reservation_data.get('type_chambre', 'N/A')}
                    - Arrivée: {reservation_data.get('date_arrivee', 'N/A')}
                    - Départ: {reservation_data.get('date_depart', 'N/A')}
                    """)
            
            # Réponse de l'API
            api_response = result.get('api_response', {})
            if api_response:
                st.subheader("📤 Réponse de l'API de Réservation")
                
                # Afficher en format JSON pour plus de clarté
                st.json(api_response)
                
                # Extraire les informations importantes
                reservation_id = api_response.get('reservation_id') or api_response.get('id')
                if reservation_id:
                    st.success(f"🎉 ID de réservation: **{reservation_id}**")
        
        else:
            st.warning("⚠️ Statut inconnu dans la réponse")
            st.json(result)

# Section d'information
st.divider()
st.subheader("ℹ️ Informations")
st.markdown("""
### À propos de la création de réservations:

1. **Processus automatique:**
   - Transcription de l'audio avec Whisper
   - Extraction automatique des informations avec IA
   - Envoi à l'API de réservation
   - Retour de confirmation avec ID de réservation

2. **Types de chambres acceptés:**
   - `simple` - Chambre simple
   - `double` - Chambre double
   - `suite` - Suite

3. **Format des dates:**
   - Accepte plusieurs formats: JJ/MM/AAAA, JJ-MM-AAAA, JJ MMM AAAA
   - Exemples: 25/12/2025, 25-12-2025, 25 décembre 2025

4. **Exemple de phrase dans l'audio:**
   > "Bonjour, je voudrais réserver une chambre double pour Jean Dupont, 
   > arrivée le 25 décembre 2025 et départ le 30 décembre 2025."
""")

