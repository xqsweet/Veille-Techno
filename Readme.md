# 🚀 Automate de Veille Technologique Quotidienne

Pipeline Serverless 100 % gratuit pour collecter, analyser et synthétiser l'actualité IT quotidienne directement dans Notion et envoyer une confirmation sur Telegram.

## 📌 Architecture
- **Déclencheur :** GitHub Actions (Cron quotidien à 06h14 France)
- **Ingestion :** Python (`feedparser`) - 14 flux RSS de référence
- **IA / Traitement :** Google AI Studio (`gemini-3.5-flash-lite`)
- **Restitution :** Notion API (Page quotidienne "Journal" avec Toggles et liens cliquables)
- **Notification :** Bot Telegram (Push sur iPhone / Mac / PC)

---

## 🛠️ Configuration Initiale (10 minutes)

### 1. Bot Telegram
1. Sur Telegram, cherche `@BotFather`, tape `/newbot` et note le `TELEGRAM_BOT_TOKEN`.
2. Cherche `@userinfobot`, lance-le et note ton ID personnel `TELEGRAM_CHAT_ID`.

### 2. Notion API
1. Prépare une page parent "Journal de Veille" dans Notion.
2. Va sur `notion.so/my-integrations`, crée une nouvelle intégration et copie le `NOTION_API_TOKEN`.
3. Sur ta page Notion, clique sur `...` (en haut à droite) ➔ `Connecter à` ➔ sélectionne ton intégration.
4. Copie l'ID de la page parent depuis son URL (la suite de 32 caractères) : `NOTION_PAGE_ID`.

### 3. Google AI Studio
1. Génère une clé API gratuite sur [aistudio.google.com](https://aistudio.google.com) : `GEMINI_API_KEY`.

### 4. Dépôt GitHub
1. Crée un dépôt GitHub privé.
2. Dépose les fichiers `main.py`, `requirements.txt` et `.github/workflows/daily_veille.yml`.
3. Dans **Settings** ➔ **Secrets and variables** ➔ **Actions**, ajoute les 5 secrets :
   - `GEMINI_API_KEY`
   - `NOTION_API_TOKEN`
   - `NOTION_PAGE_ID`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

---

## 🧪 Premier Test
Dans l'onglet **Actions** de ton dépôt GitHub, clique sur **Daily Tech Watch Automation** ➔ **Run workflow**. 
Tu recevras instantanément ta notification Telegram et la page apparaîtra dans ton Notion !