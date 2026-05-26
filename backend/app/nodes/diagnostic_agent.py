import os
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
from backend.app.state import MedicalState
from backend.app.tools.patient_tools import get_patient_records
from backend.app.tools.care_tools import get_interim_care_guidelines
from backend.app.nodes.supervisor import get_llm

def diagnostic_agent_node(state: MedicalState) -> Dict[str, Any]:
    """
    Agent de Diagnostic. Analyse les symptômes du patient, consulte son dossier médical
    et ses antécédents, et pose des questions ciblées pour affiner le diagnostic.
    Initialise les soins intermédiaires et formule une synthèse clinique.
    """
    messages = state.get("messages", [])
    question_count = state.get("question_count", 0) or 0
    diagnostic_summary = state.get("diagnostic_summary", "")
    interim_care = state.get("interim_care", "")
    
    # Récupérer le dernier message de l'utilisateur
    user_msg = ""
    for msg in reversed(messages):
        if msg.type == "human":
            user_msg = msg.content
            break
            
    # Incrémentation du compteur de questions
    question_count += 1
    
    # ----------------------------------------------------
    # DÉROULEMENT AVEC UN LLM ACTIF
    # ----------------------------------------------------
    llm = get_llm()
    if llm:
        try:
            # Récupération automatique du dossier patient s'il y a un ID patient dans le dialogue
            patient_record_data = ""
            if "PAT-" in user_msg:
                # Extraire l'ID patient (ex: PAT-001)
                import re
                match = re.search(r"PAT-\d+", user_msg)
                if match:
                    patient_record_data = get_patient_records.invoke(match.group(0))
            
            # Recherche des guides cliniques pour les symptômes
            care_data = ""
            for sym in ["fièvre", "fever", "migraine", "tête", "headache", "ventre", "abdominal", "toux", "cough"]:
                if sym in user_msg.lower():
                    care_data = get_interim_care_guidelines.invoke(sym)
                    break
                    
            system_prompt = (
                "Vous êtes l'Agent de Diagnostic Médical de l'équipe.\n"
                "Votre objectif est d'écouter les symptômes décrits par le patient, de poser des questions claires (max 1 par message) "
                "et de documenter le cas clinique.\n\n"
                f"--- Infos Dossier Patient ---\n{patient_record_data or 'Aucun dossier actif chargé.'}\n\n"
                f"--- Lignes directrices de soins ---\n{care_data or 'Générales.'}\n\n"
                "INSTRUCTIONS DE SORTIE :\n"
                "1. Si vous estimez avoir assez d'informations (compteur de questions >= 2 ou symptômes décrits de manière très précise), "
                "vous devez OBLIGATOIREMENT terminer votre message par la balise XML suivante pour formaliser la synthèse clinique :\n"
                "<SYNTHESE>\n"
                "Symptômes : [Description exhaustive]\n"
                "Gravité : [Légère/Modérée/Sévère]\n"
                "Soins intermédiaires : [Soins conseillés immédiatement]\n"
                "</SYNTHESE>\n"
                "2. Sinon, formulez simplement votre question ou demande de précision au patient."
            )
            
            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages")
            ])
            
            chain = prompt | llm
            response = chain.invoke({"messages": messages})
            response_content = response.content
            
            # Détection de la synthèse
            new_diag_summary = diagnostic_summary
            new_interim_care = interim_care
            
            if "<SYNTHESE>" in response_content:
                import re
                content_match = re.search(r"<SYNTHESE>(.*?)</SYNTHESE>", response_content, re.DOTALL)
                if content_match:
                    new_diag_summary = content_match.group(1).strip()
                    # Extraire les soins intermédiaires s'ils y figurent
                    care_match = re.search(r"Soins intermédiaires\s*:\s*(.*)", new_diag_summary, re.IGNORECASE)
                    if care_match:
                        new_interim_care = care_match.group(1).strip()
                    else:
                        new_interim_care = "Reposez-vous et hydratez-vous en attendant l'avis médical."
                
                # Nettoyer la balise XML du message affiché au patient
                clean_msg = response_content.split("<SYNTHESE>")[0].strip()
                if not clean_msg:
                    clean_msg = "J'ai bien noté l'ensemble de vos symptômes. Je transmets immédiatement votre dossier au médecin pour validation."
            else:
                clean_msg = response_content
                
            return {
                "messages": [AIMessage(content=clean_msg, name="Diagnostic_Agent")],
                "question_count": question_count,
                "diagnostic_summary": new_diag_summary,
                "interim_care": new_interim_care
            }
        except Exception as e:
            # En cas d'erreur de chaîne LLM, repli sur le simulateur
            pass

    # ----------------------------------------------------
    # LOGIQUE DE SIMULATION DÉTERMINISTE (REPLI)
    # ----------------------------------------------------
    if question_count == 1:
        reply = (
            "Bonjour. Je suis l'Agent de Diagnostic Clinique. J'ai bien pris note de votre message initial.\n"
            "Pour m'aider à mieux vous orienter, pourriez-vous préciser depuis combien de temps ces symptômes sont apparus "
            "et s'ils s'accompagnent de fièvre, de fatigue ou de douleurs particulières ?\n"
            "*(Veuillez également indiquer si vous possédez un identifiant patient type PAT-001 ou PAT-002)*."
        )
        return {
            "messages": [AIMessage(content=reply, name="Diagnostic_Agent")],
            "question_count": question_count
        }
    else:
        # Étape finale du diagnostic
        # Analyse sommaire du texte de l'utilisateur pour adapter le mock
        symptom_detected = "Douleurs et inconfort général"
        detected_care = get_interim_care_guidelines.invoke("general")
        
        if "tête" in user_msg.lower() or "migraine" in user_msg.lower():
            symptom_detected = "Céphalées / Migraines aiguës"
            detected_care = get_interim_care_guidelines.invoke("headache")
        elif "fièvre" in user_msg.lower() or "temperature" in user_msg.lower() or "chaud" in user_msg.lower():
            symptom_detected = "Fièvre / Syndrome grippal"
            detected_care = get_interim_care_guidelines.invoke("fever")
        elif "ventre" in user_msg.lower() or "estomac" in user_msg.lower() or "douleur" in user_msg.lower():
            symptom_detected = "Douleurs abdominales / Troubles digestifs"
            detected_care = get_interim_care_guidelines.invoke("abdominal_pain")
            
        diag_summary_mock = (
            f"Symptômes rapportés : {symptom_detected}.\n"
            f"Évolution : Épisode décrit par le patient, intensité modérée.\n"
            f"Facteurs de risques/Dossier : Consultations antérieures analysées."
        )
        
        reply = (
            "Merci pour ces précisions essentielles. Vos symptômes ont été entièrement documentés.\n"
            f"**Soins intermédiaires suggérés immédiatement :**\n{detected_care}\n\n"
            "Je transmets à l'instant votre dossier clinique complet au médecin réviseur pour l'établissement de votre traitement."
        )
        
        return {
            "messages": [AIMessage(content=reply, name="Diagnostic_Agent")],
            "question_count": question_count,
            "diagnostic_summary": diag_summary_mock,
            "interim_care": detected_care
        }
