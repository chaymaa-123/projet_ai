from langgraph.graph import StateGraph, END
from backend.app.state import MedicalState
from backend.app.nodes.supervisor import supervisor_node
from backend.app.nodes.diagnostic_agent import diagnostic_agent_node
from backend.app.nodes.physician_review import physician_review_node
from backend.app.nodes.report_agent import report_agent_node

# 1. Initialisation du graphe d'état clinique
workflow = StateGraph(MedicalState)

# 2. Ajout des nœuds (Agents)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("diagnostic_agent", diagnostic_agent_node)
workflow.add_node("physician_review", physician_review_node)
workflow.add_node("report_agent", report_agent_node)

# 3. Définition du point d'entrée du graphe
workflow.set_entry_point("supervisor")

# 4. Ajout des transitions de retour vers le Superviseur
# Après chaque action, le contrôle est redonné au superviseur pour analyse
workflow.add_edge("diagnostic_agent", "supervisor")
workflow.add_edge("physician_review", "supervisor")
workflow.add_edge("report_agent", "supervisor")

# 5. Définition des transitions conditionnelles depuis le Superviseur
# Il aiguille le flux en lisant l'attribut 'next' du State
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state.get("next", "diagnostic_agent"),
    {
        "diagnostic_agent": "diagnostic_agent",
        "physician_review": "physician_review",
        "report_agent": "report_agent",
        "FINISH": END
    }
)

# 6. Compilation finale du graphe clinique
graph = workflow.compile()
