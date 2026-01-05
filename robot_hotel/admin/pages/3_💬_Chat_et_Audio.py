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
        
        # Afficher les informations du fichier
        st.info(f"📁 Fichier: {uploaded_audio.name} ({uploaded_audio.size} octets)")
        
        if st.button("📝 Transcrire l'audio", type="primary", use_container_width=True):
            try:
                with st.spinner("⏳ Transcription en cours... Cela peut prendre quelques secondes."):
                    # S'assurer que le fichier est à la position 0 (début)
                    uploaded_audio.seek(0)
                    
                    # Créer un BytesIO pour garantir que le fichier est bien passé
                    import io
                    audio_bytes = uploaded_audio.read()
                    audio_file = io.BytesIO(audio_bytes)
                    audio_file.name = uploaded_audio.name  # Préserver le nom du fichier
                    
                    # Réinitialiser le pointeur
                    audio_file.seek(0)
                    
                    result = transcribe_audio(audio_file)
                
                if result and "error" not in result:
                    text = result.get('text', '')
                    language = result.get('language', '')
                    
                    if text:
                        st.success("✅ Transcription réussie!")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("🌐 Langue détectée", language.upper() if language else "N/A")
                        with col2:
                            st.metric("📏 Longueur", f"{len(text)} caractères")
                        
                        st.subheader("📄 Texte transcrit:")
                        st.text_area("", value=text, height=200, label_visibility="collapsed", key="transcribed_text")
                        
                        # Bouton pour copier
                        if st.button("📋 Copier le texte", key="copy_text_btn"):
                            st.write("✅ Texte copié dans le presse-papiers!")
                    else:
                        st.warning("⚠️ Aucun texte n'a été transcrit. Le fichier audio est peut-être trop court ou silencieux.")
                else:
                    error_msg = result.get('error', 'Erreur inconnue') if result else 'Aucune réponse du serveur'
                    st.error(f"❌ Erreur: {error_msg}")
                    if result:
                        with st.expander("🔍 Détails de l'erreur"):
                            st.json(result)
            except Exception as e:
                st.error(f"❌ Erreur lors de la transcription: {str(e)}")
                import traceback
                with st.expander("🔍 Détails de l'erreur"):
                    st.code(traceback.format_exc())

# Tab 3: Enregistrement
with tab3:
    st.header("🔴 Enregistrement Audio")
    
    st.warning("⚠️ **Note:** Cette fonctionnalité nécessite un microphone connecté et des permissions appropriées.")
    
    st.info("💡 Cliquez sur le bouton pour démarrer l'enregistrement. L'enregistrement s'arrêtera automatiquement après **3 secondes de silence**.")
    st.warning("⚠️ **Astuce:** L'enregistrement est maintenant configuré pour permettre des pauses naturelles lors de la parole. Il s'arrêtera seulement après 3 secondes de silence complet.")
    
    if st.button("🎙️ Démarrer l'Enregistrement", type="primary", use_container_width=True):
        with st.spinner("🎤 Enregistrement en cours... Parlez maintenant. Vous pouvez faire des pauses naturelles. L'enregistrement s'arrêtera après 3 secondes de silence complet."):
            result = record_audio()
        
        if result and "error" in result:
            st.error(f"❌ Erreur: {result['error']}")
        elif result:
            message = result.get('message', '')
            file_path = result.get('file', '')
            
            st.success(f"✅ {message}")
            
            if file_path:
                st.info(f"📁 Fichier sauvegardé: `{file_path}`")
                st.success("🎉 Enregistrement terminé avec succès!")
                
                # Option pour transcrire directement
                if st.button("📝 Transcrire cet enregistrement", key="transcribe_recorded"):
                    # Essayer de lire et transcrire le fichier
                    try:
                        import io
                        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                        full_path = os.path.join(script_dir, file_path)
                        
                        if os.path.exists(full_path):
                            with open(full_path, 'rb') as f:
                                audio_file = io.BytesIO(f.read())
                                audio_file.name = os.path.basename(full_path)
                                
                                with st.spinner("⏳ Transcription en cours..."):
                                    transcribe_result = transcribe_audio(audio_file)
                                
                                if transcribe_result and "error" not in transcribe_result:
                                    text = transcribe_result.get('text', '')
                                    if text:
                                        st.success("✅ Transcription réussie!")
                                        st.text_area("Texte transcrit:", value=text, height=200)
                                    else:
                                        st.warning("⚠️ Aucun texte n'a été transcrit.")
                                else:
                                    error_msg = transcribe_result.get('error', 'Erreur inconnue') if transcribe_result else 'Aucune réponse'
                                    st.error(f"❌ Erreur lors de la transcription: {error_msg}")
                        else:
                            st.error(f"❌ Fichier non trouvé: {full_path}")
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")
                        st.info("ℹ️ Utilisez l'onglet 'Transcription Audio' pour télécharger et transcrire ce fichier.")
            else:
                st.warning("⚠️ Aucun fichier retourné par l'enregistrement.")

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

