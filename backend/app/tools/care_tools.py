from langchain_core.tools import tool

@tool
def get_interim_care_guidelines(symptom_category: str) -> str:
    """
    Retrieve clinical first-line interim care guidelines and safety signals for a specific symptom category
    (e.g., 'fever', 'headache', 'abdominal_pain', 'cough').
    Use this to obtain pre-approved self-care recommendations for the patient while they await final treatment.
    """
    guidelines = {
        "fever": (
            "1. Hydratation abondante (eau, tisanes, bouillons).\n"
            "2. Repos au lit dans une pièce fraîche (18-20°C) et aérée.\n"
            "3. Vêtements légers (éviter de trop couvrir le patient).\n"
            "4. Prise de Paracétamol (500mg à 1g toutes les 6 heures si nécessaire, max 3g/jour en automédication) - vérifier l'absence d'allergie ou de contre-indication hépatique.\n"
            "⚠️ Signaux d'alerte (consulter en urgence) : Fièvre > 40°C, raideur de nuque, confusion, photophobie, ou apparition de taches rouges cutanées (purpura)."
        ),
        "headache": (
            "1. Repos dans une pièce calme, sombre et fraîche.\n"
            "2. Application d'une compresse froide sur le front ou les tempes.\n"
            "3. Hydratation (boire un grand verre d'eau).\n"
            "4. Paracétamol (500mg à 1g, max 3g/jour) ou Ibuprofène (200 à 400mg, max 1200mg/jour) si pas de contre-indication (ex: asthme, ulcère, grossesse).\n"
            "⚠️ Signaux d'alerte (consulter en urgence) : Céphalée soudaine et d'intensité maximale d'emblée ('coup de tonnerre'), déficit neurologique (trouble de parole, de vision), fièvre associée."
        ),
        "abdominal_pain": (
            "1. Diète légère (privilégier riz blanc, compote, bouillons clairs) ; éviter les produits laitiers, gras ou épicés.\n"
            "2. Application d'une bouillotte tiède sur l'abdomen.\n"
            "3. Prise d'un antispasmodique type Phloroglucinol (Spasfon) si douleurs de type crampes.\n"
            "4. Éviter la prise d'anti-inflammatoires (AINS) qui peuvent aggraver une éventuelle irritation digestive.\n"
            "⚠️ Signaux d'alerte (consulter en urgence) : Douleur brutale et très intense, abdomen dur au toucher ('ventre de bois'), fièvre associée, vomissements répétés ou sang dans les selles."
        ),
        "cough": (
            "1. Hydratation régulière pour fluidifier les sécrétions (boissons chaudes avec du miel).\n"
            "2. Surélévation de la tête du lit pour la nuit.\n"
            "3. Humidification de l'air de la chambre.\n"
            "4. Lavage de nez régulier au sérum physiologique.\n"
            "⚠️ Signaux d'alerte (consulter en urgence) : Difficultés respiratoires importantes (dyspnée), sifflements à l'expiration, crachats sanglants, ou toux persistante accompagnée d'une altération de l'état général."
        )
    }
    
    cat = symptom_category.lower().strip()
    # Find partial matches if exact match is not found
    for key, value in guidelines.items():
        if key in cat or cat in key:
            return f"--- RECOMMANDATIONS DE PREMIER RECOURS POUR : {key.upper()} ---\n{value}\n--------------------------------------------------"
            
    return (
        "--- RECOMMANDATIONS GÉNÉRALES DE SOINS DE PREMIER RECOURS ---\n"
        "1. Se reposer et éviter tout effort physique intense.\n"
        "2. Maintenir une bonne hydratation en buvant régulièrement de l'eau.\n"
        "3. Surveiller l'évolution des symptômes deux fois par jour (température, douleur).\n"
        "4. En cas de doute ou d'aggravation, contacter le médecin traitant ou appeler le 15 (SAMU).\n"
        "--------------------------------------------------------------"
    )
