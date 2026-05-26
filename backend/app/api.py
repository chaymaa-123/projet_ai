import os
from dotenv import load_dotenv

# Charger automatiquement le fichier .env
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Importation du graphe clinique compilé
from backend.app.graph import graph

app = FastAPI(
    title="API d'Orientation Clinique Multi-Agents",
    description="API FastAPI propulsée par LangGraph pour orchestrer les soins cliniques.",
    version="1.0.0"
)

# Configuration de CORS pour permettre au frontend Streamlit de communiquer avec l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles Pydantic pour la validation des requêtes et réponses
class ChatMessage(BaseModel):
    role: str = Field(..., description="Rôle du message: 'user' ou 'assistant'")
    content: str = Field(..., description="Contenu texte du message")

class ClinicalRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Historique complet de la discussion")
    patient_id: Optional[str] = Field(None, description="Identifiant patient optionnel (ex: PAT-001)")
    diagnostic_summary: Optional[str] = ""
    interim_care: Optional[str] = ""
    physician_treatment: Optional[str] = ""
    final_report: Optional[str] = ""
    question_count: Optional[int] = 0

class ClinicalResponse(BaseModel):
    messages: List[Dict[str, Any]]
    next_step: str
    question_count: int
    interim_care: str
    diagnostic_summary: str
    physician_treatment: str
    final_report: str

def convert_to_langchain_messages(messages: List[ChatMessage]):
    """Convertit les messages Pydantic en instances de messages LangChain."""
    lc_messages = []
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            # Identifier la provenance éventuelle de l'agent si possible
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages

@app.get("/")
def read_root():
    return {"status": "online", "service": "Clinical Multi-Agent API", "framework": "LangGraph"}

@app.post("/chat", response_model=ClinicalResponse)
async def process_clinical_flow(request: ClinicalRequest):
    """
    Traite la demande clinique en injectant l'historique dans le graphe d'état LangGraph.
    Exécute le flux d'agents et retourne le nouvel état mis à jour.
    """
    try:
        # 1. Reconstruire l'état clinique initial pour LangGraph
        lc_messages = convert_to_langchain_messages(request.messages)
        
        initial_state = {
            "messages": lc_messages,
            "next": "supervisor",
            "question_count": request.question_count or 0,
            "interim_care": request.interim_care or "",
            "diagnostic_summary": request.diagnostic_summary or "",
            "physician_treatment": request.physician_treatment or "",
            "final_report": request.final_report or ""
        }
        
        # 2. Exécuter le graphe (jusqu'à l'attente d'une entrée utilisateur ou de la fin du graphe)
        # On utilise stream ou invoke. Ici, invoke récupère le résultat final après le parcours des agents
        config = {"configurable": {"thread_id": "clinical_session_1"}}
        result_state = graph.invoke(initial_state, config=config)
        
        # 3. Formater la réponse pour le frontend Streamlit
        formatted_messages = []
        for msg in result_state.get("messages", []):
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            # Récupérer le nom de l'agent ayant émis le message s'il existe
            sender_name = getattr(msg, "name", None) or ("Patient" if role == "user" else "Assistant")
            
            formatted_messages.append({
                "role": role,
                "sender": sender_name,
                "content": msg.content
            })
            
        return ClinicalResponse(
            messages=formatted_messages,
            next_step=result_state.get("next", "FINISH"),
            question_count=result_state.get("question_count", 0),
            interim_care=result_state.get("interim_care", ""),
            diagnostic_summary=result_state.get("diagnostic_summary", ""),
            physician_treatment=result_state.get("physician_treatment", ""),
            final_report=result_state.get("final_report", "")
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur de traitement LangGraph : {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Lancement du serveur API sur le port 8000
    uvicorn.run("backend.app.api:app", host="0.0.0.0", port=8000, reload=True)
