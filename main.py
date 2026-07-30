import os
import re
import sys
import json
import math
import time
import asyncio
import datetime
from zoneinfo import ZoneInfo
import requests
import aiohttp
import feedparser
import google.generativeai as genai

# ---------------------------------------------------------------------------
# 1. CONFIGURATION & SECRETS CHECK (PRE-FLIGHT CHECK)
# ---------------------------------------------------------------------------
def preflight_check():
    """
    Vérifie la présence des 5 secrets GitHub indispensables au démarrage.
    Compatible avec les anciens et nouveaux noms de secrets.
    """
    notion_token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_TOKEN")
    notion_id = os.getenv("NOTION_DATABASE_ID") or os.getenv("NOTION_PAGE_ID")

    required = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "NOTION_TOKEN (ou NOTION_API_TOKEN)": notion_token,
        "NOTION_DATABASE_ID (ou NOTION_PAGE_ID)": notion_id,
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"❌ [CRITICAL] Variables d'environnement manquantes : {', '.join(missing)}")
        sys.exit(1)
    print("✅ [PRE-FLIGHT] Toutes les variables d'environnement sont présentes.")

# ---------------------------------------------------------------------------
# 2. FRENCH TIME CHECK (GUARDRAIL DOUBLE CRON)
# ---------------------------------------------------------------------------
def check_french_time():
    """
    Garantit l'exécution à 18h15 heure française.
    Si le script est relancé manuellement via workflow_dispatch, la règle est outrepassée.
    """
    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    if event_name == "workflow_dispatch":
        print("⚡ [EXECUTION] Déclenchement manuel via workflow_dispatch : outrepasser le filtre horaire.")
        return True

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    paris_time = now_utc.astimezone(ZoneInfo("Europe/Paris"))
    print(f"🕒 [HEURE LOCAL] Heure actuelle à Paris : {paris_time.strftime('%H:%M:%S (%Z)')}")

    if paris_time.hour != 18:
        print(f"🛑 [HEURE GUARD] Il est {paris_time.hour}h à Paris (18h attendu). Arrêt propre.")
        sys.exit(0)
    return True

# ---------------------------------------------------------------------------
# CONSTANTES & FLUX RSS (26 FLUX OPTIMISÉS)
# ---------------------------------------------------------------------------
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
    "https://www.cert.ssi.gouv.fr/feed/",
    "https://kubernetes.io/feed.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://github.blog/feed/",
    "https://www.omgubuntu.co.uk/feed",
    "https://www.frandroid.com/feed",
    "https://korben.info/feed",
    "https://www.presse-citron.net/feed/",
    "https://siecledigital.fr/feed/",
    "https://www.01net.com/actualites/feed/",
    "https://www.macg.co/rss",
    "https://linuxfr.org/news.atom",
]

CATEGORIES_MAP = {
    "CYBER": "1. 🛡️ Cybersécurité & Vulnérabilités",
    "CYBERSECURITE": "1. 🛡️ Cybersécurité & Vulnérabilités",
    "SECURITY": "1. 🛡️ Cybersécurité & Vulnérabilités",
    "CLOUD": "2. ☁️ Cloud, DevOps & Infrastructure",
    "DEVOPS": "2. ☁️ Cloud, DevOps & Infrastructure",
    "INFRASTRUCTURE": "2. ☁️ Cloud, DevOps & Infrastructure",
    "IA": "3. 🤖 Intelligence Artificielle & Data",
    "AI": "3. 🤖 Intelligence Artificielle & Data",
    "DATA": "3. 🤖 Intelligence Artificielle & Data",
    "SOFTWARE": "4. 💻 Système, Software & Open-Source",
    "SYSTEME": "4. 💻 Système, Software & Open-Source",
    "OS": "4. 💻 Système, Software & Open-Source",
    "OPEN-SOURCE": "4. 💻 Système, Software & Open-Source",
    "HARDWARE": "5. 📱 Hardware & Innovations Tech",
    "CONSUMER": "5. 📱 Hardware & Innovations Tech",
    "INNOVATION": "5. 📱 Hardware & Innovations Tech",
    "MOBILE": "5. 📱 Hardware & Innovations Tech",
}

DEFAULT_CATEGORY = "🌐 Divers & Tech Générale"

