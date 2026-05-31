import streamlit as st
import requests

# Configuration de la page Streamlit
st.set_page_config(page_title="Orientation Clinique IA", page_icon="🏥", layout="wide")

# URL de notre API Backend FastAPI
API_URL = "http://127.0.0.1:8000"

st.title("🏥 Système d'Orientation Clinique Multi-Agents")
st.caption("Prototype Académique - Architecture LangGraph & MCP")

# --- BARRE LATÉRALE : CONFIGURATION ---
st.sidebar.header("👤 Profil Patient & Configuration")

# Formulaire d'insertion de patient (XAMPP / MySQL via MCP)
with st.sidebar.expander("➕ Intégrer un nouveau patient", expanded=True):
    with st.form("form_ajout_patient"):
        new_id = st.text_input("ID Patient", value="PAT-002")
        new_nom = st.text_input("Nom Complet")
        new_antecedents = st.text_input("Antécédents (séparés par des virgules)")
        new_allergies = st.text_input("Allergies")
        new_traitements = st.text_input("Traitements actuels")
        
        submitted = st.form_submit_button("Enregistrer dans la DB")
        
        if submitted:
            if new_nom and new_id:
                with st.spinner("Ajout dans la base MySQL (MCP)..."):
                    try:
                        res = requests.post(f"{API_URL}/patients/add", json={
                            "patient_id": new_id,
                            "nom": new_nom,
                            "antecedents": new_antecedents,
                            "allergies": new_allergies,
                            "traitements": new_traitements
                        })
                        st.success(f"Réponse DB : {res.json().get('message', '')}")
                    except Exception as e:
                        st.error("Erreur de connexion à l'API.")
            else:
                st.error("Le nom et l'ID sont obligatoires.")

# Sélection du patient pour la démo
patient_selectionne = st.sidebar.selectbox(
    "Choisir le patient pour la consultation :",
    ["PAT-001 (Jean Dupont)", f"{new_id} ({new_nom})" if new_nom else "Aucun autre patient"]
)
patient_id = patient_selectionne.split(" ")[0]

# --- INITIALISATION DE LA SESSION ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "status" not in st.session_state:
    st.session_state.status = "initial"

if st.sidebar.button("🚀 Démarrer une nouvelle consultation"):
    try:
        res = requests.post(f"{API_URL}/sessions/start", json={"patient_id": patient_id})
        if res.status_code == 200:
            st.session_state.thread_id = res.json()["thread_id"]
            st.session_state.messages = []
            st.session_state.status = "en_collecte"
            st.sidebar.success(f"Session initialisée ! ID: {st.session_state.thread_id[:8]}")
    except Exception:
        st.sidebar.error("Impossible de joindre l'API FastAPI. Vérifie qu'elle tourne sur le port 8000.")

# --- ZONE PRINCIPALE : LES ÉCRANS ---

if st.session_state.status == "initial":
    st.info("👋 Veuillez initialiser une consultation depuis la barre latérale gauche pour commencer la collecte des symptômes.")

# ÉCRAN 1 & 2 : DISCUSSION (Collecte des symptômes)
elif st.session_state.status == "en_collecte":
    st.subheader("💬 Échange avec le Patient (Collecte des symptômes - Max 5 questions)")
    
    # Affichage de l'historique des messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["text"])
            
    # Input pour le message du patient
    if prompt := st.chat_input("Décrivez vos symptômes ici..."):
        st.session_state.messages.append({"role": "user", "text": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        # Appel de l'API pour envoyer le message au graphe LangGraph
        with st.spinner("L'agent clinique analyse vos réponses..."):
            try:
                res = requests.post(f"{API_URL}/consultation/start", json={
                    "thread_id": st.session_state.thread_id,
                    "message": prompt
                })
                if res.status_code == 200:
                    # On récupère l'état complet à jour depuis le backend
                    res_status = requests.get(f"{API_URL}/consultation/{st.session_state.thread_id}")
                    if res_status.status_code == 200:
                        status_data = res_status.json()
                        st.session_state.status = status_data["status"]
                        st.session_state.messages = status_data["messages_history"]
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur de communication : {e}")

# ÉCRAN 3 : REVUE DU MÉDECIN (Human-in-the-Loop)
elif st.session_state.status == "en_attente_medecin":
    st.warning("⚠️ Le système a atteint la limite de collecte. Le graphe LangGraph est actuellement en PAUSE (Interruption Clinique).")
    
    # --- SÉCURISATION DE LA REQUÊTE ---
    try:
        res = requests.get(f"{API_URL}/consultation/{st.session_state.thread_id}")
        
        if res.status_code == 200:
            state_data = res.json()
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 📋 Synthèse Préliminaire (Générée par l'IA)")
                st.info(state_data.get("diagnostic_summary", "Aucune synthèse."))
                st.markdown("### 🛑 Soins Intermédiaires Proposés")
                st.text(state_data.get("interim_care", "Aucun soin."))
                
            with col2:
                st.markdown("### 🩺 Décision du Médecin Senior (Validation Humaine)")
                prescription = st.text_area(
                    "Saisissez vos directives thérapeutiques officielles (Validation MCP automatique) :"
                )
                
                if st.button("🚫 Valider le traitement et relancer le Graphe"):
                    with st.spinner("Injection du traitement et relance du workflow..."):
                        res_resume = requests.post(f"{API_URL}/consultation/resume", json={
                            "thread_id": st.session_state.thread_id,
                            "physician_treatment": prescription
                        })
                        if res_resume.status_code == 200:
                            st.session_state.status = "termine"
                            st.rerun()
                        else:
                            st.error(f"Erreur lors de la reprise : {res_resume.text}")
        else:
            # Si FastAPI renvoie une erreur (ex: 500), on affiche le texte brut de l'erreur au lieu de crash
            st.error(f"Le serveur backend a renvoyé une erreur (Code {res.status_code}).")
            st.code(res.text) # Ceci va t'afficher la vraie erreur (ex: XAMPP déconnecté)
            
            if st.button("🔄 Recommencer"):
                st.session_state.status = "initial"
                st.rerun()
                
    except Exception as e:
        st.error(f"Impossible de se connecter au serveur backend : {e}")
# ÉCRAN 4 : RAPPORT FINAL
elif st.session_state.status == "termine":
    st.success("🎉 Consultation complétée ! Le Report Agent a compilé la fiche finale.")
    
    res = requests.get(f"{API_URL}/consultation/{st.session_state.thread_id}/report")
    report_data = res.json()
    
    final_report_text = report_data.get("final_report", "Rapport introuvable.")
    st.markdown(final_report_text)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="💾 Télécharger le rapport médical",
            data=final_report_text,
            file_name=f"rapport_medical_{patient_id}.md",
            mime="text/markdown"
        )
        
    with col2:
        if st.button("🔄 Commencer une nouvelle consultation patient"):
            st.session_state.status = "initial"
            st.session_state.thread_id = None
            st.rerun()