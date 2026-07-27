import os
import re
import sys
import datetime
from zoneinfo import ZoneInfo
import requests
import feedparser
import google.generativeai as genai

# ---------------------------------------------------------------------------
# 0. VERIFICATION DE L'HEURE LOCALE FR (06h14 HEURE DE PARIS)
# ---------------------------------------------------------------------------
def check_french_time():
    """Garantit l'exécution uniquement s'il est 06h (heure de Paris), été comme hiver."""
    paris_time = datetime.datetime.now(ZoneInfo("Europe/Paris"))
    is_manual = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
    
    # En cas d'exécution automatique par le CRON, on ne s'exécute qu'à 06h (heure de Paris)
    if not is_manual and paris_time.hour != 6:
        print(f"⏰ Passage ignoré : Il est actuellement {paris_time.strftime('%H:%M')} à Paris. Le script s'exécutera à 06h14.")
        sys.exit(0)

# ---------------------------------------------------------------------------
# CONFIGURATION & SECRETS (Stockés dans GitHub Repository Secrets)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Liste des 14 flux RSS de référence
RSS_FEEDS = [
    "https://www.it-connect.fr/feed/",
    "https://www.lemondeinformatique.fr/flux-rss/rss.xml",
    "https://www.numerama.com/tech/feed/",
    "https://www.clubic.com/feed/news.rss",
    "https://www.zataz.com/feed/",
    "https://www.lesnumeriques.com/rss.xml",
    "https://www.usine-digitale.fr/rss/",
    "https://www.developpez.com/index/rss",
    "https://www.bleepingcomputer.com/feed/",
    "https://feeds.feedburner.com/ArsTechnica",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://aws.amazon.com/blogs/aws/feed/",
    "https://techcrunch.com/feed/",
    "https://www.phoronix.com/phoronix-rss.php"
]

# ---------------------------------------------------------------------------
# NOTIFICATION TELEGRAM (Avec secours / Fallback texte brut)
# ---------------------------------------------------------------------------
def send_telegram(message):
    """
    Envoie une notification Push sur Telegram. 
    Essaie d'abord en Markdown, et se rabat sur le texte brut si le Markdown échoue.
    """
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # 1er essai : Envoi formaté en Markdown
        payload_markdown = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            res = requests.post(url, json=payload_markdown, timeout=5)
            if res.status_code != 200:
                # 2ème essai : Fallback en texte brut si l'API Telegram rejette le Markdown
                payload_raw = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message
                }
                requests.post(url, json=payload_raw, timeout=5)
        except Exception as e:
            print(f"⚠️ Erreur lors de l'envoi Telegram : {e}")

# ---------------------------------------------------------------------------
# PARSER NOTION RICH TEXT (Conversion des liens [Texte](URL) -> Liens Cliquables)
# ---------------------------------------------------------------------------
def parse_markdown_to_rich_text(text):
    """
    Transforme les liens Markdown [Nom](URL) en objets rich_text 
    nativement cliquables dans Notion, tout en nettoyant le gras (**).
    """
    text_clean = text.replace("**", "")
    pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
    rich_text = []
    last_end = 0

    for match in re.finditer(pattern, text_clean):
        start, end = match.span()
        if start > last_end:
            rich_text.append({"type": "text", "text": {"content": text_clean[last_end:start]}})
        
        link_title, link_url = match.group(1), match.group(2)
        rich_text.append({
            "type": "text",
            "text": {"content": link_title, "link": {"url": link_url}},
            "annotations": {"bold": True, "color": "blue"}
        })
        last_end = end

    if last_end < len(text_clean):
        rich_text.append({"type": "text", "text": {"content": text_clean[last_end:]}})

    return rich_text if rich_text else [{"type": "text", "text": {"content": text_clean}}]

