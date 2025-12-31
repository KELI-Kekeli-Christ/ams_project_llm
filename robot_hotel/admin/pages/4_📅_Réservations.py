"""
Page de gestion des réservations
"""
import streamlit as st
import sys
import os
import json
import time
import io
from PIL import Image

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    make_reservation,
    scan_qr_code,
    scan_qr_code_stream,
    start_qr_stream,
    stop_qr_stream,
    get_qr_stream_status,
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

# Section de vérification de réservation par QR code
st.divider()
st.header("🔍 Vérifier une Réservation (QR Code)")

# Initialiser l'état de session
if 'qr_scan_active' not in st.session_state:
    st.session_state.qr_scan_active = False
if 'qr_result' not in st.session_state:
    st.session_state.qr_result = None
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = 0
if 'use_backend_stream' not in st.session_state:
    st.session_state.use_backend_stream = False

# Option 1: Upload d'image statique
st.subheader("📸 Option 1: Téléverser une Image")
uploaded_image = st.file_uploader(
    "Choisir une image contenant le QR code",
    type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
    help="L'image doit contenir un QR code de réservation",
    key="qr_upload"
)

if uploaded_image is not None and uploaded_image.type.startswith('image/'):
    st.image(uploaded_image, caption="Image à analyser", width=300)
    
    if st.button("🔍 Scanner le QR Code", type="primary", use_container_width=True, key="scan_upload"):
        with st.spinner("⏳ Scan du QR code en cours... Détection et vérification."):
            uploaded_image.seek(0)
            result = scan_qr_code(uploaded_image)
        
        st.session_state.qr_result = result
        st.rerun()

# Option 2: Flux vidéo en temps réel avec détection automatique
st.divider()
st.subheader("📹 Option 2: Flux Vidéo en Temps Réel")

col1, col2 = st.columns([2, 1])

with col2:
    use_backend_stream = st.checkbox(
        "Utiliser le stream backend (flux continu)",
        help="Active le streaming vidéo continu côté serveur pour une détection automatique",
        key="use_backend_stream_check"
    )
    
    use_video_url = st.checkbox("Utiliser une URL de caméra", key="use_video_url")
    video_url = None
    if use_video_url:
        video_url = st.text_input(
            "URL de la caméra",
            placeholder="http://192.168.1.100:8080/video",
            help="Exemples: http://ip:port/video, rtsp://..., 0 pour caméra locale",
            key="video_url_input"
        )
        camera_index = st.number_input("Index caméra (si pas d'URL)", min_value=0, max_value=10, value=0, key="camera_index")

with col1:
    if use_backend_stream:
        if st.button("▶️ Démarrer le Stream Backend", type="primary", use_container_width=True, key="start_backend_stream"):
            with st.spinner("Démarrage du stream backend..."):
                result = start_qr_stream(video_url if use_video_url and video_url else None, camera_index if use_video_url else 0)
                if result.get("success"):
                    st.session_state.use_backend_stream = True
                    st.session_state.qr_scan_active = True
                    st.success("✅ Stream backend démarré!")
                    st.rerun()
                else:
                    st.error(f"❌ Erreur: {result.get('error', 'Erreur inconnue')}")
        
        if st.session_state.use_backend_stream:
            if st.button("⏹️ Arrêter le Stream Backend", type="secondary", use_container_width=True, key="stop_backend_stream"):
                stop_qr_stream()
                st.session_state.use_backend_stream = False
                st.session_state.qr_scan_active = False
                st.session_state.qr_result = None
                st.rerun()
    else:
        if st.button("▶️ Démarrer le Scan en Temps Réel", type="primary", use_container_width=True, key="start_scan"):
            st.session_state.qr_scan_active = True
            st.session_state.qr_result = None
            st.rerun()
        
        if st.session_state.qr_scan_active:
            if st.button("⏹️ Arrêter le Scan", type="secondary", use_container_width=True, key="stop_scan"):
                st.session_state.qr_scan_active = False
                st.session_state.qr_result = None
                st.rerun()

