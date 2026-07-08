# Kiwix_tool_rag
Kiwix rag systeme for openwebui fast clean 
# Kiwix RAG Tool for Open WebUI

Ce script est un "Tool" pour Open WebUI permettant de réaliser du RAG (Retrieval-Augmented Generation) sur une base de données de documentation locale servie par Kiwix.

## Fonctionnalités
- **Nettoyage HTML avancé** : Supprime automatiquement les éléments parasites (scripts, menus, boutons) pour ne garder que le contenu utile.
- **Chunking Intelligent** : Découpe les articles en blocs avec chevauchement (overlap) pour préserver le contexte technique.
- **Configuration dynamique** : Paramétrable via les "Valves" d'Open WebUI (pas besoin de modifier le code pour changer de serveur ou de livre).

## Installation
1. Dans Open WebUI, allez dans **Workspace > Tools**.
2. Cliquez sur **Create a tool**.
3. Copiez-collez le contenu de `kiwix_tool.py`.
4. Dans les paramètres (Valves) du tool, indiquez :
   - **KIWIX_BASE_URL** : L'adresse de votre serveur Kiwix (ex: `http://192.168.1.50`).
   - **DEFAULT_BOOK** : L'ID de votre fichier ZIM par défaut.

## Schéma de fonctionnement
