# Instructions du Projet Veille-Techno

## Gestion de la Boîte à Idées & Roadmap
- La source de vérité officielle pour les idées et évolutions est la base de données Notion (interrogeable via `scripts/notion_ideas.py`).
- Dès que l'utilisateur mentionne ses idées, sa feuille de route, sa boîte à idées ou demande de consulter/ajouter des propositions, l'agent doit utiliser `python scripts/notion_ideas.py` pour lister ou modifier la base Notion en temps réel.
- Le fichier `roadmap/boite-a-idees.md` sert d'export/backup Markdown local.