# ---------------------------------------------------------------------------
# 3. COLLECTE RSS ASYNCHRONE (aiohttp)
# ---------------------------------------------------------------------------
async def fetch_feed(session, url, headers):
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as response:
            if response.status == 200:
                content = await response.read()
                return url, content, None
            else:
                return url, None, f"HTTP {response.status}"
    except Exception as e:
        return url, None, str(e)

async def collect_rss_articles_async():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    articles = []
    failed_feeds = []

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    cutoff_time = now_utc - datetime.timedelta(hours=24)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_feed(session, url, headers) for url in RSS_FEEDS]
        results = await asyncio.gather(*tasks)

    for url, content, error in results:
        domain = url.split("/")[2].replace("www.", "")
        if error or not content:
            failed_feeds.append(domain)
            print(f"⚠️ [RSS KO] {url} -> {error}")
            continue

        try:
            feed = feedparser.parse(content)
            source_name = feed.feed.get("title", domain)

            for entry in feed.entries:
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime.datetime(*entry.published_parsed[:6], tzinfo=datetime.timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_date = datetime.datetime(*entry.updated_parsed[:6], tzinfo=datetime.timezone.utc)

                if pub_date is None or pub_date >= cutoff_time:
                    title = entry.get("title", "Sans titre")
                    link = entry.get("link", url)
                    summary = entry.get("summary", entry.get("description", ""))
                    clean_summary = re.sub(r"<[^<]+?>", "", summary)[:300]

                    articles.append({
                        "source": source_name,
                        "title": title,
                        "link": link,
                        "summary": clean_summary,
                        "pub_date": pub_date.strftime("%Y-%m-%d %H:%M") if pub_date else "Aujourd'hui"
                    })
        except Exception as parse_err:
            failed_feeds.append(domain)
            print(f"⚠️ [RSS PARSE ERROR] {url} -> {parse_err}")

    print(f"📡 [RSS] {len(articles)} articles récents collectés sur {len(RSS_FEEDS) - len(failed_feeds)}/{len(RSS_FEEDS)} flux.")
    return articles, failed_feeds

# ---------------------------------------------------------------------------
# 4. MEMOIRE NOTION J-1 & NETTOYAGE AUTO J
# ---------------------------------------------------------------------------
def clear_notion_page_blocks(page_id, headers):
    """Vide l'intégralité des blocs contenus dans une page Notion."""
    has_more = True
    next_cursor = None
    while has_more:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if next_cursor:
            url += f"&start_cursor={next_cursor}"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            blocks = data.get("results", [])
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
            for block in blocks:
                b_id = block["id"]
                try:
                    requests.delete(f"https://api.notion.com/v1/blocks/{b_id}", headers=headers)
                except Exception as e:
                    print(f"⚠️ [NOTION CLEAR BLOCK ERROR] {b_id} : {e}")
        else:
            break
    print(f"🧹 [NOTION] Blocs de la page {page_id} nettoyés.")

def manage_notion_pages(today_str, yesterday_str):
    notion_token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_TOKEN")
    parent_id = os.getenv("NOTION_DATABASE_ID") or os.getenv("NOTION_PAGE_ID")
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    memory_j_minus_1 = ""
    existing_today_page_id = None

    # Mode Page Parent
    blocks_url = f"https://api.notion.com/v1/blocks/{parent_id}/children?page_size=100"
    resp = requests.get(blocks_url, headers=headers)

    if resp.status_code == 200:
        results = resp.json().get("results", [])
        for block in results:
            b_type = block.get("type")
            b_id = block["id"]

            # Nettoyage des blocs de paragraphes vides parasites dans la page parent
            if b_type == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                plain_text = "".join([t.get("plain_text", "") for t in rich_text]).strip()
                if not plain_text:
                    try:
                        requests.delete(f"https://api.notion.com/v1/blocks/{b_id}", headers=headers)
                        print(f"🧹 [NOTION] Bloc paragraphe vide parasite ({b_id}) supprimé de la page parent.")
                    except Exception as e:
                        print(f"⚠️ [NOTION DELETE ERROR] {b_id} : {e}")
                    continue

            if b_type == "child_page":
                title = block.get("child_page", {}).get("title", "")
                page_id = b_id
                if title == f"Veille Tech - {today_str}":
                    existing_today_page_id = page_id
                    clear_notion_page_blocks(page_id, headers)
                    print(f"♻️ [NOTION] Ancienne page du jour ({today_str}) conservée et réinitialisée.")
                elif title == f"Veille Tech - {yesterday_str}":
                    b_resp = requests.get(f"https://api.notion.com/v1/blocks/{page_id}/children", headers=headers)
                    if b_resp.status_code == 200:
                        blocks = b_resp.json().get("results", [])
                        lines = []
                        for b in blocks[:20]:
                            b_t = b.get("type")
                            if b_t and b_t in b:
                                text_items = b[b_t].get("rich_text", [])
                                t_str = "".join([t.get("plain_text", "") for t in text_items])
                                if t_str:
                                    lines.append(t_str)
                        memory_j_minus_1 = "\n".join(lines)[:1500]
                        print(f"🧠 [NOTION] Mémoire J-1 chargée depuis Notion ({len(memory_j_minus_1)} caractères).")
    else:
        # Fallback : Mode Database Query
        query_url = f"https://api.notion.com/v1/databases/{parent_id}/query"
        payload_today = {
            "filter": {
                "and": [
                    {"property": "Name", "title": {"equals": f"Veille Tech - {today_str}"}},
                    {"archived": False}
                ]
            }
        }
        resp = requests.post(query_url, headers=headers, json=payload_today)
        if resp.status_code == 200:
            for page in resp.json().get("results", []):
                page_id = page["id"]
                existing_today_page_id = page_id
                clear_notion_page_blocks(page_id, headers)
                print(f"♻️ [NOTION] Ancienne page du jour ({today_str}) conservée et réinitialisée.")

        payload_yesterday = {
            "filter": {
                "and": [
                    {"property": "Name", "title": {"equals": f"Veille Tech - {yesterday_str}"}},
                    {"archived": False}
                ]
            }
        }
        resp_y = requests.post(query_url, headers=headers, json=payload_yesterday)
        if resp_y.status_code == 200:
            results_y = resp_y.json().get("results", [])
            if results_y:
                yesterday_page_id = results_y[0]["id"]
                blocks_url_y = f"https://api.notion.com/v1/blocks/{yesterday_page_id}/children"
                b_resp = requests.get(blocks_url_y, headers=headers)
                if b_resp.status_code == 200:
                    blocks = b_resp.json().get("results", [])
                    lines = []
                    for b in blocks[:20]:
                        b_type = b.get("type")
                        if b_type and b_type in b:
                            text_items = b[b_type].get("rich_text", [])
                            t_str = "".join([t.get("plain_text", "") for t in text_items])
                            if t_str:
                                lines.append(t_str)
                    memory_j_minus_1 = "\n".join(lines)[:1500]
                    print(f"🧠 [NOTION] Mémoire J-1 chargée depuis Notion ({len(memory_j_minus_1)} caractères).")

    if not memory_j_minus_1:
        print("ℹ️ [NOTION] Aucun historique J-1 disponible.")

    return memory_j_minus_1, existing_today_page_id

# ---------------------------------------------------------------------------
# 5. SYNTHESE GEMINI
# ---------------------------------------------------------------------------
def process_with_gemini(articles, memory_j_minus_1):
    if not articles:
        return {"articles": [], "tags": []}

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    articles_text = ""
    for idx, a in enumerate(articles, 1):
        articles_text += f"[{idx}] Source: {a['source']} | Titre: {a['title']} | Date: {a['pub_date']}\nExtrait: {a['summary']}\nLien: {a['link']}\n\n"

    SYSTEM_PROMPT = """
RÈGLES STRICTES DE CRITICITÉ (🔴 / 🟠 / 🟢) :
Sois extrêmement SÉVÈRE et SÉLECTIF. Ne colle PAS du rouge partout !

🔴 [CRITIQUE] (Max 1 à 2 articles par jour MAXIMUM dans TOUT le journal) :
- Réservé EXCLUSIVEMENT aux failles Zero-Day activement exploitées dans le monde, aux piratages majeurs d'infrastructures critiques, ou aux pannes mondiales d'acteurs majeurs (AWS, Cloudflare, Microsoft 365).
- Si une faille nécessite un accès physique ou un scénario improbable, ce N'EST PAS critique.

🟠 [ÉVOLUTION] (Urgence moyenne / Actualité importante) :
- Patchs de sécurité mensuels (Patch Tuesday, Chrome/Safari updates).
- Mises à jour majeures de frameworks, OS (iOS, Android, Windows) ou modèles d'IA.
- Rachets d'entreprises Tech majeures ou nouvelles réglementations (RGPD, AI Act).

🟢 [INFO] (Veille classique / Culture Tech) :
- Annonces de nouveaux gadgets/smartphones, sorties de bêtas.
- Outils open-source, tutoriels, astuces de dev/sysadmin.
- Articles de réflexion, nouveautés mineures d'applications.
"""

    prompt = f"""Tu es un Tech Lead expert en veille informatique (SysAdmin, Cloud, Cyber, Dev, AI, Consumer Tech).

{SYSTEM_PROMPT}

Voici une liste d'articles bruts collectés aujourd'hui sur divers flux RSS :

{articles_text}

---
CONTEXTE HISTORIQUE DU JOUR PRÉCÉDENT (J-1) :
{memory_j_minus_1 if memory_j_minus_1 else "Aucun historique disponible."}
---

CONSIGNES STRICTES :
1. Sélectionne uniquement le TOP 10 à 25 des actualités les plus pertinentes et majeures du jour. Élimine le bruit, les publicités et les sujets trop secondaires.
2. Dédoublonne les articles qui parlent du même sujet en gardant la source la plus complète. Ne répète pas les sujets déjà traités dans l'historique J-1.
3. Pour chaque article retenu, remplis les champs suivants :
   - "title": Titre court et percutant en français.
   - "category": L'une des catégories suivantes : "CYBER", "CLOUD", "IA", "SOFTWARE", "HARDWARE".
   - "urgency": Urgence ("CRITIQUE" pour failles majeures/alertes, "ÉVOLUTION" pour maj/annonces produit, "INFO" pour le reste).
   - "summary": Résumé en 2-3 phrases claires en français (utilise du Markdown léger comme **termes clés** si pertinent).
   - "impact": 1 phrase expliquant pourquoi c'est important techniquement.
   - "source_name": Nom du média source.
   - "source_url": URL exacte de l'article.
4. Génère également entre 5 et 7 hashtags ("tags") représentatifs des thèmes forts du jour (ex: ["#Cyber", "#Kubernetes", "#Apple", "#Python"]).

Réponds EXCLUSIVEMENT sous forme d'un objet JSON strict respectant la structure suivante :
{{
  "tags": ["#Tag1", "#Tag2"],
  "articles": [
    {{
      "title": "...",
      "category": "CYBER",
      "urgency": "CRITIQUE",
      "summary": "...",
      "impact": "...",
      "source_name": "...",
      "source_url": "..."
    }}
  ]
}}
"""

    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        generation_config={"response_mime_type": "application/json"}
    )

    for attempt in range(2):
        try:
            print(f"🤖 [GEMINI] Envoi de la requête en JSON structuré (Tentative {attempt+1}/2)...")
            response = model.generate_content(prompt)
            data = json.loads(response.text)
            print(f"✅ [GEMINI] Synthèse générée avec succès ({len(data.get('articles', []))} articles retenus).")
            return data
        except Exception as e:
            print(f"⚠️ [GEMINI ERROR] Tentative {attempt+1} échouée : {e}")
            if attempt == 1:
                print("❌ [GEMINI] Échec définitif après 2 tentatives.")
                raise e

