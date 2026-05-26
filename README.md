# 🏥 Système d'Orientation Clinique Multi-Agents (LangGraph & MCP)

Ce projet est un prototype académique d'orientation clinique multi-agents conçu selon les consignes du **Pr. YOUSSFI**. Il met en œuvre une équipe d'agents spécialisés coordonnés par un agent **Superviseur**, s'appuyant sur **LangGraph** pour la gestion d'états cycliques et le protocole **MCP (Model Context Protocol)** pour la vérification des directives cliniques et des contre-indications.

---

## 📐 Architecture du Projet

L'arborescence des dossiers et fichiers générée correspond exactement à la structure recommandée :

```
project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── graph.py               # Assemblage et compilation du graphe LangGraph
│   │   ├── state.py               # Structure stricte de l'état (MedicalState)
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── supervisor.py       # Agent superviseur clinique
│   │   │   ├── diagnostic_agent.py # Agent de diagnostic et collecte de symptômes
│   │   │   ├── physician_review.py # Agent médecin senior de validation des soins
│   │   │   └── report_agent.py     # Agent de rédaction du rapport de synthèse
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── patient_tools.py    # Outils d'interrogation de dossiers factices
│   │   │   ├── care_tools.py       # Outils cliniques de premier recours
│   │   │   └── mcp_client.py       # Client d'intégration du serveur MCP
│   │   └── api.py                 # Serveur API FastAPI connectant le graphe
│   ├── langgraph.json             # Configuration de déploiement LangGraph Studio
│   └── requirements.txt           # Dépendances Python du backend
├── mcp_server/
│   ├── server.py                  # Serveur MCP autonome de directives cliniques
│   └── data/                      # Base de données ou fichiers locaux
├── frontend/
│   └── app.py                     # Interface utilisateur Premium avec Streamlit
└── README.md                      # Guide d'utilisation et de lancement
```

---

## 🧬 Description de l'État Médical (`MedicalState`)

Le cœur du graphe de décision repose sur la structure stricte définie dans le sujet de cours :

```python
class MedicalState(TypedDict, total=False):
    messages: Annotated[list, add_messages]        # Historique des dialogues (Langchain Core)
    next: Literal[                                 # Prochaine étape déterminée par le superviseur
        "diagnostic_agent",
        "physician_review",
        "report_agent",
        "FINISH"
    ]
    question_count: int                            # Nombre de questions posées au patient
    interim_care: str                              # Guide de soins intermédiaires temporaires
    diagnostic_summary: str                        # Synthèse de recueil des symptômes
    physician_treatment: str                       # Plan thérapeutique validé par le médecin
    final_report: str                              # Fiche médicale Markdown finale générée
```

---

## 🚀 Guide de Démarrage et Lancement

### 1. Installation des Dépendances
Nous vous recommandons de créer un environnement virtuel Python propre.

**Sous Windows (PowerShell) :**
```powershell
# Création de l'environnement virtuel
python -m venv .venv

# Activation de l'environnement virtuel
.venv\Scripts\Activate.ps1

# Installation de toutes les dépendances
pip install -r backend/requirements.txt
```

### 2. Configuration des Variables d'Environnement
Créez un fichier `.env` à la racine du projet ou configurez vos clés directement depuis l'interface Streamlit dans le panneau latéral.
```ini
OPENAI_API_KEY=votre_cle_openai
# OU
GEMINI_API_KEY=votre_cle_gemini
```
*Note : Si aucune clé d'API n'est configurée, l'application bascule automatiquement sur un mode de simulation clinique déterministe extrêmement réaliste pour vous garantir un fonctionnement fluide en toute circonstance !*

### 3. Lancement des Composants (Dans des terminaux séparés)

#### Étape A : Démarrer le serveur de connaissances MCP
Le serveur MCP autonome fournit les directives officielles de soins et la vérification des contre-indications.
```powershell
# S'assurer d'être à la racine du projet et d'avoir activé le .venv
python mcp_server/server.py
```

#### Étape B : Démarrer le backend FastAPI
L'API FastAPI héberge le graphe LangGraph clinique et l'exécute de façon centralisée.
```powershell
# Lancement de l'API avec rechargement automatique en développement
uvicorn backend.app.api:app --reload --port 8000
```

#### Étape C : Démarrer le frontend Streamlit
L'application Streamlit premium sert d'interface graphique de démonstration.
```powershell
# Lancement du frontend
streamlit run frontend/app.py
```
L'interface s'ouvre automatiquement dans votre navigateur par défaut à l'adresse [http://localhost:8501](http://localhost:8501).

---

## 🎓 Scénario d'Orientation Clinique pour Démonstration

Pour réaliser une démonstration fluide et impressionner votre jury :

1. **Sélection du Patient** : Dans la barre latérale gauche, sélectionnez **Jean Dupont (PAT-001)**. Le système charge automatiquement ses antécédents médicaux (Hypertension artérielle) et ses allergies connues (Allergique à la Pénicilline).
2. **Premier Message Patient** : Écrivez dans le chat : *"J'ai d'affreuses migraines et très chaud depuis ce matin."*
3. **Traitement par le Diagnostic Agent** :
   - Le Superviseur oriente le flux vers le `diagnostic_agent`.
   - L'agent consulte le dossier clinique et vous demande des précisions sur vos symptômes tout en incrémentant le compteur de questions.
4. **Réponse Patient** : Répondez : *"La douleur est sur les tempes, à environ 7/10, et ma tension semble plus haute."*
5. **Génération de la Synthèse & Soins Intermédiaires** :
   - L'agent de diagnostic estime avoir assez d'éléments. Il formule des conseils de premiers secours adaptés à la migraine.
   - Il crée la `diagnostic_summary` et passe la main au Superviseur.
6. **Validation par le Physician Review** :
   - Le Superviseur détecte que la synthèse diagnostique est prête et oriente vers le `physician_review`.
   - Le médecin senior consulte la base de connaissances **MCP** pour vérifier les directives de l'hypertension et les contre-indications médicamenteuses (comme la sensibilité à l'aspirine ou aux antibiotiques selon le patient).
   - Il prescrit officiellement un plan thérapeutique adapté (Périndopril 4mg, etc.) exempt de contre-indications.
7. **Rédaction par le Report Agent** :
   - Le Superviseur transmet le dossier validé au `report_agent`.
   - L'agent compile l'ensemble des données pour générer la **Fiche de Synthèse Médicale** complète.
8. **Consultation** : L'onglet "Fiche Médicale Finale" s'illumine en vert à droite de l'écran, vous présentant le rapport final mis en forme de manière somptueuse !
