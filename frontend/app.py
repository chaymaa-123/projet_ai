import streamlit as st
import requests
from fpdf import FPDF

def markdown_to_pdf(md_text):
    class PDF(FPDF):
        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    lines = md_text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(4)
            continue
        
        # Nettoyage des caractères spéciaux non compatibles avec Helvetica standard (latin-1)
        line = line.replace("’", "'").replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
        line = line.encode("latin-1", errors="ignore").decode("latin-1")
        
        # En-têtes / Titres
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 8, line[2:].replace("**", "").replace("*", ""))
            pdf.ln(2)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 7, line[3:].replace("**", "").replace("*", ""))
            pdf.ln(2)
        elif line.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 6, line[4:].replace("**", "").replace("*", ""))
            pdf.ln(1)
        # Éléments de liste
        elif line.startswith("- ") or line.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            text = line[2:]
            pdf.write(5, "  - ")
            parts = text.split("**")
            for i, part in enumerate(parts):
                if i % 2 == 1:
                    pdf.set_font("Helvetica", "B", 10)
                else:
                    pdf.set_font("Helvetica", "", 10)
                pdf.write(5, part)
            pdf.ln(6)
        # Paragraphes normaux
        else:
            pdf.set_font("Helvetica", "", 10)
            parts = line.split("**")
            for i, part in enumerate(parts):
                if i % 2 == 1:
                    pdf.set_font("Helvetica", "B", 10)
                else:
                    pdf.set_font("Helvetica", "", 10)
                pdf.write(5, part)
            pdf.ln(6)
            
    return bytes(pdf.output())


# Configuration de la page Streamlit
st.set_page_config(page_title="Orientation Clinique IA", page_icon="🏥", layout="wide")

# URL de notre API Backend FastAPI
API_URL = "http://127.0.0.1:8000"

st.title("🏥 Système d'Orientation Clinique")
st.caption("Orientation Clinique Assistée par Intelligence Artificielle")

# --- BARRE LATÉRALE : CONFIGURATION ---
st.sidebar.header("👤 Profil Patient & Configuration")

# Formulaire d'insertion de patient (XAMPP / MySQL via MCP)
with st.sidebar.expander("➕ Enregistrer un nouveau patient", expanded=True):
    with st.form("form_ajout_patient"):
        new_id = st.text_input("ID Patient", value="PAT-002")
        new_nom = st.text_input("Nom Complet")
        new_antecedents = st.text_input("Antécédents (séparés par des virgules)")
        new_allergies = st.text_input("Allergies")
        new_traitements = st.text_input("Traitements actuels")
        
        submitted = st.form_submit_button("Enregistrer un nouveau patient")
        
        if submitted:
            if new_nom and new_id:
                with st.spinner("Enregistrement du patient..."):
                    try:
                        res = requests.post(f"{API_URL}/patients/add", json={
                            "patient_id": new_id,
                            "nom": new_nom,
                            "antecedents": new_antecedents,
                            "allergies": new_allergies,
                            "traitements": new_traitements
                        })
                        st.success("Patient enregistré avec succès !")
                    except Exception as e:
                        st.error("Erreur lors de l'enregistrement.")
            else:
                st.error("Le nom et l'ID sont obligatoires.")

# Sélection dynamique du patient depuis la base de données
try:
    res_patients = requests.get(f"{API_URL}/patients")
    if res_patients.status_code == 200:
        liste_patients = res_patients.json()
        options_patients = [f"{p['patient_id']} ({p['nom']})" for p in liste_patients]
    else:
        options_patients = ["PAT-001 (Jean Dupont)", "PAT-002 (Chaymaa Alami)", "PAT-003 (Youssef Benani)"]
except Exception:
    options_patients = ["PAT-001 (Jean Dupont)", "PAT-002 (Chaymaa Alami)", "PAT-003 (Youssef Benani)"]

patient_selectionne = st.sidebar.selectbox(
    "Choisir le patient pour la consultation :",
    options_patients
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
            st.sidebar.success("Consultation démarrée !")
    except Exception:
        st.sidebar.error("Impossible de démarrer la consultation.")

# --- ZONE PRINCIPALE : LES ÉCRANS ---

if st.session_state.status == "initial":
    st.info("👋 Veuillez démarrer une consultation depuis la barre latérale gauche pour commencer la collecte des symptômes.")

# ÉCRAN 1 & 2 : DISCUSSION (Collecte des symptômes)
elif st.session_state.status == "en_collecte":
    st.subheader("💬 Échange avec le Patient (Collecte des symptômes)")
    
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
        with st.spinner("Analyse clinique de vos réponses en cours..."):
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
    # --- SÉCURISATION DE LA REQUÊTE ---
    try:
        res = requests.get(f"{API_URL}/consultation/{st.session_state.thread_id}")
        
        if res.status_code == 200:
            state_data = res.json()
            is_urgent = state_data.get("is_urgent", False)
            
            if is_urgent:
                st.error("🚨 ALERTE : Cas d'extrême urgence détecté ! Le questionnaire a été immédiatement interrompu. Veuillez orienter le patient d'urgence.")
            else:
                st.warning("⚠️ Collecte préliminaire terminée. En attente de la validation et des directives du médecin.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 📋 Synthèse Préliminaire (Générée par l'IA)")
                st.info(state_data.get("diagnostic_summary", "Aucune synthèse."))
                st.markdown("### 🛑 Soins Intermédiaires Proposés")
                st.text(state_data.get("interim_care", "Aucun soin."))
                
            with col2:
                st.markdown("### 🩺 Directives et Prescription du Médecin")
                prescription = st.text_area(
                    "Saisissez les directives thérapeutiques officielles :"
                )
                
                if st.button("✅ Valider et finaliser la consultation"):
                    with st.spinner("Enregistrement des directives en cours..."):
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
    st.success("🎉 Consultation complétée ! La fiche de synthèse finale est disponible.")
    
    res = requests.get(f"{API_URL}/consultation/{st.session_state.thread_id}/report")
    report_data = res.json()
    
    final_report_text = report_data.get("final_report", "Rapport introuvable.")
    st.markdown(final_report_text)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        try:
            pdf_data = markdown_to_pdf(final_report_text)
            st.download_button(
                label="💾 Télécharger le rapport médical (PDF)",
                data=pdf_data,
                file_name=f"rapport_medical_{patient_id}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erreur lors de la génération du PDF : {e}")
        
    with col2:
        if st.button("🔄 Commencer une nouvelle consultation patient"):
            st.session_state.status = "initial"
            st.session_state.thread_id = None
            st.rerun()