import os
from mcp.server.fastmcp import FastMCP

# Initialisation du serveur MCP avec FastMCP
mcp = FastMCP("Clinical Guidelines & Treatment Knowledge Base")

# Base de connaissances cliniques simulée
CLINICAL_GUIDELINES = {
    "hypertension": (
        "Recommandations de traitement de l'HTA (HAS) :\n"
        "1. Mesures hygiéno-diététiques pendant 3 mois (sel < 6g/j, activité physique, perte de poids).\n"
        "2. Monothérapie de 1ère intention : IEC (ex: Périndopril), ARA II (ex: Valsartan), Inhibiteur Calcique (ex: Amlodipine) ou Diurétique thiazidique.\n"
        "3. En cas de non-contrôle à 1 mois : Association de deux classes (Bithérapie).\n"
        "⚠️ Attention : Contre-indication absolue des IEC/ARA II chez la femme enceinte ou en cas d'angioedème."
    ),
    "diabete": (
        "Recommandations de prise en charge du Diabète de type 2 (HAS) :\n"
        "1. Mesures hygiéno-diététiques d'abord (alimentation équilibrée, exercice physique régulier).\n"
        "2. Traitement de 1ère intention : Métformine en monothérapie (si non tolérée, envisager sulfamide ou inhibiteur DPP-4).\n"
        "3. Cible d'HbA1c : Généralement < 7.0% (à individualiser selon le profil du patient).\n"
        "⚠️ Attention : Risque d'acidose lactique avec la Métformine en cas d'insuffisance rénale sévère (DFG < 30 ml/min)."
    ),
    "asthme": (
        "Recommandations GINA pour l'Asthme chronique :\n"
        "1. Traitement de crise (soulagement) : Bronchodilatateur de courte durée d'action (B2-mimétique type Salbutamol/Ventoline) à la demande.\n"
        "2. Traitement de fond (contrôle) : Corticoïde inhalé (ex: Fluticasone, Budésonide) à faible dose quotidiennement.\n"
        "3. En cas d'exacerbation sévère : Recours à la corticothérapie orale courte (5-7 jours) et réévaluation rapide."
    ),
    "grippe": (
        "Prise en charge de la Grippe saisonnière :\n"
        "1. Traitement symptomatique primordial : Repos, réhydratation, antipyrétiques (Paracétamol).\n"
        "2. Traitement antiviral (Oseltamivir/Tamiflu) : Indiqué uniquement chez les patients à haut risque de complications (âgés, insuffisants cardiaques/respiratoires) débuté dans les 48h suivant les premiers symptômes.\n"
        "3. Vaccination annuelle préventive recommandée pour les populations cibles."
    )
}

@mcp.tool()
def search_clinical_guidelines(disease_query: str) -> str:
    """
    Search and retrieve evidence-based clinical guidelines and recommendations for a disease.
    Available queries: 'hypertension', 'diabete', 'asthme', 'grippe'.
    """
    query = disease_query.lower().strip()
    
    # Recherche approximative
    for key, text in CLINICAL_GUIDELINES.items():
        if key in query or query in key:
            return f"=== DIRECTIVES CLINIQUES OFFICIELLES POUR : {key.upper()} ===\n{text}"
            
    return (
        f"Aucune directive clinique spécifique trouvée pour '{disease_query}'.\n"
        f"Directives disponibles : {', '.join(CLINICAL_GUIDELINES.keys())}.\n"
        f"Veuillez vous référer aux recommandations générales de la HAS (Haute Autorité de Santé)."
    )

@mcp.tool()
def list_contraindications(substance: str) -> str:
    """
    Check and list major medical contraindications and warnings for common clinical substances or medications.
    """
    subs = substance.lower().strip()
    
    contraindications = {
        "paracetamol": "Insuffisance hépatocellulaire sévère, allergie connue au paracétamol ou à ses excipients.",
        "ibuprofene": (
            "Insuffisance cardiaque sévère, insuffisance rénale ou hépatique sévère, "
            "antécédents d'hémorragie ou d'ulcère gastroduodénal en lien avec un traitement par AINS, "
            "dernier trimestre de grossesse, asthme déclenché par l'aspirine."
        ),
        "perindopril": "Grossesse (2ème et 3ème trimestres), antécédent d'angioedème lié à la prise d'un IEC, sténose bilatérale de l'artère rénale.",
        "aspirine": "Ulcère gastroduodénal en évolution, maladie hémorragique, insuffisance rénale/hépatique/cardiaque sévère, grossesse dès le 6ème mois.",
        "metformine": "Acidose métabolique aiguë, insuffisance rénale sévère (DFG < 30 mL/min), déshydratation, infection grave, insuffisance cardiaque instable."
    }
    
    for key, text in contraindications.items():
        if key in subs or subs in key:
            return f"⚠️ CONTRE-INDICATIONS POUR LA SUBSTANCE '{key.upper()}' :\n{text}"
            
    return f"Aucune contre-indication spécifique enregistrée dans la base MCP locale pour la substance '{substance}'."

if __name__ == "__main__":
    # Lancement du serveur MCP en mode standard (stdio)
    mcp.run()