# ---------------------------------------------------------------------------
# 6. HELPERS RENDU NOTION
# ---------------------------------------------------------------------------
def parse_markdown_to_rich_text(text):
    rich_text = []
    pattern = r"(\*\*.+?\*\*|\[.+?\]\(https?://[^\s\)]+\))"
    tokens = re.split(pattern, text)

    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            rich_text.append({
                "type": "text",
                "text": {"content": token[2:-2]},
                "annotations": {"bold": True}
            })
        elif token.startswith("[") and "](" in token and token.endswith(")"):
            m = re.match(r"\[(.+?)\]\((https?://[^\s\)]+)\)", token)
            if m:
                rich_text.append({
                    "type": "text",
                    "text": {"content": m.group(1), "link": {"url": m.group(2)}}
                })
            else:
                rich_text.append({"type": "text", "text": {"content": token}})
        else:
            rich_text.append({"type": "text", "text": {"content": token}})
    
    return rich_text

def execute_notion_request_with_retry(method, url, headers, json_payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            if method.upper() == "POST":
                resp = requests.post(url, headers=headers, json=json_payload, timeout=10)
            elif method.upper() == "PATCH":
                resp = requests.patch(url, headers=headers, json=json_payload, timeout=10)
            
            if resp.status_code in [200, 201]:
                return resp
            else:
                print(f"⚠️ [NOTION API] Statut HTTP {resp.status_code} (Tentative {attempt+1}/{max_retries}) : {resp.text}")
        except Exception as e:
            print(f"⚠️ [NOTION RETRY] Exception réseau : {e} (Tentative {attempt+1}/{max_retries})")
        
        time.sleep(2)
    
    raise Exception(f"❌ [NOTION API] Impossible d'exécuter la requête {method} sur {url}")

# ---------------------------------------------------------------------------
# 7. CREATION PAGE NOTION
# ---------------------------------------------------------------------------
def create_notion_journal_page(today_str, gemini_data, failed_feeds, existing_page_id=None):
    notion_token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_TOKEN")
    parent_id = os.getenv("NOTION_DATABASE_ID") or os.getenv("NOTION_PAGE_ID")

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    articles = gemini_data.get("articles", [])
    tags = gemini_data.get("tags", [])

    total_words = 0
    for a in articles:
        total_words += len(a.get("summary", "").split())
        total_words += len(a.get("impact", "").split())
    
    reading_time = max(1, math.ceil(total_words / 200)) if articles else 0

    callout_text = f"⏱️ Temps de lecture estimé : {reading_time} min\n"
    if tags:
        callout_text += f"🏷️ Mots-clés du jour : {' '.join(tags)}"
    if failed_feeds:
        callout_text += f"\n⚠️ Source(s) non disponible(s) ({len(failed_feeds)}/{len(RSS_FEEDS)}) : {', '.join(failed_feeds)}"

    header_callout = {
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"emoji": "📌"},
            "rich_text": [{"type": "text", "text": {"content": callout_text}}]
        }
    }

    all_blocks = [header_callout]

    if not articles:
        no_article_block = {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "ℹ️ Aucune actualité majeure identifiée sur les dernières 24h."}}]
            }
        }
        all_blocks.append(no_article_block)
    else:
        grouped = {}
        for a in articles:
            raw_cat = str(a.get("category", "")).upper().strip()
            cat_name = CATEGORIES_MAP.get(raw_cat, DEFAULT_CATEGORY)
            grouped.setdefault(cat_name, []).append(a)

        urgency_order = {"CRITIQUE": 1, "ÉVOLUTION": 2, "INFO": 3}

        for cat_name in sorted(grouped.keys()):
            cat_articles = grouped[cat_name]
            cat_articles.sort(key=lambda x: urgency_order.get(str(x.get("urgency", "")).upper(), 99))

            toggle_children = []
            for item in cat_articles:
                urg = str(item.get("urgency", "")).upper()
                badge = "🔴 [CRITIQUE]" if urg == "CRITIQUE" else ("🟠 [ÉVOLUTION]" if urg == "ÉVOLUTION" else "🟢 [INFO]")
                title_str = f"{badge} {item.get('title', '')}"

                summary_rich = parse_markdown_to_rich_text(item.get("summary", ""))
                impact_rich = parse_markdown_to_rich_text(item.get("impact", ""))
                source_url = item.get("source_url", "")
                source_name = item.get("source_name", "Source")

                item_bullet = {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": title_str}, "annotations": {"bold": True}}],
                        "children": [
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"type": "text", "text": {"content": "📝 Résumé : "}, "annotations": {"bold": True}}] + summary_rich
                                }
                            },
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {"type": "text", "text": {"content": "💡 Impact : "}, "annotations": {"bold": True}}
                                    ] + impact_rich
                                }
                            },
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {"type": "text", "text": {"content": "🔗 Source : "}, "annotations": {"bold": True}},
                                        {"type": "text", "text": {"content": source_name, "link": {"url": source_url}}} if source_url else {"type": "text", "text": {"content": source_name}}
                                    ]
                                }
                            }
                        ]
                    }
                }
                toggle_children.append(item_bullet)

            toggle_block = {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{"type": "text", "text": {"content": cat_name}, "annotations": {"bold": True}}],
                    "children": toggle_children
                }
            }
            all_blocks.append(toggle_block)

    chunks = [all_blocks[i:i + 100] for i in range(0, len(all_blocks), 100)]

    if existing_page_id:
        print(f"♻️ [NOTION] Réinjection des blocs dans la page existante ({existing_page_id})...")
        page_id = existing_page_id
        page_res = requests.get(f"https://api.notion.com/v1/pages/{page_id}", headers=headers)
        page_url = page_res.json().get("url", "") if page_res.status_code == 200 else f"https://notion.so/{page_id.replace('-', '')}"
        
        for idx, chunk in enumerate(chunks, 1):
            print(f"📦 [NOTION] Ingestion du paquet #{idx} ({len(chunk)} blocks)...")
            patch_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            execute_notion_request_with_retry("PATCH", patch_url, headers, {"children": chunk})
    else:
        first_chunk = chunks[0] if chunks else []
        remaining_chunks = chunks[1:] if len(chunks) > 1 else []

        page_payload = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": [{"text": {"content": f"Veille Tech - {today_str}"}}]
            },
            "children": first_chunk
        }

        print("📝 [NOTION] Création de la page Notion...")
        try:
            res = execute_notion_request_with_retry("POST", "https://api.notion.com/v1/pages", headers, page_payload, max_retries=1)
        except Exception:
            print("🔄 [NOTION] Bascule sur le mode Database Parent...")
            db_payload = {
                "parent": {"database_id": parent_id},
                "properties": {
                    "Name": {"title": [{"text": {"content": f"Veille Tech - {today_str}"}}]}
                },
                "children": first_chunk
            }
            res = execute_notion_request_with_retry("POST", "https://api.notion.com/v1/pages", headers, db_payload, max_retries=3)

        page_data = res.json()
        page_id = page_data.get("id")
        page_url = page_data.get("url", "")

        for idx, chunk in enumerate(remaining_chunks, 1):
            print(f"📦 [NOTION] Ingestion du paquet supplémentaire #{idx} ({len(chunk)} blocks)...")
            patch_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            execute_notion_request_with_retry("PATCH", patch_url, headers, {"children": chunk})

    print(f"✅ [NOTION] Page Notion mise à jour avec succès ! URL : {page_url}")
    return page_url, reading_time

