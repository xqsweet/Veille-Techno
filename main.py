import os
import re
import sys
import datetime
from zoneinfo import ZoneInfo
import requests
import feedparser
import google.generativeai as genai

# ---------------------------------------------------------------------------
# CONFIGURATION & SECRETS
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Liste des 19 flux RSS de référence
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
    "https://www.phoronix.com/phoronix-rss.php",
    "https://www.cert.ssi.gouv.fr/feed/",       
    "https://www.cncf.io/feed/",              
    "https://huggingface.co/blog/feed.xml",     
    "https://github.blog/feed/",               
    "https://www.omgubuntu.co.uk/feed"           
]

# ---------------------------------------------------------------------------
# 0. SÉCURITÉ HORAIRE & DÉDOUBLONNAGE DYNAMIQUE NOTION
# ---------------------------------------------------------------------------
def check_notion_duplicate():
    """Vérifie l'heure locale (>= 18h) et s'assure qu'aucun doublon n'existe sur Notion."""
    is_manual = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
    if is_manual:
        print("🚀 Lancement manuel détecté (Workflow Dispatch) : Contournement du filtre d'existence.")
        return

    paris_time = datetime.datetime.now(ZoneInfo("Europe/Paris"))
    
    # Filtre Heure d'Hiver : Empêche le 1er cron (16h15 UTC = 17h15 FR) de tourner en hiver
    if paris_time.hour < 18:
        print(f"⏰ Passage ignoré : Il est actuellement {paris_time.strftime('%H:%M')} à Paris. La veille est planifiée à partir de 18h15.")
        sys.exit(0)

    # Vérification de l'existence de la page Notion pour aujourd'hui
    date_str = paris_time.strftime("%d/%m/%Y")
    expected_title = f"Veille Tech - {date_str}"

    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Notion-Version": "2022-06-28"
    }

    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            blocks = res.json().get("results", [])
            for block in blocks:
                if block.get("type") == "child_page":
                    title = block.get("child_page", {}).get("title", "")
                    if title == expected_title:
                        print(f"🛑 Une page Notion existe déjà pour aujourd'hui ({expected_title}). Passage du 2nd cron ignoré.")
                        sys.exit(0)
    except Exception as e:
        print(f"⚠️ Impossible de vérifier la présence de doublons sur Notion ({e}). Exécution maintenue par sécurité.")

# ---------------------------------------------------------------------------
# 0.b MÉMOIRE DE LA VEILLE D'HIER (DÉDOUBLONNAGE INTER-JOURS)
# ---------------------------------------------------------------------------
def get_yesterday_notion_summary():
    """Récupère les sujets traités hier sur Notion pour éviter la répétition d'un jour à l'autre."""
    paris_time = datetime.datetime.now(ZoneInfo("Europe/Paris"))
    yesterday_str = (paris_time - datetime.timedelta(days=1)).strftime("%d/%m/%Y")
    expected_title = f"Veille Tech - {yesterday_str}"

    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Notion-Version": "2022-06-28"
    }

    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code != 200:
            return ""

        blocks = res.json().get("results", [])
        yesterday_page_id = None
        for block in blocks:
            if block.get("type") == "child_page":
                if block.get("child_page", {}).get("title", "") == expected_title:
                    yesterday_page_id = block.get("id")
                    break

        if not yesterday_page_id:
            print(f"ℹ️ Aucune veille trouvée pour hier ({expected_title}). Génération standard.")
            return ""

        res_page = requests.get(f"https://api.notion.com/v1/blocks/{yesterday_page_id}/children", headers=headers, timeout=5)
        if res_page.status_code != 200:
            return ""

        child_blocks = res_page.json().get("results", [])
        extracted_topics = []

        for b in child_blocks:
            b_type = b.get("type")
            if b_type == "bulleted_list_item":
                texts = [t.get("plain_text", "") for t in b.get("bulleted_list_item", {}).get("rich_text", [])]
                if texts:
                    extracted_topics.append(" ".join(texts))
            elif b_type == "toggle":
                texts = [t.get("plain_text", "") for t in b.get("toggle", {}).get("rich_text", [])]
                if texts:
                    extracted_topics.append(" ".join(texts))

        summary_text = "\n".join(extracted_topics[:25])
        print(f"📖 {len(extracted_topics)} points d'hier récupérés pour dédoublonnage inter-jours.")
        return summary_text

    except Exception as e:
        print(f"⚠️ Impossible de lire la veille d'hier ({e}). Poursuite sans mémoire inter-jours.")
        return ""

# ---------------------------------------------------------------------------
# NOTIFICATION TELEGRAM
# ---------------------------------------------------------------------------
def send_telegram(message):
    """Envoie une notification Push sur Telegram avec fallback texte brut."""
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload_markdown = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            res = requests.post(url, json=payload_markdown, timeout=5)
            if res.status_code != 200:
                payload_raw = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message
                }
                requests.post(url, json=payload_raw, timeout=5)
        except Exception as e:
            print(f"⚠️ Erreur lors de l'envoi Telegram : {e}")

# ---------------------------------------------------------------------------
# PARSER NOTION RICH TEXT
# ---------------------------------------------------------------------------
def parse_markdown_to_rich_text(text):
    text_clean = text.replace("**", "")
    pattern = r'\[([^\]]+)\]\((https?://[^\s\)]+)\)'
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
# 1. COLLECTE RSS (24H GLISSANTES)
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
                        continue

                title = entry.get("title", "Sans titre")
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                clean_summary = re.sub('<[^<]+?>', '', summary)[:300]
                
                articles.append(f"- Titre: {title}\n  Lien: {link}\n  Extrait: {clean_summary}\n")
        except Exception:
            failed_feeds.append(url)
            continue

    print(f"✅ {len(articles)} articles pertinents collectés sur les dernières 24h.")
    return articles, failed_feeds

