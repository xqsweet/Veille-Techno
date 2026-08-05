# Instructions du Projet Veille-Techno

## Gestion de la Boîte à Idées & Roadmap
- La source de vérité officielle pour les idées et évolutions est la base de données Notion.
- Dès que l'utilisateur mentionne ses idées, sa feuille de route, sa boîte à idées ou demande de consulter/ajouter des propositions :
  1. Utiliser en priorité le serveur MCP Notion (`notion-mcp-server`) pour interroger et modifier directement la base Notion en temps réel.
  2. Utiliser `python scripts/notion_ideas.py` uniquement en secours (fallback) si le serveur MCP est indisponible.
- Le fichier `roadmap/boite-a-idees.md` sert d'export/backup Markdown local.

### 📌 Valeurs Strictes des Statuts Notion (Base "Boîte à Idées")
Lors de la mise à jour de la propriété `Statut` d'une carte dans la base Notion via le serveur MCP, utiliser **EXACTEMENT** les libellés de sélection suivants (avec leurs emojis et préfixes) pour éviter la création de doublons ou de nouvelles colonnes grisées :
- `🟡 À l'étude` (Jaune)
- `🟢 Approuvé` (Vert)
- `🔵 En cours` (Bleu)
- `🔴 Rejeté` (Rouge)
- `✅ Terminé` (Vert)
