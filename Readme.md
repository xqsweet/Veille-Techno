# 🚀 Automate de Veille Technologique Quotidienne (V4)

Pipeline Serverless 100 % gratuit pour collecter, analyser et synthétiser l'actualité IT quotidienne directement dans Notion avec mémoire inter-jours et notifications Push sur Telegram.

---

## 📌 Architecture V4 & Flux de Données

[cron-job.org] (18h22 Europe/Paris)
│ (API REST GitHub / workflow_dispatch)
▼
[GitHub Actions Runner] ──► Ingestion & Fail-Safe (19 Flux RSS / HTTP 200 / bozo check)
│
├──► [Notion API] ──► Check doublon du jour + Lecture de la mémoire J-1
│
├──► [Google AI Studio] (Gemini 3.5 Flash Lite)
│       └──► Dédoublonnage intra/inter-jours & Tri par urgence 🔴 🟠 🟢
│
├──► [Notion API] ──► Publication page "Veille Tech - JJ/MM/AAAA" (Toggles & Liens)
│
└──► [Telegram Bot API] ──► Notification Push & Rapport d'exécution (~18h22)
### 🔑 Points forts de la V4 :
- **Orchestration externe ultra-précise :** Déclenchement à 18h22 FR via `cron-job.org` et l'API REST GitHub (`workflow_dispatch`), éliminant totalement le retard aléatoire des crons natifs GitHub.
- **Fail-Safe & Tolérance aux pannes :** Timeout HTTP de 4s par flux, validation du code HTTP 200 et détection `bozo` (`feedparser`) avec alerte en fin de message Telegram pour les flux hors-ligne.
- **Mémoire Inter-Jours (J-1) :** Interrogation automatique de la page Notion de la veille (`get_yesterday_notion_summary()`) transmise au prompt IA pour éviter la répétition des sujets déjà traités.
- **Dédoublonnage & Tri par Criticité :** Classification dans 5 catégories IT (Systèmes, IA, Cybersécurité, DevOps, Hardware) avec tri automatique par urgence (`🔴 [CRITIQUE]` > `🟠 [ÉVOLUTION]` > `🟢 [INFO]`).
- **Anti-Doublon Notion :** Exécution annulée proprement si la page du jour existe déjà (`check_notion_duplicate()`).

---

## 🛠️ Configuration & Secrets

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
1. Sur Telegram, cherche `@BotFather`, lance `/newbot` et note le token : `TELEGRAM_BOT_TOKEN`.
2. Cherche `@userinfobot`, lance-le et note ton ID : `TELEGRAM_CHAT_ID`.

### 3. Notion API
1. Prépare une page parent "Journal de Veille" dans Notion.
2. Crée une intégration sur `notion.so/my-integrations` et note le secret : `NOTION_API_TOKEN`.
3. Sur la page Notion parent ➔ `...` ➔ `Connecter à` ➔ sélectionne ton intégration.
4. Copie l'ID à 32 caractères dans l'URL de la page : `NOTION_PAGE_ID`.

### 4. Google AI Studio
1. Génère une clé API gratuite sur [aistudio.google.com](https://aistudio.google.com) : `GEMINI_API_KEY`.

### 5. Dépôt GitHub & Secrets
Ajoute les 5 secrets dans **Settings ➔ Secrets and variables ➔ Actions** :
- `GEMINI_API_KEY`
- `NOTION_API_TOKEN`
- `NOTION_PAGE_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

---

## 📊 Matrice des Composants

| Étape | Composant | Spécification Technique | Rôle & Sécurité |
| :--- | :--- | :--- | :--- |
| **1. Orchestration** | cron-job.org + GitHub API | Webhook REST (18h22 Europe/Paris) | Déclenchement à la seconde près via `workflow_dispatch`. |
| **2. Collecte RSS** | Python (`feedparser`) | 19 flux FR & US (24h glissantes) | Timeout 4s, check HTTP 200 & bozo check. |
| **3. Mémoire & State** | Notion API Integration | `ZoneInfo("Europe/Paris")` | Anti-doublon et extraction de la mémoire J-1. |
| **4. Moteur IA** | Google Gemini API | `gemini-3.5-flash-lite` | Dédoublonnage sémantique et tri par criticité. |
| **5. Parser Rich Text**| Regex Markdown ➔ JSON | Convertisseur natif Notion | Conversion Markdown vers blocs Notion (`toggle`, `bulleted_list_item`). |
| **6. Restitution** | Notion REST API | Page "Veille Tech - JJ/MM/AAAA" | Publication structurée avec résumé "🚀 En bref" et 5 Toggles. |
| **7. Alerting** | Telegram Bot API | Notification Push HTTPS | Push de succès, rapport de santé des flux et alerte crash complète. |
| **8. Consultation** | Apps Notion | iOS, macOS, Windows | Lecture multi-appareil synchronisée en temps réel via le Cloud. |

---

## 🧪 Exécution Manuelle & Test
Dans l'onglet **Actions** de ton dépôt GitHub, sélectionne le workflow **Daily Tech Watch Automation** et clique sur **Run workflow**.