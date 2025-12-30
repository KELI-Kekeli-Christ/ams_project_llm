"""
Application Streamlit d'administration pour le système Robot Hotel
Interface complète pour tester et gérer toutes les fonctionnalités
"""
import streamlit as st
import sys
import os

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import test_api_connection, API_BASE_URL

# Configuration de la page
st.set_page_config(
    page_title="Robot Hotel Admin",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        padding: 20px;
    }
    .status-good {
        color: #28a745;
        font-weight: bold;
    }
    .status-bad {
        color: #dc3545;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x100?text=Robot+Hotel", width=200)
    st.title("🤖 Robot Hotel Admin")
    st.markdown("---")
    
    # Vérification de la connexion API
    st.subheader("🔌 État de l'API")
    api_status = test_api_connection()
    
    if api_status:
        st.success("✅ API Connectée")
        st.markdown('<p class="status-good">🟢 Système opérationnel</p>', unsafe_allow_html=True)
        # Afficher l'URL de l'API
        from utils import API_BASE_URL
        st.caption(f"📍 Connecté à: {API_BASE_URL}")
    else:
        st.error("❌ API Non connectée")
        st.markdown('<p class="status-bad">🔴 Vérifiez que le serveur Flask est démarré</p>', unsafe_allow_html=True)
        from utils import API_BASE_URL
        st.info(f"💡 Le serveur doit être accessible sur {API_BASE_URL}")
        with st.expander("🔧 Aide au débogage"):
            st.markdown(f"""
            **URL testée:** `{API_BASE_URL}/`
            
            **Vérifications à faire:**
            1. Le serveur Flask est-il démarré ? (`python main.py`)
            2. Le serveur écoute-t-il sur le bon port ? (par défaut 5000)
            3. Y a-t-il un firewall qui bloque la connexion ?
            4. L'URL est-elle correcte ? (actuellement: `{API_BASE_URL}`)
            
            **Pour changer l'URL de l'API:**
            - Définir la variable d'environnement: `export API_BASE_URL=http://votre-serveur:port`
            - Ou modifier `admin/utils.py` ligne 9
            """)
    
    st.markdown("---")
    
    # Navigation
    st.subheader("📋 Navigation")
    st.markdown("""
    Utilisez le menu de navigation à gauche pour accéder aux différentes pages:
    
    - 👤 **Gestion Visages** - Base de données des visages
    - 📹 **Streaming Vidéo** - Stream temps réel
    - 💬 **Chat et Audio** - Test du chatbot et transcription
    - 📅 **Réservations** - Gestion des réservations
    """)
    
    st.markdown("---")
    
    # Informations système
    st.subheader("ℹ️ Informations")
    st.markdown("""
    **Version:** 1.0.0  
    **API Base URL:** http://localhost:5000  
    **Swagger Docs:** http://localhost:5000/api-docs
    """)
    
    # Lien vers la documentation API
    if st.button("📚 Ouvrir la documentation API", use_container_width=True):
        st.markdown('<a href="http://localhost:5000/api-docs" target="_blank">Documentation Swagger</a>', unsafe_allow_html=True)

# Page principale
st.markdown('<h1 class="main-header">🤖 Robot Hotel - Administration</h1>', unsafe_allow_html=True)

st.markdown("---")

# Section de bienvenue
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("""
    ### 👋 Bienvenue dans l'interface d'administration
    
    Cette interface vous permet de gérer et tester toutes les fonctionnalités du système Robot Hotel.
    """)

# Statistiques et aperçu rapide
st.markdown("## 📊 Aperçu Rapide")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if api_status:
        st.metric("🔌 API", "Connectée", delta="OK", delta_color="normal")
    else:
        st.metric("🔌 API", "Déconnectée", delta="ERREUR", delta_color="inverse")

with col2:
    # Récupérer le nombre de personnes enregistrées
    if api_status:
        try:
            from utils import get_registered_persons
            result = get_registered_persons()
            if "error" not in result and result.get("success"):
                total_persons = result.get("total", 0)
                st.metric("👤 Personnes", total_persons, delta="Enregistrées", delta_color="off")
            else:
                st.metric("👤 Personnes", "N/A", delta="Erreur", delta_color="off")
        except:
            st.metric("👤 Personnes", "N/A", delta="Erreur", delta_color="off")
    else:
        st.metric("👤 Personnes", "N/A", delta="API offline", delta_color="off")

with col3:
    st.metric("🤖 Services", "5", delta="Actifs", delta_color="normal")

with col4:
    st.metric("📹 Streaming", "Disponible", delta="Prêt", delta_color="normal")

# Fonctionnalités principales
st.markdown("---")
st.markdown("## 🎯 Fonctionnalités Disponibles")

# Grille de fonctionnalités
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 👤 Gestion des Visages
    - ✅ Enregistrer de nouvelles personnes
    - ✅ Lister toutes les personnes enregistrées
    - ✅ Supprimer des personnes
    - ✅ Tester la détection faciale
    
    **[Accéder →](/1_👤_Gestion_Visages)**
    """)
    
    st.markdown("""
    ### 📹 Streaming Vidéo
    - ✅ Démarrer/arrêter le stream
    - ✅ Monitoring en temps réel
    - ✅ Détection et reconnaissance en direct
    - ✅ Support webcam et robot Pepper
    
    **[Accéder →](/2_📹_Streaming_Vidéo)**
    """)

with col2:
    st.markdown("""
    ### 💬 Chat et Audio
    - ✅ Tester le chatbot Llama 3
    - ✅ Transcrire des fichiers audio
    - ✅ Enregistrer de l'audio
    - ✅ Récupérer l'heure/date
    
    **[Accéder →](/3_💬_Chat_et_Audio)**
    """)
    
    st.markdown("""
    ### 📅 Réservations
    - ✅ Créer des réservations depuis audio
    - ✅ Transcription automatique
    - ✅ Extraction d'informations
    - ✅ Gestion complète
    
    **[Accéder →](/4_📅_Réservations)**
    """)

# Instructions rapides
st.markdown("---")
st.markdown("## 🚀 Démarrage Rapide")

with st.expander("📖 Guide de démarrage"):
    st.markdown("""
    ### Pour commencer:
    
    1. **Vérifier la connexion API**
       - Assurez-vous que le serveur Flask est démarré sur le port 5000
       - L'indicateur dans la barre latérale doit afficher "✅ API Connectée"
    
    2. **Gérer les visages**
       - Allez dans "Gestion Visages"
       - Enregistrez quelques personnes pour tester la reconnaissance
    
    3. **Tester le streaming**
       - Allez dans "Streaming Vidéo"
       - Démarrez le stream avec votre webcam
       - Observez les détections en temps réel
    
    4. **Tester le chat**
       - Allez dans "Chat et Audio"
       - Posez des questions au chatbot
       - Testez la transcription audio
    
    5. **Créer une réservation**
       - Allez dans "Réservations"
       - Téléchargez un fichier audio avec une demande de réservation
       - Observez l'extraction automatique des informations
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>🤖 Robot Hotel Admin Interface - Version 1.0.0</p>
    <p>Développé pour la gestion et le test du système Robot Hotel</p>
</div>
""", unsafe_allow_html=True)

