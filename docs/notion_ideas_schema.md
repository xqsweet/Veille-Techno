# 📌 Guide de Configuration : Base de Données Notion "Boîte à Idées"

Ce guide détaille la procédure pour créer la base de données Notion dédiée au suivi des idées du projet **Veille-Techno**, accessible sur **Mac M3, Windows PC et iPhone 17**.

---

## 1. Création de la Base de Données dans Notion

1. Ouvrez votre espace Notion (sur le web ou sur l'application mobile/desktop).
2. Créez une nouvelle page nommée **💡 Boîte à Idées - Veille Techno**.
3. Choisissez le format **Tableau (Table)** ou **Kanban**.
4. Configurez les propriétés suivantes pour la base de données :

| Nom de la Propriété | Type Notion | Options / Valeurs possibles |
| :--- | :--- | :--- |
| **Titre** | `Title` (Titre principal) | Nom de la proposition |
| **Statut** | `Select` | `🟡 À l'étude`, `🟢 Approuvé`, `🔵 En cours`, `🔴 Rejeté`, `✅ Terminé` |
| **Priorité** | `Select` | `🔴 Haute`, `🟠 Moyenne`, `🟢 Basse` |
| **Complexité** | `Select` | `⚡ Faible`, `🛠️ Moyenne`, `🏗️ Élevée` |
| **Impact Codebase** | `Text` | Fichiers ou composants concernés (ex: `main.py`) |
| **Description** | `Text` (Multi-lignes) | Description détaillée de l'idée |
| **Approche Technique** | `Text` (Multi-lignes) | Explication technique et modules concernés |

---

## 2. Association avec l'Intégration API Notion

1. Rendez-vous sur [notion.so/my-integrations](https://www.notion.so/my-integrations).
2. Ouvrez votre intégration existante (ou créez-en une nommée `Veille-Techno-Bot`).
3. Récupérez le **Internal Integration Secret** (`NOTION_TOKEN`).
4. Dans Notion, ouvrez votre page **💡 Boîte à Idées - Veille Techno**.
5. Cliquez sur les **3 petits points (`...`)** en haut à droite ➔ **Connections / Connexions** ➔ Ajoutez votre intégration `Veille-Techno-Bot`.

---

## 3. Récupération de l'ID de la Base de Données

1. Copiez le lien de votre base de données Notion.
2. L'URL ressemble à ceci : `https://www.notion.so/workspace/a1b2c3d4e5f67890123456789abcdef0?v=...`
3. L'identifiant de la base de données (`NOTION_IDEAS_DATABASE_ID`) est la suite de 32 caractères alphanumériques située entre le nom de domaine et le `?v=`.
4. Ajoutez-le dans votre fichier `.env` :

```env
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_IDEAS_DATABASE_ID=a1b2c3d4e5f67890123456789abcdef0
```
