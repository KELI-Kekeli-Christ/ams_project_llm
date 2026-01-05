"""
Page Streamlit pour configurer l'envoi d'emails au gestionnaire
"""
import streamlit as st
import sys
import os

# Ajouter le chemin parent pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_email_config, update_email_config, test_api_connection

st.set_page_config(
    page_title="Configuration Email",
    page_icon="📧",
    layout="wide"
)

st.title("📧 Configuration Email")
st.markdown("Configurez l'envoi automatique d'emails au gestionnaire lors des nouvelles réservations")

# Vérifier la connexion à l'API
if not test_api_connection():
    st.error(f"❌ Impossible de se connecter à l'API. Vérifiez que le serveur Flask est démarré sur {os.getenv('API_BASE_URL', 'http://localhost:5000')}")
    st.stop()

# Charger la configuration actuelle
st.subheader("⚙️ Configuration Actuelle")

try:
    config = get_email_config()
    
    if "error" in config:
        st.error(f"❌ Erreur lors du chargement de la configuration: {config['error']}")
        st.stop()
    
    # Afficher les informations actuelles
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Email du gestionnaire:** {config.get('manager_email', 'Non configuré')}")
        st.info(f"**Serveur SMTP:** {config.get('smtp_server', 'Non configuré')}")
        st.info(f"**Port SMTP:** {config.get('smtp_port', 'Non configuré')}")
    
    with col2:
        email_enabled = config.get('email_enabled', True)
        status = "🟢 Activé" if email_enabled else "🔴 Désactivé"
        st.info(f"**Statut:** {status}")
        
        password_configured = config.get('smtp_password_configured', False)
        password_status = "✅ Configuré" if password_configured else "❌ Non configuré"
        st.info(f"**Mot de passe SMTP:** {password_status}")
        
        smtp_username = config.get('smtp_username', '')
        username_status = "✅ Configuré" if smtp_username else "❌ Non configuré - OBLIGATOIRE"
        st.info(f"**Utilisateur SMTP:** {smtp_username if smtp_username else username_status}")
        
        # Afficher un avertissement si smtp_username est vide
        if not smtp_username:
            st.error("⚠️ **ATTENTION:** L'utilisateur SMTP n'est pas configuré ! Vous devez entrer votre adresse email (ex: votre.email@gmail.com) pour que l'envoi d'emails fonctionne.")
    
except Exception as e:
    st.error(f"❌ Erreur: {str(e)}")
    st.stop()

# Formulaire de configuration
st.subheader("🔧 Modifier la Configuration")
st.markdown("Modifiez les paramètres ci-dessous pour configurer l'envoi d'emails")

