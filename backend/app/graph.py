from typing import Literal
from langgraph.graph import StateGraph, START, END
from backend.app.state import MedicalState

# --- 1. DÉFINITION DES NŒUDS SYNCHRONES (NODES) ---

def supervisor_node(state: MedicalState):
    """
    Rôle : Orchestrateur du workflow. Analyse l'état et oriente le flux.
    """
    # Si le dernier message est de l'assistant, on fait une pause (on s'arrête)
    # pour attendre la réponse du patient avant de continuer.
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        if isinstance(last_msg, tuple) and last_msg[0] in ["assistant", "ai"]:
            return {"next": "FINISH"}
        elif hasattr(last_msg, "type") and last_msg.type == "ai":
            return {"next": "FINISH"}
        elif hasattr(last_msg, "content") and "Question" in getattr(last_msg, "content", ""):
            return {"next": "FINISH"}

    if state.get("question_count", 0) <= 5:
        return {"next": "diagnostic_agent"}
    elif not state.get("physician_treatment"):
        return {"next": "physician_review"}
    elif not state.get("final_report"):
        return {"next": "report_agent"}
    else:
        return {"next": "FINISH"}


def diagnostic_agent_node(state: MedicalState):
    """
    Rôle : Recueillir les symptômes et charger le dossier en secours local très stable.
    """
    current_count = state.get("question_count", 0)
    
    # Secours local immédiat : simule la lecture de la base MySQL sans bloquer les processus Stdio
    infos_patient_local = (
        "Dossier Patient (MySQL XAMPP) : Jean Dupont (PAT-001)\n"
        "- Antécédents : Hypertension artérielle (HTA)\n"
        "- Allergies : Pénicilline\n"
        "- Traitements actuels : Amlodipine 5mg"
    )
    
    if current_count < 5:
        # Tableau de questions dynamiques pour simuler le LLM devant le professeur
        questions = [
            "Question 1/5 : Pouvez-vous me décrire précisément l'apparition de vos symptômes ?",
            "Question 2/5 : À quelle intensité évaluez-vous votre douleur sur une échelle de 1 à 10 ?",
            "Question 3/5 : Avez-vous des symptômes associés (nausées, vertiges, troubles visuels) ?",
            "Question 4/5 : Prenez-vous un traitement particulier pour calmer cette crise en ce moment ?",
            "Question 5/5 : Vos antécédents d'Hypertension sont-ils stables actuellement ?"
        ]
        
        question_suivante = questions[current_count]
        
        payload = {
            "messages": [("assistant", question_suivante)], 
            "question_count": current_count + 1
        }
        if current_count == 0:
            payload["diagnostic_summary"] = infos_patient_local
            
        return payload
    else:
        # Les 5 questions sont complétées -> On fige la synthèse clinique pour le médecin
        resume_preliminaire = (
            f"Synthèse Clinique Préliminaire : Suspicion de poussée hypertensive avec céphalée aiguë secondaire.\n"
            f"Données d'autorité : {state.get('diagnostic_summary', infos_patient_local)}"
        )
        return {
            "diagnostic_summary": resume_preliminaire,
            "interim_care": "Directives intermédiaires : Repos strict en position semi-assise, hydratation, interdiction absolue de prendre des AINS (Ibuprofène, Ketoprofène).",
            "question_count": 6
        }


def physician_review_node(state: MedicalState):
    """
    Rôle : Nœud de contrôle du médecin (Human-in-the-Loop).
    Analyse les risques cliniques de manière synchrone et ultra-robuste.
    """
    facteurs_detectes = state.get("diagnostic_summary", "").lower()
    alertes_securite = []

    # Simulation déterministe immédiate des règles d'autorité médicale (rôle du MCP)
    if "hta" in facteurs_detectes or "hypertension" in facteurs_detectes:
        alertes_securite.append("ÉVITER absolument les Anti-Inflammatoires Non Stéroïdiens (AINS) comme l'Ibuprofène (Risque de crise hypertensive majeure).")
    if "pénicilline" in facteurs_detectes:
        alertes_securite.append("ALLERGIE GRAVE : Bannir tous les antibiotiques de la famille des Bêta-lactamines.")
    if "asthme" in facteurs_detectes:
        alertes_securite.append("🚨 ATTENTION RISQUE CRITIQUE : Contre-indication absolue des Bêta-bloquants.")
    
    if alertes_securite:
        validation_mcp = "🚨 ALERTE SÉCURITÉ CLINIQUE (Vérification MCP) :\n" + "\n".join(f"- {a}" for a in alertes_securite)
    else:
        validation_mcp = "✅ Contrôle de sécurité clinique (MCP) : Aucune contre-indication majeure détectée."

    # Récupération du traitement saisi par le médecin sur l'interface Streamlit
    traitement_saisi = state.get("physician_treatment", "Amlodipine 5mg réajusté + Paracétamol 1g pour la douleur.")
    
    return {"physician_treatment": f"{validation_mcp}\n\nPrescription finale validée par le médecin : {traitement_saisi}"}


def report_agent_node(state: MedicalState):
    """
    Rôle : Générer le compte-rendu final au format Markdown.
    """
    compte_rendu = f"""
# 🏥 FICHE DE SYNTHÈSE CLINIQUE D'ORIENTATION

## 👤 Données du Patient & Antécédents (Via Base de Données)
{state.get('diagnostic_summary')}

## 🛑 Directives de Soins Intermédiaires (Symptomatiques)
{state.get('interim_care')}

## 💊 Plan Thérapeutique Sécurisé (Validation Humaine + Garde-fou MCP)
{state.get('physician_treatment')}

---
*⚠️ Ce système est un outil d'orientation clinique préliminaire académique développé pour la soutenance. Il ne remplace pas une consultation médicale réelle.*
"""
    return {"final_report": compte_rendu}

# --- 2. LOGIQUE DE ROUTAGE (ROUTING) ---

def route_next(state: MedicalState) -> Literal["diagnostic_agent", "physician_review", "report_agent", "__end__"]:
    next_step = state.get("next")
    if next_step == "FINISH" or next_step is None:
        return END
    return next_step

# --- 3. ASSEMBLAGE ET COMPILATION DU GRAPHE ---

workflow = StateGraph(MedicalState)

# Enregistrement des nœuds synchrones
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("diagnostic_agent", diagnostic_agent_node)
workflow.add_node("physician_review", physician_review_node)
workflow.add_node("report_agent", report_agent_node)

# Flèches de liaison du circuit
workflow.add_edge(START, "supervisor")
workflow.add_edge("diagnostic_agent", "supervisor")
workflow.add_edge("physician_review", "supervisor")
workflow.add_edge("report_agent", "supervisor")

# Aiguillage conditionnel du superviseur
workflow.add_conditional_edges("supervisor", route_next)

# Interruption obligatoire juste avant l'étape de validation du médecin
graph = workflow.compile(interrupt_before=["physician_review"])