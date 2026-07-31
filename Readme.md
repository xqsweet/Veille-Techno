# 🚀 Automate de Veille Technologique Quotidienne (V5)

Pipeline Serverless 100 % gratuit pour collecter, analyser et synthétiser l'actualité IT quotidienne directement dans Notion avec mémoire inter-jours, bilan hebdomadaire des failles critiques et notifications Push sur Telegram.

---

## 📌 Architecture V5 & Flux de Données

[cron-job.org] (18h22 Europe/Paris)
│ (API REST GitHub / workflow_dispatch)
▼
[GitHub Actions Runner] ──► Ingestion Asynchrone & Fail-Safe (20 Flux RSS / aiohttp + requests fallback)
│
├──► [Notion API] ──► Déduplication page du jour + Lecture mémoire J-1
│
├──► [Google AI Studio] (Gemini 3.5 Flash Lite)
│       ├──► Dédoublonnage intra/inter-jours & Tri par urgence (🔴 CRITIQUE > 🟠 ÉVOLUTION > 🟢 INFO)
│       └──► [Dimanche] Scan 7 derniers jours ➔ Bilan Vulnérabilités "Impact Utilisateur"
│
├──► [Notion API] ──► Publication page "Veille Tech - JJ/MM/AAAA" (Toggles, Callouts & Rich Text)
│
└──► [Telegram Bot API] ──► Push Notification & Rapport d'exécution (~18h22 / Fallback Texte Brut)

---

## 🔑 Key Features & Évolutions V5

- **⚡ Orchestration Externe Ultra-Précise :** Déclenchement à 18h22 (Europe/Paris) via `cron-job.org` et l'API REST GitHub (`workflow_dispatch`), éliminant tout retard de planification.
- **📡 Ingestion Asynchrone Haute Disponibilité :** Récupération par `aiohttp` avec fallback synchrone automatique non-bloquant (`requests`) en cas d'erreur réseau/SSL.
- **🚨 Bilan Hebdomadaire des Failles (Dimanche) :** Extraction automatique des failles 🔴 `[CRITIQUE]` recensées dans Notion sur les 7 derniers jours, vulgarisées sous l'angle "Impact Utilisateur" (Mac, iPhone, PC, Box Internet, statut du patch ✅/❌).
- **🧠 Mémoire Inter-Jours (J-1) & Tri IA :** Injection du résumé J-1 dans Gemini 3.5 Flash Lite pour éviter les doublons et hiérarchiser les sujets par niveau d'urgence.
- **📝 Publication Notion Premium :** Mise en page automatique avec Toggles déroulants numérotés, métadonnées (temps de lecture, tags), et parsing Regex natif pour préserver le gras.
- **📲 Push Telegram avec Fallback :** Notification directe sur écran de verrouillage avec fallback automatique en texte brut en cas d'erreur de formatage Markdown.

---

## 🛠️ Configuration & Secrets GitHub

### 1. External Trigger (cron-job.org)
1. Crée un compte gratuit sur [cron-job.org](https://cron-job.org).
2. Crée un cron planifié à **18h22** (Fuseau horaire : `Europe/Paris`).
3. Configure une requête **POST** vers l'URL API GitHub :
   `https://api.github.com/repos/{owner}/{repo}/dispatches`
4. Ajoute les entêtes HTTP :
   - `Authorization: Bearer <GITHUB_PAT>`
   - `Accept: application/vnd.github.v3+json`
5. Body JSON : `{"event_type": "daily_veille"}`

### 2. Bot Telegram
1. Sur Telegram, contacte `@BotFather`, lance `/newbot` et note le token : `TELEGRAM_BOT_TOKEN`.
2. Contacte `@userinfobot`, lance-le et note ton ID : `TELEGRAM_CHAT_ID`.

### 3. Notion API
1. Prépare une page parent "Journal de Veille" dans Notion.
2. Crée une intégration sur [notion.so/my-integrations](https://www.notion.so/my-integrations) et note le token : `NOTION_TOKEN` (ou `NOTION_API_TOKEN`).
3. Sur la page Notion parent ➔ `...` ➔ `Connecter à` ➔ sélectionne ton intégration.
4. Copie l'ID à 32 caractères dans l'URL de la page : `NOTION_DATABASE_ID` (ou `NOTION_PAGE_ID`).

### 4. Google AI Studio
1. Génère une clé API gratuite sur [aistudio.google.com](https://aistudio.google.com) : `GEMINI_API_KEY`.

### 5. Variables d'Environnement GitHub
Ajoute ces 5 secrets dans **Settings ➔ Secrets and variables ➔ Actions** :
- `GEMINI_API_KEY`
- `NOTION_TOKEN` (ou `NOTION_API_TOKEN`)
- `NOTION_DATABASE_ID` (ou `NOTION_PAGE_ID`)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

---

## 📊 Matrice Détallée des Composants

| Étape | Composant | Spécification Technique | Rôle & Sécurité |
| :--- | :--- | :--- | :--- |
| **1. Orchestration** | cron-job.org + GitHub API | Webhook REST (18h22 Europe/Paris) | Déclenchement instantané via `workflow_dispatch`. |
| **2. Ingestion RSS** | `aiohttp` + `requests` + `feedparser` | 20 flux FR & US (fenêtre 36h) | Collecte asynchrone fail-safe avec fallback synchrone non-bloquant. |
| **3. Mémoire & State** | Notion API REST | `ZoneInfo("Europe/Paris")` | Remplacement/archivage auto du jour + lecture mémoire J-1. |
| **4. Moteur IA** | Google Gemini API | `gemini-3.5-flash-lite` | Dédoublonnage, tri par criticité et bilan hebdo des failles. |
| **5. Parser Rich Text** | Regex Markdown ➔ JSON | Convertisseur natif Notion | Conversion du Markdown (`**gras**`, liens) vers objets `rich_text`. |
| **6. Restitution** | Notion REST API | Page native avec Callouts & Toggles | Génération de la page quotidienne et encadré bilan le dimanche. |
| **7. Alerting** | Telegram Bot API | Push HTTPS (Markdown + Fallback Plain) | Rapport quotidien, alerte failles hebdo et résilience d'envoi. |
| **8. Consultation** | Apps Notion | iOS, macOS, Windows | Lecture multi-appareil synchronisée en temps réel. |

---

## 🧪 Exécution Manuelle & Test

Dans l'onglet **Actions** de ton dépôt GitHub, sélectionne le workflow **Daily Tech Watch Automation** et clique sur **Run workflow**.