# ---------------------------------------------------------------------------
# 8. NOTIFICATION TELEGRAM (FORMAT HTML & LIEN PERSONNALISÉ)
# ---------------------------------------------------------------------------
def send_telegram_notification(today_str, page_url, article_count, reading_time, tags, failed_feeds):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if article_count == 0:
        message = f"ℹ️ <b>Veille du {today_str}</b> : 0 article aujourd'hui."
    else:
        tags_str = " ".join(tags) if tags else "#TechWatch"
        message = (
            f"✅ <b>Veille Tech du {today_str} est disponible !</b>\n\n"
            f"📊 <b>{article_count}</b> articles analysés | ⏱️ <b>{reading_time} min</b> de lecture\n"
            f"🏷️ {tags_str}\n"
        )
        if failed_feeds:
            message += f"⚠️ {len(failed_feeds)} source(s) indisponible(s)\n"

        # Bouton/Hyperlien HTML épuré
        message += f'\n👉 <a href="{page_url}"><b>📖 Ouvrir le Journal dans Notion</b></a>'

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("📲 [TELEGRAM] Notification envoyée avec succès sur iPhone !")
        else:
            print(f"⚠️ [TELEGRAM ERROR] Statut HTTP {resp.status_code} : {resp.text}")
    except Exception as e:
        print(f"❌ [TELEGRAM ERROR] Exception lors de l'envoi : {e}")

# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------
def main():
    print("🚀 [START] Lancement du pipeline de Veille Technologique...")

    preflight_check()
    check_french_time()

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    paris_time = now_utc.astimezone(ZoneInfo("Europe/Paris"))
    today_str = paris_time.strftime("%d/%m/%Y")
    yesterday_str = (paris_time - datetime.timedelta(days=1)).strftime("%d/%m/%Y")

    memory_j_minus_1, existing_today_page_id = manage_notion_pages(today_str, yesterday_str)
    raw_articles, failed_feeds = asyncio.run(collect_rss_articles_async())
    gemini_data = process_with_gemini(raw_articles, memory_j_minus_1)

    page_url, reading_time = create_notion_journal_page(today_str, gemini_data, failed_feeds, existing_page_id=existing_today_page_id)

    articles_count = len(gemini_data.get("articles", []))
    tags = gemini_data.get("tags", [])
    send_telegram_notification(today_str, page_url, articles_count, reading_time, tags, failed_feeds)

    print("🎉 [FINISHED] Pipeline terminé avec succès !")

if __name__ == "__main__":
    main()
