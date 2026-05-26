from langchain_core.tools import tool

@tool
def get_patient_records(patient_id: str) -> str:
    """
    Retrieve the simulated medical records, history, and active allergy listings for a given patient ID.
    Use this to understand any pre-existing conditions or contraindications.
    """
    # Factice database lookup
    records = {
        "PAT-001": {
            "name": "Jean Dupont",
            "age": 45,
            "gender": "M",
            "medical_history": [
                "Hypertension artérielle modérée (traitée par Périndopril)",
                "Asthme léger d'effort dans l'enfance"
            ],
            "allergies": [
                "Pénicilline (réaction cutanée type urticaire)",
                "Pollen de graminées"
            ],
            "last_visit": "2026-03-12 (Contrôle tensionnel - normalisé à 125/80 mmHg)"
        },
        "PAT-002": {
            "name": "Marie Martin",
            "age": 32,
            "gender": "F",
            "medical_history": [
                "Migraines chroniques avec aura",
                "Hypothyroïdie fruste (traitée par Lévothyrox 75 µg)"
            ],
            "allergies": [
                "Aspirine (bronchospasme sévère)",
                "Arachides"
            ],
            "last_visit": "2026-01-20 (Bilan thyroïdien de routine)"
        }
    }
    
    patient = records.get(patient_id)
    if not patient:
        return f"Aucun dossier clinique trouvé pour l'identifiant patient {patient_id}. Création d'un dossier temporaire vierge."
    
    return (
        f"--- DOSSIER MÉDICAL DU PATIENT: {patient['name']} ({patient_id}) ---\n"
        f"Âge : {patient['age']} ans | Genre : {patient['gender']}\n"
        f"Antécédents médicaux : {', '.join(patient['medical_history'])}\n"
        f"Allergies connues : {', '.join(patient['allergies'])}\n"
        f"Dernière consultation : {patient['last_visit']}\n"
        f"--------------------------------------------------"
    )
