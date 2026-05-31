import os
import sys
import pymysql
from mcp.server import Server
import mcp.types as types

# Utilisation de la classe de base Server (beaucoup plus stable sous Windows Stdio)
app = Server("Serveur-Directives-Cliniques")

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="cabinet_medical",
        cursorclass=pymysql.cursors.DictCursor
    )

CONTRE_INDICATIONS = {
    "hta": "ÉVITER absolument les Anti-Inflammatoires Non Stéroïdiens (AINS) comme l'Ibuprofène.",
    "pénicilline": "ALLERGIE GRAVE : Bannir tous les antibiotiques de la famille des Bêta-lactamines.",
    "aspirine": "ALLERGIE : Risque de syndrome de Widal. Éviter les salicylés.",
    "asthme": "🚨 ATTENTION RISQUE CRITIQUE : Contre-indication absolue des Bêta-bloquants."
}

# --- ENREGISTREMENT DES OUTILS (MODE STANDARD) ---

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="ajouter_nouveau_patient",
            description="Insère un nouveau patient dans MySQL XAMPP",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "nom": {"type": "string"},
                    "antecedents": {"type": "string"},
                    "allergies": {"type": "string"},
                    "traitements": {"type": "string"}
                },
                "required": ["patient_id", "nom"]
            }
        ),
        types.Tool(
            name="consulter_dossier_patient",
            description="Recherche un patient dans MySQL et renvoie sa fiche",
            inputSchema={
                "type": "object",
                "properties": {"patient_id": {"type": "string"}},
                "required": ["patient_id"]
            }
        ),
        types.Tool(
            name="verifier_contre_indications",
            description="Analyse les risques cliniques",
            inputSchema={
                "type": "object",
                "properties": {"facteurs_risque": {"type": "string"}},
                "required": ["facteurs_risque"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "ajouter_nouveau_patient":
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO patients VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(sql, (arguments["patient_id"], arguments["nom"], arguments.get("antecedents",""), arguments.get("allergies",""), arguments.get("traitements","")))
            connection.commit()
            msg = f"Succès : Le patient {arguments['nom']} a été enregistré."
        except Exception as e:
            msg = f"Erreur MySQL : {e}"
        finally:
            connection.close()
        return [types.TextContent(type="text", text=msg)]

    elif name == "consulter_dossier_patient":
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM patients WHERE patient_id = %s", (arguments["patient_id"],))
                p = cursor.fetchone()
            if not p:
                msg = f"Aucun dossier trouvé pour {arguments['patient_id']}."
            else:
                msg = f"Dossier Réel MySQL de {p['nom']} :\n- Antécédents : {p['antecedents']}\n- Allergies : {p['allergies']}"
        except Exception as e:
            msg = f"Erreur : {e}"
        finally:
            connection.close()
        return [types.TextContent(type="text", text=msg)]

    elif name == "verifier_contre_indications":
        alertes = []
        risques = arguments.get("facteurs_risque", "").lower()
        for cle, text in CONTRE_INDICATIONS.items():
            if cle in risques:
                alertes.append(text)
        msg = "🚨 ALERTE :\n" + "\n".join(f"- {a}" for a in alertes) if alertes else "Aucune contre-indication majeure."
        return [types.TextContent(type="text", text=msg)]

if __name__ == "__main__":
    # Correction du nom de la fonction officielle du SDK d'Anthropic
    from mcp.server.stdio import stdio_server
    import asyncio
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
            
    asyncio.run(main())