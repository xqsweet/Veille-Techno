# 💡 Boîte à Idées & Roadmap

Ce fichier sert de registre pour centraliser toutes les idées d'évolutions, d'améliorations et de nouvelles fonctionnalités pour le projet **Veille-Techno**.

---

## 📝 Modèle pour Ajouter une Nouvelle Idée

Copier-coller le bloc ci-dessous lors de l'ajout d'une nouvelle proposition :

```markdown
### 💡 [Titre de l'idée]

- **Statut :** 🟡 À l'étude | 🟢 Approuvé | 🔵 En cours | 🔴 Rejeté | ✅ Terminé
- **Priorité :** 🔴 Haute | 🟠 Moyenne | 🟢 Basse
- **Complexité :** ⚡ Faible | 🛠️ Moyenne | 🏗️ Élevée
- **Impact Codebase :** [Fichiers ou composants concernés]

#### Description
[Description détaillée du besoin et du problème résolu.]

#### Approche Technique Pressentie
[Explication des composants à modifier ou ajouter (APIs, scripts, workflows, etc.).]
```

---

## 📌 Idées & Évolutions Proposées

### 💡 Bot Telegram Interactif Bidirectionnel (À la demande & Bookmark)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟠 Moyenne
- **Complexité :** 🏗️ Élevée
- **Impact Codebase :** Élevé (`main.py` / création d'un webhook Telegram dédié ou d'un worker serverless)

#### Description
Transformer le bot Telegram (actuellement à sens unique pour les notifications) en un assistant interactif bidirectionnel. L'utilisateur pourra interagir en temps réel avec la veille et la mémoire Notion directement depuis Telegram.

#### Fonctionnalités Visées
1. **Recherche & Synthèse à la demande :**
   - Commande `/recherche <mot-clé>` pour interroger les synthèses précédentes dans Notion via Gemini.
   - Commande `/resume_7jours` pour générer un bilan express personnalisé sur les 7 derniers jours.
2. **Gestion Dynamique des Flux RSS :**
   - Commande `/add_feed <url>` pour ajouter un flux RSS directement sans modifier le code source.
   - Commande `/list_feeds` pour consulter les flux actifs.
3. **Mise en Favoris (Bookmark) :**
   - Ajout d'un bouton inline Telegram sous la notification quotidienne (`📌 Sauvegarder dans Notion`) pour ajouter l'article directement dans une section "Favoris" dédiée de la page Notion.

#### Approche Technique Pressentie
- Mettre en place un endpoint Webhook serverless léger (ex: Cloudflare Workers gratuit ou Vercel Serverless Function) ou exploiter `workflow_dispatch` de l'API REST GitHub.
- Adapter `main.py` ou créer un script dédié pour gérer la réception des updates Telegram (`telegram.Bot` API).
- Connecter les commandes au client Notion et à l'API Gemini.
