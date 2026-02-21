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
    chat_voice,
    transcribe_audio,
    record_audio,
    get_location,
    test_api_connection,
    API_BASE_URL
)

st.set_page_config(page_title="Chat et Audio", page_icon="💬", layout="wide")

st.title("💬 Chat, Vocal et Audio")

# Vérifier la connexion API
if not test_api_connection():
    st.error(f"❌ Impossible de se connecter à l'API. Vérifiez que le serveur Flask est démarré sur {API_BASE_URL}")
    st.info(f"💡 URL testée: {API_BASE_URL}/")
    st.stop()

# Tabs : Chat, Transcription, Appel vocal, Enregistrement, Heure/Lieu
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🤖 Chat",
    "🎤 Transcription Audio",
    "☎️ Appel vocal",
    "🔴 Enregistrement",
    "📍 Heure/Lieu"
])

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
        type=['mp3', 'wav', 'ogg', 'm4a', 'flac', 'webm', 'mp4'],
        help="WAV, WebM (navigateur), MP4, etc. Transcrit avec détection automatique de la langue."
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

# Tab 3: Appel vocal (comme le chat web : envoi vocal → transcription + réponse du bot)
with tab3:
    st.header("☎️ Appel vocal")
    
    st.info("💡 Envoyez un message vocal : il est transcrit puis envoyé au chatbot. Même API que l’interface web (/chat/voice). **2 secondes de silence** = fin d’enregistrement sur le micro. Sur le chat web : *parler fort = interrompre Pepper*.")
    
    if "voice_session_id" not in st.session_state:
        st.session_state.voice_session_id = None
    if "voice_history" not in st.session_state:
        st.session_state.voice_history = []
    
    for msg in st.session_state.voice_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    col_up, col_rec = st.columns(2)
    with col_up:
        voice_file = st.file_uploader(
            "Ou déposer un fichier vocal (WAV, WebM, MP4…)",
            type=["wav", "webm", "mp4", "ogg", "m4a", "mp3"],
            key="voice_upload",
            help="Même formats que le micro du navigateur."
        )
    with col_rec:
        st.caption("Enregistrement (micro du serveur)")
        do_record = st.button("🎙️ Enregistrer puis envoyer (2 s silence = stop)", key="voice_record_btn")
    
    send_audio = None
    if voice_file is not None:
        send_audio = voice_file
    if do_record:
        with st.spinner("🎤 Enregistrement… Parlez, 2 s de silence = arrêt."):
            rec_result = record_audio()
        if rec_result and "error" not in rec_result and rec_result.get("file"):
            import io
            script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            full_path = os.path.join(script_dir, rec_result["file"])
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    send_audio = io.BytesIO(f.read())
                    send_audio.name = os.path.basename(full_path)
    
    if send_audio is not None:
        send_audio.seek(0)
        with st.spinner("⏳ Transcription et réponse du bot…"):
            out = chat_voice(send_audio, session_id=st.session_state.voice_session_id)
        if out.get("error"):
            st.error(f"❌ {out['error']}")
        else:
            if out.get("session_id"):
                st.session_state.voice_session_id = out["session_id"]
            transcript = (out.get("transcript") or "").strip()
            response = (out.get("response") or "").strip()
            if transcript:
                st.session_state.voice_history.append({"role": "user", "content": f"🎤 {transcript}"})
            if response:
                st.session_state.voice_history.append({"role": "assistant", "content": response})
            if transcript or response:
                st.rerun()
            elif not transcript:
                st.warning("Aucune parole détectée. Parlez plus fort ou plus près du micro.")
    
    if st.button("🗑️ Effacer l’historique vocal", key="clear_voice_hist"):
        st.session_state.voice_history = []
        st.session_state.voice_session_id = None
        st.rerun()

# Tab 4: Enregistrement
with tab4:
    st.header("🔴 Enregistrement Audio")
    
    st.warning("⚠️ **Note:** Cette fonctionnalité nécessite un microphone connecté (serveur) et des permissions appropriées.")
    
    st.info("💡 Cliquez pour démarrer l’enregistrement. L’arrêt est automatique après **2 secondes de silence**.")
    st.caption("Permet des pauses naturelles ; arrêt seulement après 2 secondes de silence complet.")
    
    if st.button("🎙️ Démarrer l'Enregistrement", type="primary", use_container_width=True, key="rec_btn"):
        with st.spinner("🎤 Enregistrement… Parlez. Arrêt après 2 secondes de silence."):
            result = record_audio()
        
        if result and "error" in result:
            st.error(f"❌ Erreur: {result['error']}")
        elif result:
            message = result.get('message', '')
            file_path = result.get('file', '')
            
            st.success(f"✅ {message}")
            
            if file_path:
                st.info(f"📁 Fichier sauvegardé: `{file_path}`")
                st.success("🎉 Enregistrement terminé.")
                
                if st.button("📝 Transcrire cet enregistrement", key="transcribe_recorded"):
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
                                        st.text_area("Texte transcrit:", value=text, height=200, key="rec_transcript")
                                    else:
                                        st.warning("⚠️ Aucun texte n'a été transcrit.")
                                else:
                                    err = transcribe_result.get('error', 'Erreur') if transcribe_result else 'Aucune réponse'
                                    st.error(f"❌ {err}")
                        else:
                            st.error(f"❌ Fichier non trouvé: {full_path}")
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")
            else:
                st.warning("⚠️ Aucun fichier retourné.")

# Tab 5: Heure et Lieu
with tab5:
    st.header("📍 Heure et Date Actuelles")
    
    st.info("💡 Récupère l'heure et la date actuelles du système.")
    
    if st.button("🕐 Récupérer l'heure et la date", type="primary", use_container_width=True):
        result = get_location()
        
        if "error" in result:
            st.error(f"❌ Erreur: {result['error']}")
        else:
            st.success("✅ Information récupérée!")
            st.markdown(f"### {result}")

