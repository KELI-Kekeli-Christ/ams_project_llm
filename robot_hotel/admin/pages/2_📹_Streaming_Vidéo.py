"""
Page de gestion du streaming vidéo en temps réel
"""
import streamlit as st
import time
import sys
import os

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    start_video_stream,
    stop_video_stream,
    get_latest_detections,
    test_api_connection,
    API_BASE_URL
)

st.set_page_config(page_title="Streaming Vidéo", page_icon="📹", layout="wide")

st.title("📹 Gestion du Streaming Vidéo en Temps Réel")

# Vérifier la connexion API
if not test_api_connection():
    st.error(f"❌ Impossible de se connecter à l'API. Vérifiez que le serveur Flask est démarré sur {API_BASE_URL}")
    st.info(f"💡 URL testée: {API_BASE_URL}/")
    st.stop()

# Initialiser l'état de la session
if 'streaming' not in st.session_state:
    st.session_state.streaming = False
if 'camera_index' not in st.session_state:
    st.session_state.camera_index = 0
if 'video_url' not in st.session_state:
    st.session_state.video_url = ""

# Section de configuration
st.header("⚙️ Configuration du Stream")

col1, col2 = st.columns(2)

with col1:
    camera_index = st.number_input(
        "Index de la caméra",
        min_value=0,
        max_value=10,
        value=st.session_state.camera_index,
        help="L'index de la caméra à utiliser (généralement 0 pour la webcam par défaut)"
    )
    st.session_state.camera_index = camera_index

with col2:
    use_video_url = st.checkbox("Utiliser une URL de flux vidéo (ex: Pepper)")
    if use_video_url:
        video_url = st.text_input(
            "URL du flux vidéo",
            value=st.session_state.video_url or "http://pepper.local:8080/video",
            placeholder="http://pepper.local:8080/video",
            help="URL du flux vidéo (pour robot Pepper par exemple)"
        )
        st.session_state.video_url = video_url if video_url else None
    else:
        st.session_state.video_url = None
        video_url = None

# Boutons de contrôle
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("▶️ Démarrer le Stream", type="primary", use_container_width=True):
        with st.spinner("⏳ Démarrage du stream..."):
            result = start_video_stream(
                camera_index=camera_index,
                video_url=video_url if use_video_url else None
            )
        
        if "error" in result:
            st.error(f"❌ Erreur: {result['error']}")
        elif result.get("success"):
            st.success(f"✅ {result.get('message', 'Stream démarré!')}")
            st.session_state.streaming = True

with col2:
    if st.button("⏹️ Arrêter le Stream", type="secondary", use_container_width=True):
        with st.spinner("⏳ Arrêt du stream..."):
            result = stop_video_stream()
        
        if "error" in result:
            st.error(f"❌ Erreur: {result['error']}")
        elif result.get("success"):
            st.success(f"✅ {result.get('message', 'Stream arrêté!')}")
            st.session_state.streaming = False

# Section de monitoring en temps réel
st.header("📊 Monitoring en Temps Réel")

if st.session_state.streaming:
    st.success("🟢 Stream actif")
    
    # Auto-refresh pour les détections
    auto_refresh = st.checkbox("🔄 Actualisation automatique", value=True)
    
    if auto_refresh:
        refresh_interval = st.slider(
            "Intervalle d'actualisation (secondes)",
            min_value=1,
            max_value=10,
            value=3,
            help="Fréquence de mise à jour des détections"
        )
    
    # Zone d'affichage des détections
    detection_placeholder = st.empty()
    
    # Bouton de rafraîchissement manuel
    if st.button("🔄 Actualiser maintenant"):
        st.rerun()
    
    # Fonction pour afficher les détections
    def display_detections():
        result = get_latest_detections()
        
        if "error" in result:
            with detection_placeholder.container():
                st.error(f"❌ Erreur: {result['error']}")
                if "No video stream is running" in result.get('error', ''):
                    st.session_state.streaming = False
        elif result.get("success"):
            with detection_placeholder.container():
                detections = result.get("detections", [])
                recognized_persons = result.get("recognized_persons", [])
                total_detected = result.get("total_detected", 0)
                total_recognized = result.get("total_recognized", 0)
                timestamp = result.get("timestamp", 0)
                
                # Convertir le timestamp en heure lisible
                from datetime import datetime
                if timestamp:
                    dt = datetime.fromtimestamp(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                else:
                    time_str = "N/A"
                
                # Métriques
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("👥 Personnes détectées", total_detected)
                with col2:
                    st.metric("✅ Personnes reconnues", total_recognized)
                with col3:
                    st.metric("🕐 Dernière mise à jour", time_str)
                
                # Personnes reconnues
                if recognized_persons:
                    st.success(f"🎯 **Personnes reconnues:** {', '.join(recognized_persons)}")
                else:
                    st.info("ℹ️ Aucune personne reconnue pour le moment.")
                
                # Détails des détections
                if detections:
                    st.subheader("📋 Détections en cours")
                    for idx, detection in enumerate(detections, 1):
                        name = detection.get('name', 'Unknown Person')
                        confidence = detection.get('confidence', 0)
                        recognized = detection.get('recognized', False)
                        
                        status_color = "🟢" if recognized else "🟡"
                        status_text = "✅ Reconnu" if recognized else "❓ Inconnu"
                        
                        with st.expander(f"{status_color} Détection #{idx}: {name} ({confidence:.1%}) - {status_text}"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write(f"**Confiance:** {confidence:.2%}")
                            with col2:
                                st.write(f"**Statut:** {status_text}")
                            with col3:
                                bbox = detection.get('bbox', {})
                                st.write(f"**Position:** ({bbox.get('x1', 0)}, {bbox.get('y1', 0)})")
                else:
                    st.info("📭 Aucune détection pour le moment.")
    
    # Afficher les détections
    display_detections()
    
    # Auto-refresh si activé
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
    
else:
    st.info("ℹ️ Le stream n'est pas actif. Cliquez sur 'Démarrer le Stream' pour commencer.")

# Instructions
with st.expander("ℹ️ Instructions"):
    st.markdown("""
    ### Comment utiliser le streaming vidéo:
    
    1. **Configuration:**
       - Pour une webcam locale, laissez l'index de caméra à 0
       - Pour un robot Pepper, cochez "Utiliser une URL de flux vidéo" et entrez l'URL du flux
    
    2. **Démarrer le stream:**
       - Cliquez sur "Démarrer le Stream"
       - Le système va commencer à détecter et reconnaître les visages en temps réel
    
    3. **Monitoring:**
       - Les détections sont affichées en temps réel
       - Activez l'actualisation automatique pour un suivi continu
       - Les personnes reconnues sont mises en évidence
    
    4. **Arrêter:**
       - Cliquez sur "Arrêter le Stream" quand vous avez terminé
    """)

