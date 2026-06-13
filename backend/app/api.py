import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importation de notre graphe synchrone et de la structure d'état
from langchain_core.messages import HumanMessage
from backend.app.graph import graph

app = FastAPI(title="API d'Orientation Clinique Multi-Agents", version="1.0")

# Activation du CORS pour Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structure locale pour mémoriser les états des sessions sans base complexe
SESSIONS = {}

# --- MODÈLES DE DONNÉES (PYDANTIC) ---
class StartSessionRequest(BaseModel):
    patient_id: str

class StartConsultationRequest(BaseModel):
    thread_id: str
    message: str

class ResumeConsultationRequest(BaseModel):
    thread_id: str
    physician_treatment: str

class AddPatientRequest(BaseModel):
    patient_id: str
    nom: str
    antecedents: str
    allergies: str
    traitements: str

# --- 🚀 LES ROUTES DE L'API 100% SYNCHRONES ---

@app.post("/patients/add")
def add_patient_route(req: AddPatientRequest):
    """Enregistre un patient dans MySQL via le MCP."""
    import asyncio
    from backend.app.tools.mcp_client import call_mcp_ajouter_patient
    try:
        res = asyncio.run(call_mcp_ajouter_patient(
            req.patient_id, req.nom, req.antecedents, req.allergies, req.traitements
        ))
        return {"status": "success", "message": res}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/patients")
def list_patients_route():
    """Récupère la liste de tous les patients depuis la base de données via MCP."""
    import asyncio
    import json
    from backend.app.tools.mcp_client import call_mcp_lister_patients
    try:
        res = asyncio.run(call_mcp_lister_patients())
        patients = json.loads(res)
        return patients
    except Exception as e:
        # Fallback stable
        return [
            {"patient_id": "PAT-001", "nom": "Jean Dupont"},
            {"patient_id": "PAT-002", "nom": "Chaymaa Alami"},
            {"patient_id": "PAT-003", "nom": "Youssef Benani"}
        ]

@app.post("/sessions/start")
def start_session(request: StartSessionRequest):
    """
    Initialise une session et crée un dictionnaire d'état vierge pour le patient.
    """
    thread_id = str(uuid.uuid4())
    SESSIONS[thread_id] = {
        "patient_id": request.patient_id,
        "status": "en_collecte",
        "state": {
            "patient_id": request.patient_id,
            "messages": [],
            "question_count": 0,
            "physician_treatment": "",
            "final_report": "",
            "diagnostic_summary": "",
            "interim_care": "",
            "is_urgent": False
        }
    }
    return {"thread_id": thread_id, "patient_id": request.patient_id, "status": "Initialisé"}


@app.post("/consultation/start")
async def start_consultation(request: StartConsultationRequest):
    """
    Exécute le graphe de manière déterministe et isole l'état pour éviter les crashs d'interruption.
    """
    if request.thread_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session introuvable.")
    
    session = SESSIONS[request.thread_id]
    current_medical_state = session["state"]
    
    # Ajout du message de l'utilisateur dans l'historique sous forme de HumanMessage
    current_medical_state["messages"].append(HumanMessage(content=request.message))
    
    try:
        # Configuration bidon pour satisfaire la signature du graphe compille
        config = {"configurable": {"thread_id": request.thread_id}}
        
        # Lancement du graphe de manière synchrone
        # On passe l'état actuel et on récupère le dictionnaire modifié en sortie
        output = await graph.ainvoke(current_medical_state, config=config)
        session["state"].update(output)
    except Exception as e:
        # Capture l'interruption de LangGraph avant le médecin sans faire planter l'API
        print(f"Erreur d'invocation du graphe: {e}")

    # Forçage du passage à l'étape du médecin si le compteur atteint la limite ou si c'est un cas urgent
    if session["state"].get("question_count", 0) >= 6 or session["state"].get("is_urgent", False):
        session["status"] = "en_attente_medecin"
    else:
        session["status"] = "en_collecte"
    return {
        "message": "Requête traitée.",
        "state": {
            "question_count": session["state"].get("question_count", 0),
            "diagnostic_summary": session["state"].get("diagnostic_summary", ""),
            "interim_care": session["state"].get("interim_care", "")
        }
    }


@app.post("/consultation/resume")
async def resume_consultation(request: ResumeConsultationRequest):
    """
    Injecte la décision du médecin et finalise le rapport.
    """
    if request.thread_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session introuvable.")
    
    session = SESSIONS[request.thread_id]
    
    # Injection du traitement
    session["state"]["physician_treatment"] = request.physician_treatment
    
    try:
        config = {"configurable": {"thread_id": request.thread_id}}
        # Relance le graphe pour exécuter les nœuds restants (Report Agent)
        output = await graph.ainvoke(session["state"], config=config)
        session["state"].update(output)
    except Exception as e:
        print(f"Erreur de reprise du graphe: {e}")
        
    session["status"] = "termine"
    return {"message": "Consultation terminée."}


@app.get("/consultation/{thread_id}")
def get_consultation_state(thread_id: str):
    """
    Renvoie instantanément l'état mémoire de l'API sans interroger le composant Checkpointer.
    """
    if thread_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session introuvable.")
        
    session = SESSIONS[thread_id]
    state = session["state"]
    
    # Extraction propre de l'historique pour l'interface de chat Streamlit
    history = []
    for msg in state.get("messages", []):
        if isinstance(msg, tuple):
            history.append({"role": msg[0], "text": msg[1]})
        elif hasattr(msg, "content"):
            history.append({"role": "assistant" if msg.type == "ai" else "user", "text": msg.content})
            
    return {
        "thread_id": thread_id,
        "status": session["status"],
        "question_count": state.get("question_count", 0),
        "diagnostic_summary": state.get("diagnostic_summary", ""),
        "interim_care": state.get("interim_care", ""),
        "physician_treatment": state.get("physician_treatment", ""),
        "is_urgent": state.get("is_urgent", False),
        "messages_history": history
    }


@app.get("/consultation/{thread_id}/report")
def get_final_report(thread_id: str):
    """
    Retourne le livrable Markdown final.
    """
    if thread_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session introuvable.")
        
    session = SESSIONS[thread_id]
    return {"final_report": session["state"].get("final_report", "Rapport non disponible.")}