with st.form("email_config_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        new_manager_email = st.text_input(
            "📧 Email du gestionnaire",
            value=config.get('manager_email', 'christlearn834@gmail.com'),
            help="Adresse email qui recevra les notifications de nouvelles réservations",
            placeholder="exemple@email.com"
        )
        
        new_smtp_server = st.text_input(
            "🌐 Serveur SMTP",
            value=config.get('smtp_server', 'smtp.gmail.com'),
            help="Adresse du serveur SMTP (ex: smtp.gmail.com pour Gmail)",
            placeholder="smtp.gmail.com"
        )
        
        new_smtp_port = st.number_input(
            "🔌 Port SMTP",
            value=config.get('smtp_port', 587),
            min_value=1,
            max_value=65535,
            help="Port SMTP (587 pour TLS, 465 pour SSL)"
        )
    
    with col2:
        new_smtp_username = st.text_input(
            "👤 Utilisateur SMTP (OBLIGATOIRE)",
            value=config.get('smtp_username', ''),
            help="Nom d'utilisateur pour l'authentification SMTP (généralement votre adresse email complète, ex: votre.email@gmail.com)",
            placeholder="votre.email@gmail.com"
        )
        
        # Avertissement si smtp_username est vide
        if not new_smtp_username:
            st.warning("⚠️ **Important:** Vous devez configurer l'utilisateur SMTP (votre adresse email) pour que l'envoi d'emails fonctionne!")
        
        new_smtp_password = st.text_input(
            "🔐 Mot de passe SMTP",
            type="password",
            value="",
            help="Mot de passe SMTP ou 'App Password' pour Gmail. Laissez vide pour ne pas modifier le mot de passe actuel.",
            placeholder="Laissez vide pour ne pas modifier"
        )
        
        email_enabled_toggle = st.checkbox(
            "✅ Activer l'envoi d'emails",
            value=config.get('email_enabled', True),
            help="Active ou désactive l'envoi automatique d'emails lors des nouvelles réservations"
        )
    
    # Instructions
    st.markdown("---")
    st.markdown("### 📝 Instructions")
    
    with st.expander("ℹ️ Comment configurer Gmail", expanded=False):
        st.markdown("""
        Pour utiliser Gmail comme serveur SMTP :
        
        1. **Activer la validation en deux étapes** sur votre compte Google
        2. **Générer un mot de passe d'application** :
           - Allez dans votre compte Google → Sécurité
           - Sous "Connexion à Google", cliquez sur "Mots de passe des applications"
           - Générez un nouveau mot de passe pour "Courrier" et "Ordinateur"
           - Utilisez ce mot de passe (16 caractères) comme mot de passe SMTP
        
        3. **Configuration** :
           - Serveur SMTP: `smtp.gmail.com`
           - Port: `587` (TLS) ou `465` (SSL)
           - Utilisateur: Votre adresse Gmail complète
           - Mot de passe: Le mot de passe d'application généré
        """)
    
    with st.expander("ℹ️ Configuration pour autres serveurs", expanded=False):
        st.markdown("""
        **Outlook/Hotmail:**
        - Serveur: `smtp-mail.outlook.com`
        - Port: `587`
        
        **Yahoo:**
        - Serveur: `smtp.mail.yahoo.com`
        - Port: `587` ou `465`
        
        **Autre serveur SMTP:**
        - Contactez votre administrateur email pour les paramètres SMTP
        """)
    
    submitted = st.form_submit_button("💾 Enregistrer la Configuration", type="primary", use_container_width=True)
    
    if submitted:
        # Validation
        if not new_manager_email or '@' not in new_manager_email:
            st.error("❌ Veuillez entrer une adresse email valide pour le gestionnaire")
        elif not new_smtp_server:
            st.error("❌ Veuillez entrer un serveur SMTP")
        elif not new_smtp_username or '@' not in new_smtp_username:
            st.error("❌ Veuillez entrer une adresse email valide pour l'utilisateur SMTP (généralement votre adresse Gmail)")
        else:
            # Préparer la configuration
            update_data = {
                "manager_email": new_manager_email.strip(),
                "smtp_server": new_smtp_server.strip(),
                "smtp_port": int(new_smtp_port),
                "smtp_username": new_smtp_username.strip(),
                "email_enabled": email_enabled_toggle
            }
            
            # Ajouter le mot de passe seulement s'il a été fourni
            if new_smtp_password:
                update_data["smtp_password"] = new_smtp_password
            else:
                # Utiliser "*" pour indiquer qu'on ne veut pas le modifier
                update_data["smtp_password"] = "*"
            
            # Envoyer la mise à jour
            with st.spinner("⏳ Mise à jour de la configuration..."):
                result = update_email_config(update_data)
            
            if "error" in result:
                st.error(f"❌ Erreur lors de la mise à jour: {result['error']}")
            elif result.get("success"):
                st.success(f"✅ Configuration mise à jour avec succès !")
                st.success(f"📧 Les emails seront envoyés à: {result.get('manager_email', new_manager_email)}")
                st.rerun()
            else:
                st.error("❌ Échec de la mise à jour. Vérifiez les paramètres.")

# Section de test
st.markdown("---")
st.subheader("🧪 Test d'Envoi")

st.markdown("Pour tester la configuration email, créez une nouvelle réservation via l'interface ou le robot Pepper.")

if st.button("🔄 Recharger la Configuration", use_container_width=True):
    st.rerun()

