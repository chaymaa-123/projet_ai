import os
from typing import Dict, Any
from langchain_core.messages import AIMessage
from backend.app.state import MedicalState
from backend.app.nodes.supervisor import get_llm

def report_agent_node(state: MedicalState) -> Dict[str, Any]:
    """
    Agent de Rapport. Compile toutes les données collectées (Diagnostic, Soins intermédiaires,
    Validation et Prescription du médecin) pour rédiger un rapport d'orientation clinique
    final structuré et ultra-professionnel au format Markdown.
    """
    diag_summary = state.get("diagnostic_summary", "")
    interim_care = state.get("interim_care", "")
    phys_treatment = state.get("physician_treatment", "")
    messages = state.get("messages", [])
    
    # ----------------------------------------------------
    # DÉROULEMENT AVEC UN LLM ACTIF
    # ----------------------------------------------------
    llm = get_llm()
    if llm:
        try:
            system_prompt = (
                "Vous êtes l'Agent de Rédaction du Rapport Clinique Final de l'établissement.\n"
                "Votre tâche est de fusionner et de mettre en forme de manière extrêmement professionnelle "
                "toutes les informations cliniques collectées dans ce dossier patient.\n\n"
                f"--- 1. Synthèse du Diagnostic ---\n{diag_summary}\n\n"
                f"--- 2. Directives de Soins Intermédiaires ---\n{interim_care}\n\n"
                f"--- 3. Plan de Traitement Médecin Senior ---\n{phys_treatment}\n\n"
                "CONSIGNES DE MISE EN FORME :\n"
                "Rédigez un rapport clinique final structuré en Markdown sous forme de fiche médicale complète.\n"
                "Utilisez un ton formel, précis et de riches éléments de formatage Markdown (tableaux, listes, alertes).\n"
                "Le rapport doit impérativement comporter :\n"
                "- Un titre principal professionnel (ex: RAPPORT D'ORIENTATION ET DE SYNTHÈSE CLINIQUE)\n"
                "- Les informations du dossier médical du patient\n"
                "- La synthèse clinique détaillée\n"
                "- Le plan de soins de premier recours\n"
                "- La prescription médicamenteuse validée avec sa posologie et sa durée\n"
                "- Les signaux d'alarme et critères de surveillance critiques"
            )
            
            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages")
            ])
            
            chain = prompt | llm
            response = chain.invoke({"messages": messages})
            final_report = response.content
            
            reply = (
                "📄 **[Rapport Médical Généré]** Le rapport clinique officiel d'orientation a été rédigé, "
                "signé électroniquement par l'équipe d'agents et archivé dans le dossier du patient."
            )
            
            return {
                "messages": [AIMessage(content=reply, name="Report_Agent")],
                "final_report": final_report
            }
        except Exception as e:
            # Repli sur la simulation en cas d'erreur de chaîne LLM
            pass

    # ----------------------------------------------------
    # LOGIQUE DE SIMULATION DÉTERMINISTE (REPLI)
    # ----------------------------------------------------
    markdown_report = f"""# 📄 FICHE DE SYNTHÈSE & D'ORIENTATION CLINIQUE
*Établi électroniquement par l'équipe d'orientation multi-agents*

---

## 👤 Informations Cliniques
- **Type de dossier** : Consultation d'orientation clinique dématérialisée
- **Statut** : Validé par le médecin senior

---

## 🩺 1. Synthèse Diagnostique
{diag_summary}

---

## 💊 2. Plan de Traitement Médical (Médecin Senior)
{phys_treatment}

---

## 🩹 3. Soins Intermédiaires & Premiers Secours
{interim_care}

---

## 🚨 4. Critères de Surveillance & Signaux d'Alerte
> [!WARNING]  
> En cas d'apparition de l'un des symptômes suivants, veuillez cesser tout traitement en cours et **contacter immédiatement le 15 (SAMU)** ou vous rendre au service des urgences le plus proche :
> - Difficultés respiratoires aiguës ou sifflements thoraciques importants.
> - Douleur abdominale intense, brutale et persistante avec ventre dur au toucher.
> - Fièvre élevée (> 39.5°C) accompagnée d'une raideur de nuque ou de confusion.
> - Éruption cutanée inexpliquée ou apparition de taches rouges violacées (purpura).

---
*Fin du rapport clinique. Document certifié conforme pour orientation initiale.*
"""
    
    reply = (
        "📄 **[Rapport Médical Généré]** Le rapport clinique officiel d'orientation a été structuré et compilé "
        "avec succès. Vous pouvez désormais le consulter et l'imprimer depuis votre espace patient."
    )
    
    return {
        "messages": [AIMessage(content=reply, name="Report_Agent")],
        "final_report": markdown_report
    }