# ---------------------------------------------------------------------------
# 2. SYNTHÈSE GEMINI (MÉMOIRE + TRI PAR URGENCE)
# ---------------------------------------------------------------------------
def generate_summary_with_gemini(articles, yesterday_context=""):
    print("🧠 Analyse, tri par urgence et dédoublonnage par Gemini API...")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-3.5-flash-lite")
    date_str = datetime.datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y")
    news_context = "\n".join(articles)

    yesterday_prompt_section = ""
    if yesterday_context:
        yesterday_prompt_section = f"""
SUJETS ET ACTUALITÉS DÉJÀ TRAITÉS DANS LA VEILLE D'HIER :
{yesterday_context}

⚠️ RÈGLE DE DÉDOUBLONNAGE D'UN JOUR À L'AUTRE :
Si une actualité brute du jour concerne EXACTEMENT le même événement, la même annonce ou la même faille que l'un des sujets traités hier ci-dessus, ÉLIMINE-LA et NE LA RETIENS PAS pour le rapport d'aujourd'hui (sauf s'il y a un développement majeur ou un correctif officiel publié aujourd'hui).
"""

    prompt = f"""Tu es un assistant expert en veille technologique. Voici les actualités brutes récoltées aujourd'hui ({date_str}) :

ACTUALITÉS BRUTES DU JOUR :
{news_context}
{yesterday_prompt_section}

Analyse ces informations brutes et rédige la synthèse de la veille techno en français au format Markdown.

RÈGLES STRICTES DE SÉLECTION & DE TRI :
- Élimine les doublons de couverture presse entre médias.
- En haut du rapport, rédige entre 3 et 5 faits marquants synthétisant les événements les plus critiques de la journée.
- Conserve ensuite le Top 3 à 5 des actualités majeures par catégorie.
- NIVEAU D'URGENCE : Tu DOIS attribuer un niveau d'urgence à CHAQUE article avec le préfixe correspondant :
  * 🔴 [CRITIQUE] : Failles majeures/Zero-Day, pannes Cloud critiques, fuites massives, rachat/faillite.
  * 🟠 [ÉVOLUTION] : Sortie de version majeure (K8s, LLM, OS), nouvelles fonctionnalités clés.
  * 🟢 [INFO] : Tutoriels, bons plans hardware, actualités de fond ou secondaires.
- TRI STRICT : Dans chaque catégorie, TRIE obligatoirement les articles du PLUS CRITIQUE au MOINS CRITIQUE (d'abord les 🔴, puis les 🟠, puis les 🟢).
- Si une catégorie n'a aucune actualité aujourd'hui, écris exactement : "Aucune actualité majeure aujourd'hui dans cette catégorie."
- Format strict des liens hypertextes : [Nom du Média](URL_DIRECTE)

STRUCTURE EXACTE À RESPECTER :

## 🚀 En bref
- [Fait marquant 1]
- [Fait marquant 2]
- [Fait marquant 3]

## 1. Systèmes, Réseaux & Virtualisation
### 🔴 [CRITIQUE] Titre de l'article le plus urgent
- Résumé : 2 à 3 phrases claires.
- Pourquoi c'est important : Impact technique ou organisationnel.
- Source : [Nom du Média](URL)

### 🟠 [ÉVOLUTION] Titre de l'article suivant
(Même structure)

### 🟢 [INFO] Titre de l'article suivant
(Même structure)

## 2. Intelligence Artificielle & Développement Software
(Même structure triée par urgence)

## 3. Cybersécurité & Vulnérabilités critiques
(Même structure triée par urgence)

## 4. DevOps, Cloud Native & Open Source
(Même structure triée par urgence)

## 5. Hardware & Innovations Tech
(Même structure triée par urgence)
"""
    response = model.generate_content(prompt)
    return response.text

# ---------------------------------------------------------------------------
# 3. CRÉATION PAGE NOTION
# ---------------------------------------------------------------------------
def create_notion_journal_page(markdown_text):
    print("📝 Injection du rapport dans Notion...")
    date_str = datetime.datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y")
    sections = re.split(r'\n(?=## )', markdown_text)
    children_blocks = []

    for section in sections:
        lines = section.strip().split("\n")
        if not lines or not lines[0].startswith("## "):
            continue
        
        header_title = lines[0].replace("## ", "").strip()
        body_lines = lines[1:]

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
        check_notion_duplicate()
        articles, failed_feeds = collect_rss_articles()
        
        if not articles:
            print("ℹ️ Aucun article trouvé sur les dernières 24h.")
            send_telegram("ℹ️ Veille Tech : Aucun nouvel article publié sur les dernières 24h.")
        else:
            yesterday_context = get_yesterday_notion_summary()
            summary_md = generate_summary_with_gemini(articles, yesterday_context)
            create_notion_journal_page(summary_md)
            print("🎉 Terminé avec succès !")
            
            date_now = datetime.datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y")
            msg = f"✅ Veille Tech du {date_now} disponible sur ton Notion !"
            if failed_feeds:
                msg += f"\n\n⚠️ Note : {len(failed_feeds)} flux RSS n'a/ont pas répondu aujourd'hui."
            send_telegram(msg)

    except Exception as err:
        error_msg = f"🚨 CRASH VEILLE TECH 🚨\n\nDétail de l'erreur :\n{str(err)}"
        print(error_msg)
        send_telegram(error_msg)
        sys.exit(1)