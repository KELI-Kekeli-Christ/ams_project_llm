"""
Page de gestion de la base de données des visages
"""
import streamlit as st
import sys
import os

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    get_registered_persons,
    register_person,
    delete_person,
    detect_faces,
    test_api_connection,
    API_BASE_URL
)

st.set_page_config(page_title="Gestion des Visages", page_icon="👤", layout="wide")

st.title("👤 Gestion de la Base de Données des Visages")

# Vérifier la connexion API
if not test_api_connection():
    st.error(f"❌ Impossible de se connecter à l'API. Vérifiez que le serveur Flask est démarré sur {API_BASE_URL}")
    st.info(f"💡 URL testée: {API_BASE_URL}/")
    st.stop()

# Tabs pour organiser les fonctionnalités
tab1, tab2, tab3, tab4 = st.tabs(["📋 Liste des Personnes", "➕ Enregistrer une Personne", "🗑️ Supprimer une Personne", "🔍 Tester la Détection"])

# Tab 1: Liste des personnes
with tab1:
    st.header("📋 Liste des Personnes Enregistrées")
    
    if st.button("🔄 Actualiser la Liste", use_container_width=True):
        st.rerun()
    
    result = get_registered_persons()
    
    if "error" in result:
        st.error(f"❌ Erreur: {result['error']}")
    elif result.get("success"):
        persons = result.get("persons", [])
        total = result.get("total", 0)
        
        if total == 0:
            st.info("📭 Aucune personne enregistrée dans la base de données.")
        else:
            st.success(f"✅ {total} personne(s) enregistrée(s)")
            
            # Afficher la liste
            cols = st.columns(3)
            for idx, person in enumerate(persons):
                with cols[idx % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div style="
                            border: 2px solid #4CAF50;
                            border-radius: 10px;
                            padding: 15px;
                            margin: 10px 0;
                            background-color: #f0f9f4;
                        ">
                            <h3 style="margin: 0; color: #2E7D32;">👤 {person}</h3>
                        </div>
                        """, unsafe_allow_html=True)

# Tab 2: Enregistrer une personne
with tab2:
    st.header("➕ Enregistrer une Nouvelle Personne")
    
    st.info("💡 **Instructions:** Téléchargez une image contenant un seul visage de la personne à enregistrer.")
    
    uploaded_file = st.file_uploader(
        "Choisir une image",
        type=['jpg', 'jpeg', 'png', 'bmp'],
        help="L'image doit contenir un seul visage clairement visible"
    )
    
    person_name = st.text_input(
        "Nom de la personne",
        placeholder="Ex: Jean Dupont",
        help="Le nom sera utilisé pour identifier cette personne"
    )
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Image téléchargée", width=300)
        
        if st.button("💾 Enregistrer cette Personne", type="primary", use_container_width=True):
            if not person_name or not person_name.strip():
                st.error("❌ Veuillez entrer un nom pour la personne.")
            else:
                with st.spinner("⏳ Enregistrement en cours..."):
                    # Réinitialiser le pointeur du fichier
                    uploaded_file.seek(0)
                    result = register_person(uploaded_file, person_name.strip())
                
                if "error" in result:
                    st.error(f"❌ Erreur: {result['error']}")
                elif result.get("success"):
                    st.success(f"✅ {result.get('message', 'Personne enregistrée avec succès!')}")
                    st.balloons()
                    st.info(f"📊 Total de personnes enregistrées: {result.get('total_registered', 0)}")
                    # Réinitialiser le formulaire
                    st.rerun()

# Tab 3: Supprimer une personne
with tab3:
    st.header("🗑️ Supprimer une Personne")
    
    st.warning("⚠️ **Attention:** Cette action est irréversible!")
    
    result = get_registered_persons()
    
    if "error" in result:
        st.error(f"❌ Erreur: {result['error']}")
    elif result.get("success"):
        persons = result.get("persons", [])
        
        if len(persons) == 0:
            st.info("📭 Aucune personne à supprimer.")
        else:
            selected_person = st.selectbox(
                "Sélectionner la personne à supprimer",
                persons,
                help="Choisissez une personne de la liste"
            )
            
            if st.button("🗑️ Supprimer cette Personne", type="primary", use_container_width=True):
                if selected_person:
                    with st.spinner("⏳ Suppression en cours..."):
                        result_delete = delete_person(selected_person)
                    
                    if "error" in result_delete:
                        st.error(f"❌ Erreur: {result_delete['error']}")
                    elif result_delete.get("success"):
                        st.success(f"✅ {result_delete.get('message', 'Personne supprimée avec succès!')}")
                        st.info(f"📊 Total de personnes restantes: {result_delete.get('total_registered', 0)}")
                        st.rerun()

# Tab 4: Tester la détection
with tab4:
    st.header("🔍 Tester la Détection de Visages")
    
    st.info("💡 **Test:** Téléchargez une image pour tester la détection et la reconnaissance faciale.")
    
    test_file = st.file_uploader(
        "Choisir une image à analyser",
        type=['jpg', 'jpeg', 'png', 'bmp'],
        key="test_detection",
        help="L'image sera analysée pour détecter et identifier les visages"
    )
    
    if test_file is not None:
        st.image(test_file, caption="Image à analyser", width=400)
        
        if st.button("🔍 Analyser l'Image", type="primary", use_container_width=True):
            with st.spinner("⏳ Analyse en cours... Cela peut prendre quelques secondes."):
                test_file.seek(0)
                result = detect_faces(test_file)
            
            if "error" in result:
                st.error(f"❌ Erreur: {result['error']}")
            elif result.get("success"):
                total_detected = result.get("total_detected", 0)
                total_recognized = result.get("total_recognized", 0)
                detections = result.get("detections", [])
                recognized = result.get("recognized_persons", [])
                
                st.success(f"✅ Analyse terminée!")
                
                # Statistiques
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("👥 Personnes détectées", total_detected)
                with col2:
                    st.metric("✅ Personnes reconnues", total_recognized)
                
                # Liste des personnes reconnues
                if recognized:
                    st.success(f"🎯 Personnes reconnues: {', '.join(recognized)}")
                else:
                    st.info("ℹ️ Aucune personne reconnue dans cette image.")
                
                # Détails des détections
                if detections:
                    st.subheader("📋 Détails des Détections")
                    for idx, detection in enumerate(detections, 1):
                        with st.expander(f"Détection #{idx}: {detection.get('name', 'Unknown')}"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write(f"**Confiance:** {detection.get('confidence', 0):.2%}")
                            with col2:
                                st.write(f"**Reconnue:** {'✅ Oui' if detection.get('recognized') else '❌ Non'}")
                            with col3:
                                bbox = detection.get('bbox', {})
                                st.write(f"**Position:** ({bbox.get('x1', 0)}, {bbox.get('y1', 0)})")
                else:
                    st.warning("⚠️ Aucune personne détectée dans l'image.")

