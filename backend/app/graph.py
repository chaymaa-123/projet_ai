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


async def diagnostic_agent_node(state: MedicalState):
    """
    Rôle : Recueillir les symptômes et charger le dossier en secours local très stable.
    Utilise GPT pour poser des questions intelligentes et générer la synthèse clinique.
    """
    current_count = state.get("question_count", 0)
    patient_id = state.get("patient_id", "PAT-001")
    
    from backend.app.tools.mcp_client import call_mcp_consulter_patient
    
    # Secours local si XAMPP est éteint
    infos_patient_local = (
        f"Dossier Patient (Profil de Secours) : ({patient_id})\n"
        "- Antécédents : Hypertension artérielle (HTA)\n"
        "- Allergies : Pénicilline\n"
        "- Traitements actuels : Amlodipine 5mg"
    )
    
    # APPEL RÉEL À LA BASE DE DONNÉES VIA MCP
    try:
        mcp_data = await call_mcp_consulter_patient(patient_id)
        if "Erreur" not in mcp_data and "Aucun dossier" not in mcp_data:
            infos_patient_local = f"Dossier Patient depuis MySQL :\n{mcp_data}"
    except Exception:
        pass
    
    # Questions par défaut (fallback en cas d'erreur API ou absence de clé)
    questions_default = [
        "Question 1/5 : Pouvez-vous me décrire précisément l'apparition de vos symptômes ?",
        "Question 2/5 : À quelle intensité évaluez-vous votre douleur sur une échelle de 1 à 10 ?",
        "Question 3/5 : Avez-vous des symptômes associés (nausées, vertiges, troubles visuels) ?",
        "Question 4/5 : Prenez-vous un traitement particulier pour calmer cette crise en ce moment ?",
        "Question 5/5 : Vos antécédents d'Hypertension sont-ils stables actuellement ?"
    ]
    
    # Détection d'urgence (secours déterministe)
    mots_cles_urgence = ["poitrine", "respirer", "etouffe", "avc", "inconscient", "sang", "paralyse", "cardiaque", "infarctus", "severe", "insupportable", "mortel", "agonie"]
    dernier_msg_texte = ""
    for m in reversed(state.get("messages", [])):
        if hasattr(m, "content"):
            dernier_msg_texte = m.content.lower()
            break
        elif isinstance(m, tuple) and len(m) > 1:
            dernier_msg_texte = m[1].lower()
            break
    
    est_urgent_secours = any(k in dernier_msg_texte for k in mots_cles_urgence)
    
    if current_count < 5:
        question_suivante = questions_default[current_count]
        est_urgent_llm = False
        
        llm = get_llm()
        if llm:
            try:
                system_prompt = (
                    "Vous êtes l'Agent de Diagnostic Médical d'une équipe clinique multi-agents.\n"
                    "Votre objectif est d'analyser les symptômes décrits par le patient, son dossier et de lui poser "
                    "une question pertinente (UNE SEULE question claire, directe et empathique à la fois).\n\n"
                    f"--- Dossier Médical du Patient ---\n{infos_patient_local}\n\n"
                    "CONSIGNE DE SÉCURITÉ CLINIQUE CRITIQUE :\n"
                    "Si le patient décrit des symptômes d'extrême urgence (ex: douleur thoracique intense, grande difficulté à respirer, signes d'AVC, perte de connaissance, hémorragie sévère, crise hypertensive majeure avec symptômes neurologiques), vous devez OBLIGATOIREMENT interrompre immédiatement le questionnaire et déclarer l'urgence.\n"
                    "Pour déclarer l'urgence, entourez votre message de la balise <URGENT>. Exemple :\n"
                    "<URGENT>🚨 ATTENTION : Vos symptômes présentent des signes de gravité immédiate. C'est urgent, veuillez consulter immédiatement un médecin ou vous rendre aux urgences !</URGENT>\n\n"
                    f"Sinon, vous devez poser la QUESTION {current_count + 1}/5 de manière intelligente en fonction des messages précédents."
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
                
                if "<URGENT>" in question_suivante:
                    est_urgent_llm = True
                    question_suivante = question_suivante.split("<URGENT>")[1].split("</URGENT>")[0].strip()
            except Exception:
                pass
        
        if est_urgent_secours or est_urgent_llm:
            urgent_msg = "🚨 ATTENTION : Vos symptômes présentent des signes de gravité immédiate. C'est urgent, veuillez consulter immédiatement un médecin ou vous rendre aux urgences !" if not llm or not est_urgent_llm else question_suivante
            return {
                "messages": [("assistant", urgent_msg)],
                "question_count": 6, # Force l'interruption immédiate du graphe vers le médecin
                "diagnostic_summary": f"🚨 CAS D'URGENCE EXTRÊME DÉTECTÉ : {dernier_msg_texte or 'Symptômes sévères signalés.'}",
                "interim_care": "⚠️ URGENCE MÉDICALE IMMÉDIATE. Veuillez contacter les secours ou vous diriger vers le service d'urgence le plus proche.",
                "is_urgent": True
            }
            
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


async def physician_review_node(state: MedicalState):
    """
    Rôle : Nœud de contrôle du médecin (Human-in-the-Loop).
    Analyse les risques cliniques de manière synchrone via l'outil MCP réel.
    """
    from backend.app.tools.mcp_client import call_mcp_verifier_contre_indications
    
    facteurs_detectes = state.get("diagnostic_summary", "").lower()
 
    # VÉRITABLE APPEL AU SERVEUR MCP
    try:
        # On exécute la fonction asynchrone du MCP de manière non bloquante
        validation_mcp_brute = await call_mcp_verifier_contre_indications(facteurs_detectes)
        validation_mcp = f"🛡️ **Vérification MCP** :\n{validation_mcp_brute}"
    except Exception as e:
        validation_mcp = f"⚠️ Mode Secours (Le serveur MCP est injoignable) : Aucune contre-indication vérifiée."

    # Récupération du traitement saisi par le médecin sur l'interface Streamlit
    traitement_saisi = state.get("physician_treatment", "")
    
    return {"physician_treatment": f"{validation_mcp}\n\nPrescription finale validée par le médecin : {traitement_saisi}"}


async def report_agent_node(state: MedicalState):
    """
    Rôle : Générer le compte-rendu final au format Markdown.
    Utilise GPT pour rédiger un rapport médical hautement qualitatif et professionnel.
    """
    diag_sum = state.get('diagnostic_summary', 'Non spécifié')
    interim = state.get('interim_care', 'Non spécifié')
    phys_treat = state.get('physician_treatment', 'Non spécifié')
    patient_id = state.get('patient_id', 'PAT-001')
    
    from backend.app.tools.mcp_client import call_mcp_consulter_patient
    try:
        db_info = await call_mcp_consulter_patient(patient_id)
    except Exception:
        db_info = f"Dossier du patient {patient_id}."
    
    compte_rendu = f"""# 📄 RAPPORT MÉDICAL D'ORIENTATION ET DE CONSEIL
*Généré par votre Assistant Médical IA & Validé par un Médecin Senior*

---

### 👤 Informations du Dossier Médical
{db_info}

### 🩺 1. Résumé de vos symptômes
Voici ce que nous avons retenu de notre échange :
> {diag_sum}

### 🩹 2. Ce que vous pouvez faire immédiatement
En attendant que le traitement fasse effet, voici des conseils pratiques pour vous soulager :
{interim}

### 💊 3. La décision du médecin et votre traitement
Après révision de votre dossier et vérification stricte de votre sécurité (allergies, contre-indications) :
{phys_treat}

---
💡 **Notre conseil** : Ce traitement a été spécialement adapté à votre profil clinique. Si vos symptômes s'aggravent ou persistent au-delà de 48 heures, veuillez consulter physiquement un professionnel de santé ou appeler les urgences.

*⚠️ Avertissement : Ce document est issu d'un outil académique d'orientation. Il ne remplace en aucun cas une véritable consultation médicale.*
"""
    
    if state.get("is_urgent", False):
        compte_rendu = f"""# 🚨 ATTENTION : PARTEZ CHEZ LE MÉDECIN, C'EST UN CAS EXTRÊME !

⚠️ **URGENCE MÉDICALE ABSOLUE DÉTECTÉE**
Veuillez vous diriger immédiatement vers le cabinet médical le plus proche ou appeler les urgences (le 15 ou le 112).

---

{compte_rendu}"""

    llm = get_llm()
    if llm:
        try:
            system_prompt = (
                "Vous êtes l'Agent de Rédaction du Rapport Médical. Votre rôle est de rédiger un rapport final destiné au patient.\n"
                "Le rapport doit être explicatif, pédagogique, détaillé mais facile à lire pour quelqu'un qui n'est pas médecin.\n\n"
                "Voici les données d'entrée validées par le médecin senior :\n"
                f"1. Informations de la base de données : {db_info}\n"
                f"2. Synthèse clinique et symptômes : {diag_sum}\n"
                f"3. Conseils pratiques de soins : {interim}\n"
                f"4. Traitement officiel du médecin : {phys_treat}\n\n"
                "INSTRUCTIONS :\n"
                "- Adressez-vous directement au patient (utilisez 'vous') et mentionnez son nom s'il est dans les informations de la base de données.\n"
                "- Expliquez brièvement pourquoi ce traitement a été choisi en fonction de ses symptômes et de son dossier (allergies/antécédents).\n"
                "- Structurez de manière claire (Votre dossier, Vos symptômes, Premiers gestes, Votre traitement officiel).\n"
                "- Terminez obligatoirement par un avertissement de sécurité indiquant que le système ne remplace pas une consultation."
            )
            if state.get("is_urgent", False):
                system_prompt += "\n- CRITIQUE : Ce patient est dans un état d'urgence extrême. Vous DEVEZ absolument commencer le rapport par le message exact suivant en gras : '🚨 ATTENTION : PARTEZ CHEZ LE MÉDECIN, C'EST UN CAS EXTRÊME !' et lui intimer l'ordre de consulter sur-le-champ."
                
            response = llm.invoke([("system", system_prompt)])
            compte_rendu = response.content
            
            # Garanti que l'en-tête d'urgence est toujours présent en haut du rapport généré par le LLM
            if state.get("is_urgent", False) and "PARTEZ CHEZ LE MÉDECIN" not in compte_rendu:
                compte_rendu = f"# 🚨 ATTENTION : PARTEZ CHEZ LE MÉDECIN, C'EST UN CAS EXTRÊME !\n\n⚠️ **URGENCE MÉDICALE IMMÉDIATE**\n\n" + compte_rendu
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