import streamlit as st
import requests
import json
import os
import sys
from dotenv import load_dotenv

# Charger automatiquement le fichier .env
load_dotenv()

# Ajout du chemin parent pour pouvoir importer localement LangGraph si le backend n'est pas lancé
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Tenter d'importer directement le graph pour un repli autonome (Fallback local)
try:
    from backend.app.graph import graph
    from langchain_core.messages import HumanMessage, AIMessage
    LOCAL_GRAPH_AVAILABLE = True
except Exception as e:
    LOCAL_GRAPH_AVAILABLE = False

# Configuration de la page Streamlit (Thème médical premium)
st.set_page_config(
    page_title="Hôpital Virtuel - Orientation Multi-Agents",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injection de styles CSS personnalisés pour une esthétique exceptionnelle (Aesthetics)
st.markdown("""
<style>
    /* Import de la police premium Outfit depuis Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* En-tête avec dégradé subtil et effet glassmorphism */
    .clinical-header {
        background: linear-gradient(135deg, rgba(15, 32, 67, 0.95) 0%, rgba(27, 75, 114, 0.9) 100%);
        padding: 30px;
        border-radius: 20px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Cartes d'information avec micro-animations */
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        border-left: 6px solid #1e88e5;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
    }
    
    /* Badges d'état pour les agents */
    .agent-badge {
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 600;
        display: inline-block;
        margin: 5px;
    }
    
    .agent-active {
        background-color: #e3f2fd;
        color: #0d47a1;
        border: 1px solid #90caf9;
        animation: pulse 2s infinite;
    }
    
    .agent-completed {
        background-color: #e8f5e9;
        color: #1b5e20;
        border: 1px solid #a5d6a7;
    }
    
    .agent-pending {
        background-color: #f5f5f5;
        color: #757575;
        border: 1px solid #e0e0e0;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.03); }
        100% { transform: scale(1); }
    }
    
    /* Styles des bulles de chat personnalisées */
    .chat-bubble-patient {
        background-color: #f1f3f9;
        color: #1e293b;
        padding: 15px 20px;
        border-radius: 18px 18px 0px 18px;
        margin-bottom: 15px;
        border: 1px solid #e2e8f0;
    }
    
    .chat-bubble-agent {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        color: #0f172a;
        padding: 18px 22px;
        border-radius: 18px 18px 18px 0px;
        margin-bottom: 18px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        border: 1px solid #e2e8f0;
        border-left: 5px solid #10b981;
    }
    
    .agent-title {
        font-weight: 700;
        color: #0d9488;
        font-size: 0.9em;
        text-transform: uppercase;
        margin-bottom: 5px;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# INITIALISATION DES VARIABLES DE SESSION
# ----------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "next_step" not in st.session_state:
    st.session_state.next_step = "diagnostic_agent"
if "question_count" not in st.session_state:
    st.session_state.question_count = 0
if "interim_care" not in st.session_state:
    st.session_state.interim_care = ""
if "diagnostic_summary" not in st.session_state:
    st.session_state.diagnostic_summary = ""
if "physician_treatment" not in st.session_state:
    st.session_state.physician_treatment = ""
if "final_report" not in st.session_state:
    st.session_state.final_report = ""

# ----------------------------------------------------
# BARRE LATÉRALE - CONFIGURATION & PROFIL PATIENT
# ----------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/809/809957.png", width=80)
    st.title("Clinique Connectée")
    st.caption("Orientation Clinique Multi-Agents")
    
    st.markdown("---")
    
    # 1. Sélection du profil patient pour démonstration
    st.subheader("👤 Profil Patient Simulé")
    patient_choice = st.selectbox(
        "Sélectionner un profil de test :",
        ["Visiteur Anonyme", "Jean Dupont (PAT-001)", "Marie Martin (PAT-002)"]
    )
    
    patient_id = None
    if "PAT-001" in patient_choice:
        patient_id = "PAT-001"
        st.info("💡 Hypertension connue, Allergique à la Pénicilline.")
    elif "PAT-002" in patient_choice:
        patient_id = "PAT-002"
        st.info("💡 Hypothyroïdie, Allergique à l'Aspirine.")
    else:
        st.info("💡 Patient générique (aucune allergie ou antécédent répertorié).")
        
    st.markdown("---")
    
    # 2. Configuration des clés d'API (Optionnel)
    st.subheader("🔑 Clés d'API Modèles")
    openai_key = st.text_input("OpenAI API Key :", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    gemini_key = st.text_input("Gemini API Key :", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    
    # Mettre à jour les variables d'environnement au besoin
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
    if gemini_key:
        os.environ["GEMINI_API_KEY"] = gemini_key
        
    st.markdown("---")
    
    # 3. Mode de communication
    st.subheader("⚙️ Mode de Connexion")
    conn_mode = st.radio("Se connecter via :", ["API FastAPI (Port 8000)", "Moteur local (Autonome)"])
    
    # 4. Actions système
    if st.button("🔄 Réinitialiser le dossier", use_container_width=True):
        st.session_state.messages = []
        st.session_state.next_step = "diagnostic_agent"
        st.session_state.question_count = 0
        st.session_state.interim_care = ""
        st.session_state.diagnostic_summary = ""
        st.session_state.physician_treatment = ""
        st.session_state.final_report = ""
        st.rerun()

# ----------------------------------------------------
# EN-TÊTE PRINCIPAL DE L'APPLICATION
# ----------------------------------------------------
st.markdown("""
<div class="clinical-header">
    <h1 style="margin: 0; color: white; font-size: 2.3em; font-weight: 700;">🏥 Espace d'Orientation Médicale Multi-Agents</h1>
    <p style="margin: 5px 0 0 0; color: #cbd5e1; font-size: 1.1em; font-weight: 300;">
        Système d'aide au diagnostic clinique supervisé en temps réel avec le protocole LangGraph et MCP.
    </p>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# VISUALISATION DE LA TIMELINE DES AGENTS (Workflow progression)
# ----------------------------------------------------
st.subheader("🤖 Suivi du Graphe d'Agents en Temps Réel")

# Définition des états visuels
current_step = st.session_state.next_step

status_diag = "agent-active" if current_step == "diagnostic_agent" else (
    "agent-completed" if st.session_state.diagnostic_summary else "agent-pending"
)
status_phys = "agent-active" if current_step == "physician_review" else (
    "agent-completed" if st.session_state.physician_treatment else "agent-pending"
)
status_repr = "agent-active" if current_step == "report_agent" else (
    "agent-completed" if st.session_state.final_report else "agent-pending"
)
status_fin = "agent-completed" if current_step == "FINISH" else "agent-pending"

cols = st.columns(4)
with cols[0]:
    st.markdown(f'<div class="metric-card"><span class="agent-badge {status_diag}">1. Diagnostic Agent</span><br/><small>Recueil des symptômes et antécédents</small></div>', unsafe_allow_html=True)
with cols[1]:
    st.markdown(f'<div class="metric-card"><span class="agent-badge {status_phys}">2. Physician Review</span><br/><small>Validation clinique senior & directives MCP</small></div>', unsafe_allow_html=True)
with cols[2]:
    st.markdown(f'<div class="metric-card"><span class="agent-badge {status_repr}">3. Report Agent</span><br/><small>Rédaction de la synthèse finale</small></div>', unsafe_allow_html=True)
with cols[3]:
    st.markdown(f'<div class="metric-card"><span class="agent-badge {status_fin}">4. FINISH</span><br/><small>Rapport clinique validé</small></div>', unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# Disposition principale : Chat (gauche) | Dossier Médical & État du Graphe (droite)
chat_col, data_col = st.columns([3, 2])

# ----------------------------------------------------
# COLONNE DE CHAT INTERACTIF
# ----------------------------------------------------
with chat_col:
    st.subheader("💬 Dialogue d'Orientation")
    
    # Affichage de l'historique des messages
    chat_container = st.container(height=450)
    with chat_container:
        if not st.session_state.messages:
            st.markdown(
                '<div class="chat-bubble-agent"><div class="agent-title">Accueil Clinique</div>'
                'Bonjour ! Je suis le système d\'orientation automatisé. '
                'Décrivez-moi précisément les symptômes qui vous amènent aujourd\'hui '
                '*(par exemple: "J\'ai de la fièvre et des frissons depuis hier matin")* et laissez l\'équipe '
                'médicale virtuelle analyser votre situation.</div>',
                unsafe_allow_html=True
            )
        else:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="chat-bubble-patient"><b>Vous :</b><br/>{msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="chat-bubble-agent">'
                        f'<div class="agent-title">🤖 {msg["sender"]}</div>'
                        f'{msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                    
    # Saisie utilisateur
    user_input = st.chat_input("Décrivez vos symptômes ici...")
    
    if user_input:
        # 1. Ajouter le message de l'utilisateur à la session
        st.session_state.messages.append({"role": "user", "sender": "Patient", "content": user_input})
        st.rerun()

# ----------------------------------------------------
# BOUTON DE DÉCLENCHEMENT DE L'ANALYSE PAR LES AGENTS
# ----------------------------------------------------
# On exécute le flux d'analyse dès qu'un nouveau message utilisateur est ajouté en fin de liste
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with chat_col:
        with st.spinner("L'équipe médicale virtuelle analyse votre cas..."):
            
            # Formatage de l'historique complet pour l'envoi
            chat_history = []
            for msg in st.session_state.messages:
                chat_history.append({"role": msg["role"], "content": msg["content"]})
                
            # Injecter l'ID patient si sélectionné dans le premier message si absent
            if patient_id and not any(patient_id in m["content"] for m in st.session_state.messages):
                chat_history[-1]["content"] += f" (ID Patient: {patient_id})"
            
            success = False
            
            # MODE 1 : Connexion API FastAPI
            if conn_mode == "API FastAPI (Port 8000)":
                try:
                    payload = {
                        "messages": chat_history,
                        "patient_id": patient_id,
                        "diagnostic_summary": st.session_state.diagnostic_summary,
                        "interim_care": st.session_state.interim_care,
                        "physician_treatment": st.session_state.physician_treatment,
                        "final_report": st.session_state.final_report,
                        "question_count": st.session_state.question_count
                    }
                    
                    response = requests.post("http://localhost:8000/chat", json=payload, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.messages = data["messages"]
                        st.session_state.next_step = data["next_step"]
                        st.session_state.question_count = data["question_count"]
                        st.session_state.interim_care = data["interim_care"]
                        st.session_state.diagnostic_summary = data["diagnostic_summary"]
                        st.session_state.physician_treatment = data["physician_treatment"]
                        st.session_state.final_report = data["final_report"]
                        success = True
                    else:
                        st.error(f"Erreur API FastAPI ({response.status_code}) : {response.text}")
                except Exception as ex:
                    st.warning("⚠️ Impossible de joindre l'API FastAPI sur le port 8000. Tentative de bascule sur le Moteur local autonome...")
            
            # MODE 2 / FALLBACK : Moteur local autonome
            if not success:
                if LOCAL_GRAPH_AVAILABLE:
                    try:
                        lc_history = []
                        for msg in chat_history:
                            if msg["role"] == "user":
                                lc_history.append(HumanMessage(content=msg["content"]))
                            else:
                                lc_history.append(AIMessage(content=msg["content"]))
                                
                        inputs = {
                            "messages": lc_history,
                            "next": "supervisor",
                            "question_count": st.session_state.question_count,
                            "interim_care": st.session_state.interim_care,
                            "diagnostic_summary": st.session_state.diagnostic_summary,
                            "physician_treatment": st.session_state.physician_treatment,
                            "final_report": st.session_state.final_report
                        }
                        
                        outputs = graph.invoke(inputs)
                        
                        # Mettre à jour la session
                        st.session_state.next_step = outputs.get("next", "FINISH")
                        st.session_state.question_count = outputs.get("question_count", 0)
                        st.session_state.interim_care = outputs.get("interim_care", "")
                        st.session_state.diagnostic_summary = outputs.get("diagnostic_summary", "")
                        st.session_state.physician_treatment = outputs.get("physician_treatment", "")
                        st.session_state.final_report = outputs.get("final_report", "")
                        
                        # Reformater les messages
                        formatted = []
                        for msg in outputs.get("messages", []):
                            role = "user" if isinstance(msg, HumanMessage) else "assistant"
                            sender = getattr(msg, "name", None) or ("Patient" if role == "user" else "Assistant")
                            formatted.append({"role": role, "sender": sender, "content": msg.content})
                            
                        st.session_state.messages = formatted
                        success = True
                    except Exception as local_ex:
                        st.error(f"Erreur d'exécution locale du graphe : {local_ex}")
                else:
                    st.error("Le module LangGraph local n'a pas pu être importé. Vérifiez vos dépendances.")
            
            if success:
                st.rerun()

# ----------------------------------------------------
# COLONNE DE DROITE - DOSSIER CLINIQUE & ÉTAT DU GRAPHE
# ----------------------------------------------------
with data_col:
    tab1, tab2 = st.tabs(["📄 Fiche Médicale Finale", "⚙️ Inspecteur de l'État"])
    
    with tab1:
        if st.session_state.final_report:
            st.success("✅ Rapport Clinique Final Disponible !")
            st.markdown(st.session_state.final_report)
        else:
            st.info("⏳ Le rapport clinique final sera généré automatiquement une fois que le diagnostic aura été affiné par l'agent de diagnostic et validé par le médecin senior.")
            
            # Afficher des résumés intermédiaires au fur et à mesure pour la visibilité
            if st.session_state.diagnostic_summary:
                st.warning("⚠️ Phase : En attente de validation du Médecin")
                st.subheader("Synthese Diagnostique (Diagnostic Agent)")
                st.code(st.session_state.diagnostic_summary, language="markdown")
                
            if st.session_state.interim_care:
                st.subheader("Soins de premier secours conseillés")
                st.info(st.session_state.interim_care)
                
    with tab2:
        st.subheader("Inspection des Variables du Graphe")
        st.markdown("Valeurs actuelles de l'état `MedicalState` de LangGraph :")
        
        state_inspector = {
            "next": st.session_state.next_step,
            "question_count": st.session_state.question_count,
            "interim_care": st.session_state.interim_care,
            "diagnostic_summary": st.session_state.diagnostic_summary,
            "physician_treatment": st.session_state.physician_treatment,
            "final_report": "Généré (voir l'onglet principal)" if st.session_state.final_report else "Vide"
        }
        
        st.json(state_inspector)
        
        # Guide d'utilisation clinique
        st.subheader("📚 Guide de démonstration")
        st.markdown("""
        **Comment faire une démo impeccable ?**
        1. Sélectionnez un profil à gauche (ex : **Jean Dupont**).
        2. Écrivez ses symptômes (ex: *"J'ai très mal à la tête et j'ai chaud"*).
        3. Répondez à la question de précision posée par l'agent.
        4. Observez la transition de la timeline en haut et l'apparition du rapport validé par le médecin !
        """)
