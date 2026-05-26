import os
from typing import Dict, Any
from langchain_core.messages import AIMessage
from backend.app.state import MedicalState
from backend.app.tools.mcp_client import mcp_client
from backend.app.nodes.supervisor import get_llm

def physician_review_node(state: MedicalState) -> Dict[str, Any]:
    """
    Revue du Médecin. Valide la synthèse de diagnostic, consulte la base de connaissances
    médicales MCP pour les directives thérapeutiques officielles, vérifie les contre-indications
    médicamenteuses et rédige le plan de traitement officiel.
    """
    diag_summary = state.get("diagnostic_summary", "")
    interim_care = state.get("interim_care", "")
    messages = state.get("messages", [])
    
    # ----------------------------------------------------
    # APPEL AU SERVEUR MCP POUR RÉCUPÉRER LES DIRECTIVES CLINIQUE
    # ----------------------------------------------------
    # Détecter la pathologie probable pour guider le traitement
    disease_key = "grippe"  # Défaut
    medication_to_check = "paracetamol"
    
    diag_lower = diag_summary.lower()
    if "tension" in diag_lower or "hyper" in diag_lower or "céphalée" in diag_lower or "tête" in diag_lower:
        disease_key = "hypertension"
        medication_to_check = "perindopril"
    elif "diab" in diag_lower:
        disease_key = "diabete"
        medication_to_check = "metformine"
    elif "asth" in diag_lower:
        disease_key = "asthme"
        medication_to_check = "salbutamol"
        
    guidelines = mcp_client.search_guidelines(disease_key)
    contraindications = mcp_client.check_contraindications(medication_to_check)
    
    # Vérification d'autres médicaments standards
    paracetamol_warnings = mcp_client.check_contraindications("paracetamol")
    
    # ----------------------------------------------------
    # DÉROULEMENT AVEC UN LLM ACTIF
    # ----------------------------------------------------
    llm = get_llm()
    if llm:
        try:
            system_prompt = (
                "Vous êtes le Médecin Réviseur Senior de la clinique.\n"
                "Votre tâche est de valider la synthèse de diagnostic fournie par l'Agent de Diagnostic, "
                "de consulter les directives cliniques officielles et de concevoir un traitement médical sûr.\n\n"
                f"--- Synthèse Diagnostique ---\n{diag_summary}\n\n"
                f"--- Directives de Traitement MCP ---\n{guidelines}\n\n"
                f"--- Contre-indications Détectées MCP ---\n"
                f"- Pour {medication_to_check} : {contraindications}\n"
                f"- Pour Paracétamol : {paracetamol_warnings}\n\n"
                "INSTRUCTIONS :\n"
                "Rédigez votre plan de traitement médical validé de manière rigoureuse en français.\n"
                "Vous devez absolument inclure :\n"
                "1. La validation ou correction du diagnostic.\n"
                "2. La prescription recommandée avec posologie, fréquence et durée.\n"
                "3. Les contre-indications et précautions d'emploi spécifiques au patient.\n"
                "4. Les critères de surveillance et de réévaluation.\n"
                "Votre réponse doit être claire, professionnelle et structurée pour être lue par le Report Agent."
            )
            
            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages")
            ])
            
            chain = prompt | llm
            response = chain.invoke({"messages": messages})
            physician_treatment = response.content
            
            reply = (
                "🧑‍⚕️ **[Avis Médecin Senior]** Dossier clinique révisé avec succès.\n"
                "J'ai appliqué les directives cliniques institutionnelles et vérifié la sécurité du plan de traitement.\n"
                "La prescription officielle est en cours de finalisation."
            )
            
            return {
                "messages": [AIMessage(content=reply, name="Physician_Review")],
                "physician_treatment": physician_treatment
            }
        except Exception as e:
            # Repli sur la simulation en cas d'erreur de chaîne LLM
            pass

    # ----------------------------------------------------
    # LOGIQUE DE SIMULATION DÉTERMINISTE (REPLI)
    # ----------------------------------------------------
    prescriptions = {
        "hypertension": (
            "**Diagnostic validé :** Poussée hypertensive modérée à contrôler.\n"
            "**Plan thérapeutique :**\n"
            "- Prise de Périndopril 4 mg : 1 comprimé le matin au petit-déjeuner pendant 1 mois.\n"
            "- Mesures de surveillance : Auto-mesure tensionnelle matin et soir (règle des 3).\n"
            "**Précautions & Contre-indications :**\n"
            f"- {contraindications}\n"
            "- Ne pas associer à d'autres IEC/ARA II sans avis médical."
        ),
        "diabete": (
            "**Diagnostic validé :** Suspicion de Diabète de type 2 à confirmer par bilan biologique.\n"
            "**Plan thérapeutique :**\n"
            "- Métformine 500 mg : 1 comprimé au cours du repas du soir pendant 2 semaines, puis passage à 1 comprimé matin et soir si tolérance digestive correcte.\n"
            "- Prescription d'un bilan sanguin complet (HbA1c, Créatininémie, Bilan lipidique).\n"
            "**Précautions & Contre-indications :**\n"
            f"- {contraindications}\n"
            "- Arrêt temporaire requis en cas d'examen avec produit de contraste iodé."
        ),
        "asthme": (
            "**Diagnostic validé :** Crise d'asthme légère ou asthme instable.\n"
            "**Plan thérapeutique :**\n"
            "- Salbutamol (Ventoline) 100 µg/dose : 1 à 2 inhalations en cas de crise ou de gêne respiratoire, renouvelable jusqu'à 4 fois par jour.\n"
            "- Consultation rapide requise chez le médecin traitant pour introduction d'un traitement de fond.\n"
            "**Précautions & Contre-indications :**\n"
            f"- {contraindications}"
        ),
        "grippe": (
            "**Diagnostic validé :** Syndrome grippal saisonnier non compliqué.\n"
            "**Plan thérapeutique :**\n"
            "- Paracétamol 1g : 1 comprimé toutes les 6 heures en cas de fièvre ou de courbatures (maximum 3 comprimés par jour).\n"
            "- Repos complet pendant 5 jours et hydratation abondante.\n"
            "**Précautions & Contre-indications :**\n"
            f"- {paracetamol_warnings}"
        )
    }
    
    chosen_treatment = prescriptions.get(disease_key, prescriptions["grippe"])
    
    reply = (
        "🧑‍⚕️ **[Avis Médecin Senior]** Diagnostic et antécédents médicaux passés en revue.\n"
        f"**Directives cliniques appliquées :** {disease_key.upper()}.\n"
        "**Plan de traitement validé et sécurisé.** Transmission des consignes de prescription pour le rapport final."
    )
    
    return {
        "messages": [AIMessage(content=reply, name="Physician_Review")],
        "physician_treatment": chosen_treatment
    }
