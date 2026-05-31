import os
import re
from typing import Literal
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from backend.app.state import MedicalState

# Charger automatiquement le fichier .env
load_dotenv()

def get_llm():
    """
    Initialise le LLM ChatOpenAI en fonction de la clé d'API dans .env.
    """
    if os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    return None

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
    Utilise GPT pour poser des questions intelligentes et générer la synthèse clinique.
    """
    current_count = state.get("question_count", 0)
    
    # Secours local immédiat : simule la lecture de la base MySQL sans bloquer les processus Stdio
    infos_patient_local = (
        "Dossier Patient (MySQL XAMPP) : Jean Dupont (PAT-001)\n"
        "- Antécédents : Hypertension artérielle (HTA)\n"
        "- Allergies : Pénicilline\n"
        "- Traitements actuels : Amlodipine 5mg"
    )
    
    # Questions par défaut (fallback en cas d'erreur API ou absence de clé)
    questions_default = [
        "Question 1/5 : Pouvez-vous me décrire précisément l'apparition de vos symptômes ?",
        "Question 2/5 : À quelle intensité évaluez-vous votre douleur sur une échelle de 1 à 10 ?",
        "Question 3/5 : Avez-vous des symptômes associés (nausées, vertiges, troubles visuels) ?",
        "Question 4/5 : Prenez-vous un traitement particulier pour calmer cette crise en ce moment ?",
        "Question 5/5 : Vos antécédents d'Hypertension sont-ils stables actuellement ?"
    ]
    
    if current_count < 5:
        question_suivante = questions_default[current_count]
        
        llm = get_llm()
        if llm:
            try:
                system_prompt = (
                    "Vous êtes l'Agent de Diagnostic Médical d'une équipe clinique multi-agents.\n"
                    "Votre objectif est d'analyser les symptômes décrits par le patient, son dossier et de lui poser "
                    "une question pertinente (UNE SEULE question claire, directe et empathique à la fois).\n\n"
                    f"--- Dossier Médical du Patient ---\n{infos_patient_local}\n\n"
                    f"CONSIGNE DE WORKFLOW :\n"
                    f"Vous devez poser la QUESTION {current_count + 1}/5.\n"
                    "Adaptez cette question de manière intelligente en fonction des messages précédents."
                )
                
                # Conversion des messages pour l'historique de discussion
                lc_messages = []
                for msg in state.get("messages", []):
                    if isinstance(msg, tuple):
                        if msg[0] == "user":
                            lc_messages.append(HumanMessage(content=msg[1]))
                        else:
                            lc_messages.append(AIMessage(content=msg[1]))
                    else:
                        lc_messages.append(msg)
                        
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    MessagesPlaceholder(variable_name="chat_history")
                ])
                chain = prompt | llm
                response = chain.invoke({"chat_history": lc_messages})
                question_suivante = response.content
            except Exception:
                pass
        
        payload = {
            "messages": [("assistant", question_suivante)], 
            "question_count": current_count + 1
        }
        if current_count == 0:
            payload["diagnostic_summary"] = infos_patient_local
            
        return payload
    else:
        # Les 5 questions sont complétées -> On fige la synthèse clinique pour le médecin
        diag_sum = state.get('diagnostic_summary', infos_patient_local)
        
        resume_preliminaire = (
            f"Synthèse Clinique Préliminaire : Suspicion de poussée hypertensive avec céphalée aiguë secondaire.\n"
            f"Données d'autorité : {diag_sum}"
        )
        interim_care = "Directives intermédiaires : Repos strict en position semi-assise, hydratation, interdiction absolue de prendre des AINS (Ibuprofène, Ketoprofène)."
        
        llm = get_llm()
        if llm:
            try:
                system_prompt = (
                    "Vous êtes l'Agent de Diagnostic Médical. Le recueil des symptômes est terminé (5 questions ont été posées).\n"
                    "Sur la base de tout l'historique de discussion et du dossier patient, vous devez produire :\n"
                    "1. Une synthèse clinique préliminaire structurée.\n"
                    "2. Les directives de soins intermédiaires symptomatiques adaptées et prudentes.\n\n"
                    f"--- Dossier Médical du Patient ---\n{infos_patient_local}\n\n"
                    "RÉPONDEZ STRICTEMENT sous le format XML suivant (sans aucune autre phrase d'accompagnement) :\n"
                    "<SYNTHESE>\n"
                    "Symptômes : [Description exhaustive des symptômes relevés]\n"
                    "Gravité suspectée : [Légère/Modérée/Sévère]\n"
                    "Facteurs aggravants : [Antécédents ou anomalies constatées]\n"
                    "</SYNTHESE>\n"
                    "<SOINS>\n"
                    "[Vos recommandations de soins intermédiaires pour soulager le patient en attendant l'avis médical final]\n"
                    "</SOINS>"
                )
                
                # Conversion des messages
                lc_messages = []
                for msg in state.get("messages", []):
                    if isinstance(msg, tuple):
                        if msg[0] == "user":
                            lc_messages.append(HumanMessage(content=msg[1]))
                        else:
                            lc_messages.append(AIMessage(content=msg[1]))
                    else:
                        lc_messages.append(msg)
                        
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    MessagesPlaceholder(variable_name="chat_history")
                ])
                chain = prompt | llm
                response = chain.invoke({"chat_history": lc_messages})
                
                summary_match = re.search(r"<SYNTHESE>(.*?)</SYNTHESE>", response.content, re.DOTALL)
                care_match = re.search(r"<SOINS>(.*?)</SOINS>", response.content, re.DOTALL)
                
                if summary_match:
                    resume_preliminaire = summary_match.group(1).strip()
                if care_match:
                    interim_care = care_match.group(1).strip()
            except Exception:
                pass
                
        return {
            "diagnostic_summary": resume_preliminaire,
            "interim_care": interim_care,
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
    Utilise GPT pour rédiger un rapport médical hautement qualitatif et professionnel.
    """
    diag_sum = state.get('diagnostic_summary')
    interim = state.get('interim_care')
    phys_treat = state.get('physician_treatment')
    
    compte_rendu = f"""
# 🏥 FICHE DE SYNTHÈSE CLINIQUE D'ORIENTATION

## 👤 Données du Patient & Antécédents (Via Base de Données)
{diag_sum}

## 🛑 Directives de Soins Intermédiaires (Symptomatiques)
{interim}

## 💊 Plan Thérapeutique Sécurisé (Validation Humaine + Garde-fou MCP)
{phys_treat}

---
*⚠️ Ce système est un outil d'orientation clinique préliminaire académique développé pour la soutenance. Il ne remplace pas une consultation médicale réelle.*
"""
    llm = get_llm()
    if llm:
        try:
            system_prompt = (
                "Vous êtes le Report Agent. Votre rôle est de rédiger une Fiche de Synthèse Clinique d'Orientation "
                "médicale extrêmement professionnelle, lisible, structurée et rédigée dans un excellent français au format Markdown.\n\n"
                "Voici les données d'entrée fournies par les autres agents et validées par le médecin senior :\n"
                f"1. Synthèse clinique et antécédents : {diag_sum}\n"
                f"2. Directives de soins intermédiaires : {interim}\n"
                f"3. Décision du médecin (avec alertes de sécurité mcp) : {phys_treat}\n\n"
                "INSTRUCTIONS :\n"
                "- Mettez en valeur les sections avec des titres clairs et une mise en page soignée (#, ##, listes, caractères gras).\n"
                "- Structurez de manière clinique et rigoureuse (Dossier, Symptômes, Diagnostic, Contre-indications, Prescription).\n"
                "- Terminez obligatoirement par l'avertissement de sécurité indiquant que le système ne remplace pas une vraie consultation."
            )
            response = llm.invoke([("system", system_prompt)])
            compte_rendu = response.content
        except Exception:
            pass
            
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