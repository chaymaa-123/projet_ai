import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.app.state import MedicalState

# Charger automatiquement le fichier .env
load_dotenv()

def get_llm():
    """
    Initialise le LLM en fonction des variables d'environnement.
    Garantit une initialisation sécurisée et flexible.
    """
    if os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)
    elif os.getenv("GEMINI_API_KEY"):
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    else:
        # Aucun clé d'API fournie : retourne None, la logique de repli locale prendra le relais
        return None

def supervisor_node(state: MedicalState) -> Dict[str, Any]:
    """
    Le Superviseur Clinique. Analyse l'état médical global et les derniers messages
    pour aiguiller le cas clinique vers l'agent adéquat.
    """
    messages = state.get("messages", [])
    question_count = state.get("question_count", 0)
    diag_summary = state.get("diagnostic_summary", "")
    phys_treatment = state.get("physician_treatment", "")
    final_report = state.get("final_report", "")
    
    # ----------------------------------------------------
    # LOGIQUE DE REPLI DIRECT (RÈGLES CLINIQUES DÉTERMINISTES)
    # ----------------------------------------------------
    # Cela garantit que le graphe fonctionne même sans clé API active
    if not diag_summary:
        # Étape 1 : Diagnostic / Recueil des symptômes
        next_agent = "diagnostic_agent"
    elif diag_summary and not phys_treatment:
        # Étape 2 : Revue par le médecin
        next_agent = "physician_review"
    elif diag_summary and phys_treatment and not final_report:
        # Étape 3 : Synthèse par le Report Agent
        next_agent = "report_agent"
    else:
        # Étape 4 : Terminé
        next_agent = "FINISH"
        
    # ----------------------------------------------------
    # APPEL AU LLM POUR VALIDATION / RAISONNEMENT SUPERVISEUR
    # ----------------------------------------------------
    llm = get_llm()
    decision_reason = "Règle de transition clinique automatique appliquée."
    
    if llm:
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "Vous êtes le Superviseur Clinique d'une équipe médicale multi-agents.\n"
                    "Votre rôle est d'analyser l'historique et de décider quel agent doit intervenir ensuite.\n"
                    "Agents disponibles :\n"
                    "- 'diagnostic_agent' : Recueil des symptômes et questions initiales.\n"
                    "- 'physician_review' : Examen clinique senior et plan de traitement officiel (requis dès que les symptômes sont clairs).\n"
                    "- 'report_agent' : Rédaction de la synthèse finale (dès que le traitement est établi).\n"
                    "- 'FINISH' : Dès que le rapport final est rédigé.\n\n"
                    "Etat actuel :\n"
                    "- diagnostic_summary: {diagnostic_summary}\n"
                    "- physician_treatment: {physician_treatment}\n"
                    "- final_report: {final_report}\n\n"
                    "Répondez sous la forme d'un seul mot correspondant à l'agent choisi."
                )),
                MessagesPlaceholder(variable_name="messages")
            ])
            
            chain = prompt | llm
            response = chain.invoke({
                "diagnostic_summary": diag_summary,
                "physician_treatment": phys_treatment,
                "final_report": final_report,
                "messages": messages
            })
            
            llm_decision = response.content.strip()
            # Validation de la réponse LLM
            if llm_decision in ["diagnostic_agent", "physician_review", "report_agent", "FINISH"]:
                next_agent = llm_decision
                decision_reason = "Décision prise par le LLM Superviseur."
        except Exception as e:
            decision_reason = f"Erreur LLM ({str(e)}). Repli sur les règles cliniques."
            
    # Message de log pour l'interface utilisateur
    log_message = AIMessage(
        content=f"[Superviseur] Phase suivante déterminée : **{next_agent}** ({decision_reason})",
        name="Clinical_Supervisor"
    )
    
    return {
        "next": next_agent,
        "messages": [log_message]
    }