# Mode stream backend (flux continu côté serveur)
if st.session_state.use_backend_stream and st.session_state.qr_scan_active:
    st.info("🎥 **Mode Stream Backend Actif** - Le serveur analyse le flux vidéo en continu. Positionnez le QR code devant la caméra.")
    
    # Zone de statut
    status_placeholder = st.empty()
    result_placeholder = st.empty()
    
    # Vérifier le statut du stream en continu
    if 'last_status_check' not in st.session_state:
        st.session_state.last_status_check = 0
    if 'last_result' not in st.session_state:
        st.session_state.last_result = None
    
    current_time = time.time()
    # Vérifier le statut régulièrement (toutes les 0.5 secondes pour réactivité)
    should_check = current_time - st.session_state.last_status_check > 0.5
    
    if should_check or st.session_state.last_result is None:
        status_result = get_qr_stream_status()
        st.session_state.last_result = status_result
        st.session_state.last_status_check = current_time
    
    status_result = st.session_state.last_result
    is_active = status_result.get("active", False)
    stream_result = status_result.get("result")
    
    # Debug - afficher les informations
    with st.expander("🔧 Debug (statut)", expanded=False):
        st.json(status_result)
        st.write(f"Dernière vérification: {time.strftime('%H:%M:%S', time.localtime(st.session_state.last_status_check))}")
    
    # Vérifier si un QR code valide a été détecté
    if stream_result and stream_result.get("success"):
        # QR code valide détecté - arrêter et afficher
        if not st.session_state.qr_result or st.session_state.qr_result.get("qr_id") != stream_result.get("qr_id"):
            # Nouveau QR code détecté
            st.session_state.qr_result = stream_result
            st.session_state.use_backend_stream = False
            st.session_state.qr_scan_active = False
            status_placeholder.success("✅ QR Code détecté et validé!")
            st.balloons()
            time.sleep(0.3)  # Petite pause pour afficher le message
            st.rerun()
    elif not is_active and stream_result:
        # Stream arrêté mais pas de succès - peut être une erreur
        if stream_result.get("error"):
            error_msg = stream_result.get('error', 'Erreur inconnue')
            if "Impossible d'ouvrir" in error_msg:
                status_placeholder.error(f"❌ Erreur caméra: {error_msg}")
            else:
                status_placeholder.warning(f"⚠️ {error_msg}")
                if stream_result.get("qr_id"):
                    status_placeholder.info(f"QR Code détecté: `{stream_result.get('qr_id')}` mais invalide")
        else:
            status_placeholder.warning("⚠️ Stream arrêté sans résultat")
    elif is_active:
        # Stream actif - continuer le scan
        status_placeholder.info("🔍 Scan en cours... Analyse du flux vidéo en continu. Positionnez le QR code devant la caméra.")
        
        # Auto-refresh continu pour détecter rapidement les changements
        time.sleep(0.5)  # Petite pause avant le refresh
        st.rerun()
    else:
        status_placeholder.info("⏸️ Stream arrêté")

