import os
import sys
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# Charge les variables d'environnement (.env)
load_dotenv()

MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "mcp_server/server.py")

# On utilise le même exécutable Python que celui de l'environnement virtuel actif
PYTHON_EXE = sys.executable 

async def call_mcp_tool(tool_name: str, tool_args: dict) -> str:
    """
    Se connecte au serveur MCP via Stdio, exécute un outil et renvoie le résultat.
    """
    # Configuration des paramètres pour lancer le serveur MCP autonome
    server_params = StdioServerParameters(
        command=PYTHON_EXE,
        args=[MCP_SERVER_PATH],
        env=os.environ.copy()
    )
    
    try:
        # Ouverture du canal Stdio avec le serveur
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialisation de la session MCP
                await session.initialize()
                
                # Appel dynamique de l'outil demandé
                result = await session.call_tool(tool_name, arguments=tool_args)
                
                # Extraction du texte de la réponse du serveur MCP
                if result and result.content:
                    return result.content[0].text
                return "Erreur : Le serveur MCP a renvoyé une réponse vide."
                
    except Exception as e:
        return f"🚨 Erreur de connexion MCP (Stdio) : {str(e)}"

# --- FONCTIONS COROUTINES POUR TES NOEUDS ---

async def call_mcp_consulter_patient(patient_id: str) -> str:
    return await call_mcp_tool("consulter_dossier_patient", {"patient_id": patient_id})

async def call_mcp_verifier_contre_indications(facteurs_risque: str) -> str:
    return await call_mcp_tool("verifier_contre_indications", {"facteurs_risque": facteurs_risque})

async def call_mcp_ajouter_patient(patient_id: str, nom: str, antecedents: str, allergies: str, traitements: str) -> str:
    return await call_mcp_tool("ajouter_nouveau_patient", {
        "patient_id": patient_id,
        "nom": nom,
        "antecedents": antecedents,
        "allergies": allergies,
        "traitements": traitements
    })