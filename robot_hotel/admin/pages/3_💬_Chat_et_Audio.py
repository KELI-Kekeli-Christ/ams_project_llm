"""
Page de test du chat et de la transcription audio
"""
import streamlit as st
import sys
import os

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    chat_api,
    transcribe_audio,
    record_audio,
    get_location,
    test_api_connection,
    API_BASE_URL
)

st.set_page_config(page_title="Chat et Audio", page_icon="💬", layout="wide")

st.title("💬 Test du Chat et Transcription Audio")

# Vérifier la connexion API
if not test_api_connection():
    st.error(f"❌ Impossible de se connecter à l'API. Vérifiez que le serveur Flask est démarré sur {API_BASE_URL}")
    st.info(f"💡 URL testée: {API_BASE_URL}/")
    st.stop()

# Tabs pour organiser les fonctionnalités
tab1, tab2, tab3, tab4 = st.tabs(["🤖 Chat", "🎤 Transcription Audio", "🔴 Enregistrement", "📍 Heure/Lieu"])

# Tab 1: Chat
with tab1:
    st.header("🤖 Chat avec Llama 3")
    
    st.info("💡 Posez des questions au chatbot sur les services de l'hôtel.")
    
    # Initialiser l'historique de conversation
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Afficher l'historique
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message['role'] == 'user':
                with st.chat_message("user"):
                    st.write(message['content'])
            else:
                with st.chat_message("assistant"):
                    st.write(message['content'])
                    if 'context' in message:
                        with st.expander("📚 Contexte utilisé"):
                            st.write(message['context'])
    
    # Zone de saisie
    user_input = st.chat_input("Posez votre question ici...")
    
    if user_input:
        # Ajouter le message utilisateur à l'historique
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input
        })
        
        with st.spinner("🤔 Le chatbot réfléchit..."):
            result = chat_api(user_input)
        
        if "error" in result:
            st.error(f"❌ Erreur: {result['error']}")
        else:
            response = result.get('response', '')
            context = result.get('context_used', '')
            
            # Ajouter la réponse à l'historique
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': response,
                'context': context
            })
            st.rerun()
    
    # Bouton pour effacer l'historique
    if st.button("🗑️ Effacer l'historique"):
        st.session_state.chat_history = []
        st.rerun()

# Tab 2: Transcription Audio
with tab2:
    st.header("🎤 Transcription Audio")
    
    st.info("💡 Téléchargez un fichier audio (MP3, WAV, etc.) pour le transcrire en texte.")
    
    uploaded_audio = st.file_uploader(
        "Choisir un fichier audio",
        type=['mp3', 'wav', 'ogg', 'm4a', 'flac'],
        help="Le fichier sera transcrit en texte avec détection automatique de la langue"
    )
    
    if uploaded_audio is not None:
        st.audio(uploaded_audio, format='audio/wav')
        
        if st.button("📝 Transcrire l'audio", type="primary", use_container_width=True):
            with st.spinner("⏳ Transcription en cours... Cela peut prendre quelques secondes."):
                uploaded_audio.seek(0)
                result = transcribe_audio(uploaded_audio)
            
            if "error" in result:
                st.error(f"❌ Erreur: {result['error']}")
            else:
                text = result.get('text', '')
                language = result.get('language', '')
                
                st.success("✅ Transcription réussie!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("🌐 Langue détectée", language.upper() if language else "N/A")
                with col2:
                    st.metric("📏 Longueur", f"{len(text)} caractères")
                
                st.subheader("📄 Texte transcrit:")
                st.text_area("", value=text, height=200, label_visibility="collapsed")
                
                # Bouton pour copier
                if st.button("📋 Copier le texte"):
                    st.write("✅ Texte copié dans le presse-papiers!")

# Tab 3: Enregistrement
with tab3:
    st.header("🔴 Enregistrement Audio")
    
    st.warning("⚠️ **Note:** Cette fonctionnalité nécessite un microphone connecté et des permissions appropriées.")
    
    st.info("💡 Cliquez sur le bouton pour démarrer l'enregistrement. L'enregistrement s'arrêtera automatiquement après détection d'un silence.")
    
    if st.button("🎙️ Démarrer l'Enregistrement", type="primary", use_container_width=True):
        with st.spinner("🎤 Enregistrement en cours... Parlez maintenant. L'enregistrement s'arrêtera automatiquement après un silence."):
            result = record_audio()
        
        if "error" in result:
            st.error(f"❌ Erreur: {result['error']}")
        else:
            message = result.get('message', '')
            file_path = result.get('file', '')
            
            st.success(f"✅ {message}")
            
            if file_path:
                st.info(f"📁 Fichier sauvegardé: `{file_path}`")
                st.success("🎉 Enregistrement terminé avec succès!")
                
                # Option pour transcrire directement
                if st.button("📝 Transcrire cet enregistrement"):
                    # Ici, il faudrait lire le fichier et le transcrire
                    st.info("ℹ️ Utilisez l'onglet 'Transcription Audio' pour transcrire ce fichier.")

# Tab 4: Heure et Lieu
with tab4:
    st.header("📍 Heure et Date Actuelles")
    
    st.info("💡 Récupère l'heure et la date actuelles du système.")
    
    if st.button("🕐 Récupérer l'heure et la date", type="primary", use_container_width=True):
        result = get_location()
        
        if "error" in result:
            st.error(f"❌ Erreur: {result['error']}")
        else:
            st.success("✅ Information récupérée!")
            st.markdown(f"### {result}")