# Mode caméra Streamlit (détection frame par frame)
elif st.session_state.qr_scan_active and not st.session_state.use_backend_stream:
    st.info("🎥 **Mode Scan Actif** - Positionnez le QR code devant la caméra. La détection est automatique et en continu.")
    
    # Zone pour le flux vidéo
    video_container = st.container()
    
    with video_container:
        # Placeholder pour le statut de détection
        status_placeholder = st.empty()
        
        if use_video_url and video_url:
            status_placeholder.info(f"📡 Mode URL de caméra: `{video_url}`")
            st.info("💡 La détection se fera automatiquement sur les frames capturées.")
            camera_image = st.camera_input(
                "Flux vidéo - Détection automatique (utiliser aussi la caméra locale en complément)",
                help="Le QR code sera détecté automatiquement",
                key="qr_camera_stream"
            )
        else:
            camera_image = st.camera_input(
                "Flux vidéo - Détection automatique",
                help="Positionnez le QR code devant la caméra. La détection se fait automatiquement.",
                key="qr_camera_stream"
            )
        
        # Zone pour afficher les résultats de détection en temps réel
        detection_status = st.empty()
        
        # Détection automatique si une nouvelle image est capturée
        if camera_image is not None:
            current_time = time.time()
            # Scanner toutes les 0.3 secondes pour une détection fluide
            time_since_last_scan = current_time - st.session_state.last_scan_time
            
            if time_since_last_scan > 0.3:
                # Afficher le statut de scan
                with detection_status.container():
                    status_placeholder.info("🔍 Scan en cours... Analyse de la frame...")
                
                try:
                    camera_image.seek(0)
                    result = scan_qr_code_stream(camera_image, video_url if use_video_url else None)
                    
                    st.session_state.last_scan_time = current_time
                    
                    # Si un QR code est détecté
                    if result.get('detected', False):
                        if result.get('success', False):
                            # QR code valide détecté!
                            st.session_state.qr_result = result
                            st.session_state.qr_scan_active = False  # Arrêter le scan automatique après détection
                            status_placeholder.success("✅ QR Code détecté et validé!")
                            time.sleep(0.5)  # Petite pause pour afficher le message
                            st.rerun()
                        else:
                            # QR code détecté mais invalide
                            qr_id = result.get('qr_id', 'N/A')
                            error = result.get('error', 'Inconnu')
                            with detection_status.container():
                                status_placeholder.warning(f"⚠️ QR Code détecté mais invalide: `{qr_id}` - {error}")
                    else:
                        # Aucun QR code détecté dans cette frame
                        with detection_status.container():
                            status_placeholder.info("👀 Aucun QR code détecté... Continuez à positionner le QR code devant la caméra.")
                
                except Exception as e:
                    with detection_status.container():
                        status_placeholder.error(f"❌ Erreur lors du scan: {str(e)}")
        else:
            detection_status.info("📷 Activez la caméra pour commencer la détection automatique")

# Afficher les résultats
if st.session_state.qr_result is not None:
    st.divider()
    result = st.session_state.qr_result
    success = result.get('success', False)
    
    if not success:
        error = result.get('error', 'Erreur inconnue')
        qr_id = result.get('qr_id', 'N/A')
        
        st.error(f"❌ Erreur: {error}")
        if qr_id and qr_id != 'N/A':
            st.info(f"QR Code détecté: `{qr_id}` (mais invalide ou réservation non trouvée)")
    else:
        st.success("✅ QR Code scanné avec succès!")
        st.balloons()
        
        qr_id = result.get('qr_id', 'N/A')
        reservation = result.get('reservation', {})
        client = result.get('client', {})
        
        # Afficher le QR ID
        st.markdown(f"### 🆔 ID QR Code: `{qr_id}`")
        
        # Informations de réservation
        if reservation:
            st.subheader("📅 Informations de Réservation")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                **Détails:**
                - ID Réservation: `{reservation.get('id_res', 'N/A')}`
                - Type chambre: **{reservation.get('type_chambre', 'N/A').upper()}**
                - Statut: **{reservation.get('statut', 'N/A')}**
                """)
            
            with col2:
                st.markdown(f"""
                **Dates:**
                - Arrivée: **{reservation.get('date_arrivee', 'N/A')}**
                - Départ: **{reservation.get('date_depart', 'N/A')}**
                """)
        
        # Informations client
        if client:
            st.subheader("👤 Informations du Client")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                **Identité:**
                - Nom: **{client.get('nom', 'N/A')}**
                - Prénom: **{client.get('prenom', 'N/A')}**
                - ID Client: `{client.get('id_client', 'N/A')}`
                """)
            
            with col2:
                st.markdown(f"""
                **Historique:**
                - Nombre de visites: **{client.get('nb_visites', 0)}**
                - Dernière visite: {client.get('derniere_visite', 'N/A')}
                """)
        
        # Afficher le JSON complet en expander
        with st.expander("📋 Détails JSON complets"):
            st.json(result)
        
        # Bouton pour réinitialiser
        if st.button("🔄 Nouveau Scan", use_container_width=True, key="reset_scan"):
            st.session_state.qr_result = None
            st.session_state.qr_scan_active = False
            st.rerun()

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