# ---------------------------------------------------------------------------
# 1. COLLECTE DES FLUX RSS (Fenêtre glissante 24h & Contrôle de santé des flux)
# ---------------------------------------------------------------------------
def collect_rss_articles():
    print("📡 Collecte des flux RSS...")
    articles = []
    failed_feeds = []
    now = datetime.datetime.now(datetime.timezone.utc)
    yesterday = now - datetime.timedelta(hours=24)

    for url in RSS_FEEDS:
        try:
            response = requests.get(url, timeout=4, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                failed_feeds.append(url)
                continue

            feed = feedparser.parse(response.content)
            if feed.bozo and not feed.entries:
                failed_feeds.append(url)
                continue

            for entry in feed.entries:
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if published_parsed:
                    pub_date = datetime.datetime(*published_parsed[:6], tzinfo=datetime.timezone.utc)
                    if pub_date < yesterday:
                        continue # Rejette ce qui date de plus de 24h

                title = entry.get("title", "Sans titre")
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                clean_summary = re.sub('<[^<]+?>', '', summary)[:300]
                
                articles.append(f"- Titre: {title}\n  Lien: {link}\n  Extrait: {clean_summary}\n")
        except Exception:
            failed_feeds.append(url)
            continue

    print(f"✅ {len(articles)} articles pertinents collectés sur les dernières 24h.")
    if failed_feeds:
        print(f"⚠️ {len(failed_feeds)} flux RSS n'ont pas répondu : {failed_feeds}")

    return articles, failed_feeds

# ---------------------------------------------------------------------------
# 2. SYNTHÈSE GEMINI (PROMPT BATCH)
# ---------------------------------------------------------------------------
def generate_summary_with_gemini(articles):
    print("🧠 Analyse et synthèse par Gemini API...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-3.5-flash-lite")

    date_str = datetime.datetime.now().strftime("%d/%m/%Y")
    news_context = "\n".join(articles)

    prompt = f"""
Tu es un assistant expert en veille technologique. Voici les actualités brutes récoltées aujourd'hui ({date_str}) :

---
ACTUALITÉS BRUTES DU JOUR :
{news_context}
---

Analyse ces informations brutes et rédige la synthèse de la veille techno en français au format Markdown.

### RÈGLES STRICTES DE SÉLECTION :
- Élimine les doublons de couverture presse entre médias.
- En haut du rapport, rédige entre 3 et 5 faits marquants (TL;DR) synthétisant les événements les plus critiques de la journée.
- Conserve ensuite uniquement le Top 3 à 5 des actualités majeures par catégorie.
- Si une catégorie n'a aucune actualité marquante aujourd'hui (ex: le week-end), écris exactement : "*Aucune actualité majeure aujourd'hui dans cette catégorie.*"
- Format strict des liens hypertextes : [Nom du Média](URL_EXACTE)

### STRUCTURE EXACTE À RESPECTER :

## 🚀 En bref (TL;DR)
- [Fait marquant 1]
- [Fait marquant 2]
- [Fait marquant 3]
- [Fait marquant 4]
- [Fait marquant 5]

## 1. Systèmes, Réseaux, Cloud & Virtualisation
### [Titre clair de l'article en français]
- **Résumé :** 2 à 3 phrases claires et synthétiques.
- **Pourquoi c'est important :** Impact technique ou organisationnel.
- **Source :** [Nom du Média](Lien_Direct)

## 2. Intelligence Artificielle & Développement Software
(Même structure pour les articles)

## 3. Cybersécurité & Vulnérabilités critiques
(Même structure pour les articles)

## 4. Hardware & Innovations Tech
(Même structure pour les articles)
"""

    response = model.generate_content(prompt)
    return response.text

# ---------------------------------------------------------------------------
# 3. CRÉATION NOTION (RENDU PRO AVEC SOUS-BLOCS NATIFS ET TOGGLES)
# ---------------------------------------------------------------------------
def create_notion_journal_page(markdown_text):
    print("📝 Injection du rapport dans Notion...")
    date_str = datetime.datetime.now().strftime("%d/%m/%Y")
    sections = re.split(r'\n(?=## )', markdown_text)
    
    children_blocks = []

    for section in sections:
        lines = section.strip().split("\n")
        if not lines or not lines[0].startswith("## "):
            continue

        header_title = lines[0].replace("## ", "").strip()
        body_lines = lines[1:]

        # 1. Section En bref (TL;DR) -> Titre H2 + Puces d'éléments
        if "En bref" in header_title:
            children_blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": header_title}}]}
            })
            for line in body_lines:
                line_clean = line.strip()
                if line_clean.startswith("- "):
                    content = line_clean.replace("- ", "").strip()
                    children_blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": parse_markdown_to_rich_text(content)}
                    })
        # 2. Catégories -> Blocks Déroulants (Toggles) contenant des sous-blocs natifs
        else:
            toggle_children = []
            for line in body_lines:
                line_str = line.strip()
                if not line_str:
                    continue
                if line_str.startswith("### "):
                    toggle_children.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"type": "text", "text": {"content": line_str.replace("### ", "")}}]}
                    })
                elif line_str.startswith("- "):
                    toggle_children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": parse_markdown_to_rich_text(line_str.replace("- ", ""))}
                    })
                else:
                    toggle_children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": parse_markdown_to_rich_text(line_str)}
                    })

            children_blocks.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": header_title}}],
                    "children": toggle_children if toggle_children else [{
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Aucun contenu disponible."}}]}
                    }]
                }
            })

    # Envoi HTTP vers l'API Notion
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "parent": {"page_id": NOTION_PAGE_ID},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": f"Veille Tech - {date_str}"}}]
            }
        },
        "children": children_blocks
    }

    res = requests.post(url, json=payload, headers=headers)
    if res.status_code != 200:
        raise Exception(f"Erreur Notion API ({res.status_code}) : {res.text}")

# ---------------------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        # Check de l'heure locale (filtre 06h14 France)
        check_french_time()

        articles, failed_feeds = collect_rss_articles()
        if not articles:
            print("ℹ️ Aucun article trouvé sur 24h.")
            send_telegram("ℹ️ **Veille Tech** : Aucun nouvel article publié sur les dernières 24h.")
        else:
            summary_md = generate_summary_with_gemini(articles)
            create_notion_journal_page(summary_md)
            print("🎉 Terminé avec succès !")
            
            date_now = datetime.datetime.now().strftime("%d/%m/%Y")
            msg = f"✅ **Veille Tech du {date_now}** disponible sur ton Notion !"
            
            # Alerte discrète si certains flux RSS n'ont pas répondu
            if failed_feeds:
                msg += f"\n\n⚠️ *Note : {len(failed_feeds)} flux RSS n'a/ont pas répondu aujourd'hui.*"
            
            send_telegram(msg)
    except Exception as err:
        error_msg = f"🚨 **CRASH VEILLE TECH** 🚨\n\n**Détail de l'erreur :**\n`{str(err)}`"
        print(error_msg)
        send_telegram(error_msg)
        sys.exit(1)