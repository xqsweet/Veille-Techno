from requests import structures
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
# 2. HORAIRE ET DÉCLENCHEMENT (VERIFICATION HEURE FRANÇAISE / CRON-JOB)
# ---------------------------------------------------------------------------
def check_french_time():
    """
    Vérifie le déclenchement. Si workflow_dispatch ou manual, ignore.
    Sinon s'assure de l'exécution à l'heure FR.
    """
    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    if event_name == "workflow_dispatch":
        print("⚡ [TRIGGER] Déclenchement manuel / API (cron-job.org) détecté. Exécution immédiate.")
        return

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    paris_time = now_utc.astimezone(ZoneInfo("Europe/Paris"))
    print(f"🕒 [TIME CHECK] Heure actuelle à Paris : {paris_time.strftime('%Y-%m-%d %H:%M:%S')}")

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# 3. LISTE DES FLUX RSS & INGESTION ASYNCHRONE FAIL-SAFE
# ---------------------------------------------------------------------------
RSS_FEEDS = [
    # --- Flux Francophones (Conservés & Optimisés) ---
    "https://www.lemondeinformatique.fr/flux-rss/thematique/toutes-les-actualites/rss.xml",
    "https://www.01net.com/actualites/feed/",
    "https://www.frandroid.com/feed",
    "https://www.presse-citron.net/feed/",
    "https://www.iphon.fr/feed",
    "https://korben.info/feed",
    "https://linuxfr.org/news.atom",
    "https://www.cert.ssi.gouv.fr/feed/",
    "https://www.futura-sciences.com/rss/actualites.xml",
    "https://www.silicon.fr/feed",
    "https://www.developpez.com/index/rss",
    "https://www.it-connect.fr/feed/",
    "https://www.clubic.com/feed/news.rss",
    # --- Flux Internationaux (Cyber, Dev, Cloud & IA) ---
    "https://www.bleepingcomputer.com/feed/",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://hnrss.org/frontpage?points=100",
    "https://dev.to/feed",
    "https://thenewstack.io/blog/feed/",
    "https://feed.infoq.com/",
    "https://github.blog/feed/",
]

def sync_fallback_fetch(url, headers):
    """
    Fallback synchrone via requests en cas d'échec d'aiohttp.
    Exécuté hors du thread principal via asyncio.to_thread.
    """
    try:
        r = requests.get(url, headers=headers, timeout=12, verify=False)
        if r.status_code == 200:
            parsed = feedparser.parse(r.content)
            if parsed.entries:
                return parsed.entries, None
        return [], f"HTTP {r.status_code}"
    except Exception as e:
        return [], f"Exception ({type(e).__name__})"

async def fetch_feed(session, url, headers):
    """
    Tente la récupération asynchrone via aiohttp, puis bascule sur requests en fallback.
    """
    # 1. Tentative asynchrone (aiohttp)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=12), ssl=False) as response:
            if response.status == 200:
                content = await response.read()
                parsed = feedparser.parse(content)
                if parsed.entries:
                    return parsed.entries, None
    except Exception:
        pass

    # 2. Fallback synchrone non-bloquant en thread séparé
    entries, err_desc = await asyncio.to_thread(sync_fallback_fetch, url, headers)
    if entries:
        return entries, None
    
    print(f"❌ [RSS FAIL] {url} -> {err_desc}")
    return [], url

async def collect_rss_articles_async():
    print("📡 [RSS] Ingestion asynchrone des flux RSS (mode fail-safe high-reliability)...")
    articles = []
    failed_feeds = []
    
    headers = {
        "User-Agent": "feedparser/6.0.14 (Mozilla/5.0; +https://github.com)"
    }
    
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        tasks = [fetch_feed(session, url, headers) for url in RSS_FEEDS]
        results = await asyncio.gather(*tasks)
        
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        cutoff_time = now_utc - datetime.timedelta(hours=36)
        
        for entries, failed_url in results:
            if failed_url:
                failed_feeds.append(failed_url)
                continue
            
            for entry in entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                summary_clean = re.sub("<.*?>", "", summary)
                
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if published_parsed:
                    pub_dt = datetime.datetime(*published_parsed[:6], tzinfo=datetime.timezone.utc)
                    if pub_dt < cutoff_time:
                        continue
                
                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "summary": summary_clean[:300]
                    })
                    
    print(f"✅ [RSS] {len(articles)} articles récents collectés. ({len(failed_feeds)} flux indisponibles)")
    return articles, failed_feeds

# ---------------------------------------------------------------------------
# 4. GESTION DES PAGES NOTION & HISTORIQUE HEBDOMADAIRE
# ---------------------------------------------------------------------------
def get_notion_headers():
    token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

def manage_notion_pages(today_str, yesterday_str):
    """
    Gère la déduplication de la page Notion du jour et récupère la mémoire J-1.
    Compatible avec une Page Notion parente (page_id) ou une Base de Données (database_id).
    """
    target_id = os.getenv("NOTION_DATABASE_ID") or os.getenv("NOTION_PAGE_ID")
    headers = get_notion_headers()
    
    memory_j_minus_1 = ""
    existing_today_page_id = None
    
    try:
        # Essai 1: Si c'est une database
        url_db = f"https://api.notion.com/v1/databases/{target_id}/query"
        response = requests.post(url_db, headers=headers, json={"page_size": 10})
        
        # Essai 2: Si c'est une page parente, lister les enfants via /blocks/{id}/children
        if response.status_code != 200:
            url_blocks = f"https://api.notion.com/v1/blocks/{target_id}/children"
            response = requests.get(url_blocks, headers=headers)
            
        if response.status_code == 200:
            results = response.json().get("results", [])
            for page in results:
                title_text = ""
                # Si objet page Notion
                if page.get("object") == "page":
                    props = page.get("properties", {})
                    title_objs = props.get("title", {}).get("title", []) or props.get("Name", {}).get("title", []) or props.get("Titre", {}).get("title", [])
                    title_text = "".join([t.get("plain_text", "") for t in title_objs])
                # Si bloc child_page
                elif page.get("type") == "child_page":
                    title_text = page.get("child_page", {}).get("title", "")
                
                page_id = page.get("id")
                
                if f"Veille Tech - {today_str}" in title_text or f"Veille Tech du {today_str}" in title_text:
                    existing_today_page_id = page_id
                elif f"Veille Tech - {yesterday_str}" in title_text or f"Veille Tech du {yesterday_str}" in title_text:
                    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                    b_resp = requests.get(blocks_url, headers=headers)
                    if b_resp.status_code == 200:
                        b_results = b_resp.json().get("results", [])
                        texts = []
                        for b in b_results:
                            b_type = b.get("type")
                            if b_type and b_type in b:
                                rich_texts = b[b_type].get("rich_text", [])
                                texts.append("".join([rt.get("plain_text", "") for rt in rich_texts]))
                        memory_j_minus_1 = "\n".join(texts)[:2000]
    except Exception as e:
        print(f"⚠️ [NOTION MEMORY] Erreur lors de la gestion des pages : {e}")
        
    return memory_j_minus_1, existing_today_page_id

def get_weekly_notion_history():
    """
    Scrape l'historique des pages Notion des 7 derniers jours pour extraire les failles 🔴.
    """
    target_id = os.getenv("NOTION_DATABASE_ID") or os.getenv("NOTION_PAGE_ID")
    headers = get_notion_headers()
    
    weekly_texts = []
    try:
        url_db = f"https://api.notion.com/v1/databases/{target_id}/query"
        response = requests.post(url_db, headers=headers, json={"page_size": 15})
        if response.status_code != 200:
            url_blocks = f"https://api.notion.com/v1/blocks/{target_id}/children"
            response = requests.get(url_blocks, headers=headers)
            
        if response.status_code == 200:
            results = response.json().get("results", [])
            for page in results[:7]:
                page_id = page.get("id")
                blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                b_resp = requests.get(blocks_url, headers=headers)
                if b_resp.status_code == 200:
                    b_results = b_resp.json().get("results", [])
                    for b in b_results:
                        b_type = b.get("type")
                        if b_type and b_type in b:
                            rich_texts = b[b_type].get("rich_text", [])
                            text = "".join([rt.get("plain_text", "") for rt in rich_texts])
                            if "🔴" in text or "CRITIQUE" in text.upper() or "CVE" in text.upper():
                                weekly_texts.append(text)
    except Exception as e:
        print(f"⚠️ [NOTION WEEKLY HISTORY] Erreur lors de la récupération : {e}")
        
    return "\n".join(weekly_texts[:4000])

# ---------------------------------------------------------------------------
# 5. MOTEUR IA GEMINI (DAILY SYNTHESIS & WEEKLY TOP)
# ---------------------------------------------------------------------------
def process_with_gemini(raw_articles, memory_j_minus_1):
    print("🧠 [GEMINI] Analyse et synthèse par Gemini 3.5 Flash Lite...")
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    model = genai.GenerativeModel("gemini-3.5-flash-lite", safety_settings=safety_settings)
    
    prompt = f"""
Tu es un ingénieur Tech Lead expert en veille technologique et cybersécurité.
Voici la liste des articles collectés au cours des dernières 24-36h :
{json.dumps(raw_articles, ensure_ascii=False, indent=2)}

Voici un résumé de la veille d'hier (Mémoire J-1) à ne PAS répéter :
{memory_j_minus_1}

CONSIGNES DE TRAITEMENT :
1. Élimine les doublons stricts et les sujets déjà traités dans la mémoire J-1.
2. Classe les articles retenus dans exactement 5 catégories :
   - 🛡️ Cybersécurité & Vulnérabilités
   - 🤖 Intelligence Artificielle & Data
   - 💻 Développement, DevOps & Cloud
   - 📱 Consumer Tech, Hardware & OS
   - 🌐 Écosystème IT, Digital & Innovation
3. Pour chaque article, attribue un niveau de criticité/urgence :
   - 🔴 [CRITIQUE] : Faille zéro-day activement exploitée, panne majeure de service cloud/infrastructure mondial, menace immédiate.
   - 🟠 [ÉVOLUTION] : Publication de correctifs majeurs, mise à jour de version principale (v2.0, etc.), annonce produit importante.
   - 🟢 [INFO] : Bonnes pratiques, article de fond, tutoriel, annonce mineure.
4. Tri : À l'intérieur de chaque catégorie, classe impérativement les articles du plus urgent au moins urgent (🔴 puis 🟠 puis 🟢).
5. Résumé : Fournis un résumé synthétique clair et percutant de 2 à 3 phrases par article avec la référence exacte du lien fourni.
6. En Bref : Génère un chapeau "🚀 En bref" synthétisant en 3 à 5 puces les faits majeurs absolus de la journée.

Renvoie UNIQUEMENT un objet JSON valide structuré comme suit :
{{
  "en_bref": [
    "Puce 1...",
    "Puce 2..."
  ],
  "categories": {{
    "🛡️ Cybersécurité & Vulnérabilités": [
      {{
        "title": "🔴 [CRITIQUE] Titre de l'article",
        "link": "https://...",
        "summary": "Résumé clair et percutant."
      }}
    ],
    "🤖 Intelligence Artificielle & Data": [],
    "💻 Développement, DevOps & Cloud": [],
    "📱 Consumer Tech, Hardware & OS": [],
    "🌐 Écosystème IT, Digital & Innovation": []
  }}
}}
"""
    try:
        response = model.generate_content(prompt)
        text = response.text
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return json.loads(text)
    except Exception as e:
        print(f"❌ [GEMINI ERROR] Échec du traitement IA : {e}")
        return {
            "en_bref": ["Erreur de traitement IA lors de la génération."],
            "categories": {}
        }

def process_weekly_top_with_gemini(weekly_history_text):
    """
    Analyse l'historique de la semaine et génère la synthèse des failles critiques.
    Format orienté 'Impact Utilisateur' (iPhone, Mac, PC, Box Internet) SANS jargon dev.
    """
    print("🧠 [GEMINI] Génération du Bilan Hebdomadaire des Failles Critiques (Dimanche)...")
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    model = genai.GenerativeModel("gemini-3.5-flash-lite", safety_settings=safety_settings)
    
    prompt = f"""
Tu es un expert en cybersécurité et vulgarisation grand public.
Voici l'historique des vulnérabilités extraites des 7 derniers jours :
{weekly_history_text}

CONSIGNES STRICTES :
1. Extrais uniquement les failles réellement 🔴 [CRITIQUE] apparues cette semaine.
2. S'il y a 3 failles critiques ➔ Fais un Top 3. S'il y en a moins (1 ou 2) ➔ Fais un Top 1 ou Top 2 (NE FORCE PAS du remplissage avec des failles mineures !). S'il n'y en a aucune, indique qu'aucune faille critique majeure n'a été recensée cette semaine.
3. Formule le contenu en mode "IMPACT UTILISATEUR" (pour quelqu'un qui possède un iPhone, Mac, PC, Box Internet) SANS jargon de développeur inutile.

Chaque élément de la liste doit comporter :
- "title": Nom complet de la faille / Référence CVE
- "en_gros": Explication simple en 1 phrase claire
- "patch_status": Indicateur de statut du patch (ex: "✅ Patch officiel disponible." ou "❌ Aucun patch disponible pour l'instant (Zero-Day).")
- "impact": Précision claire sur les appareils de l'utilisateur touchés et l'action simple à faire (ex: "📲 Concerne ton Mac et ton iPhone. Lance la dernière mise à jour iOS/macOS.")

Renvoie UNIQUEMENT un objet JSON valide structuré comme suit :
{{
  "count": 2,
  "top_failles": [
    {{
      "title": "🔴 Faille critique Google Chrome & Safari — CVE-2026-XXXX",
      "en_gros": "Un pirate peut prendre le contrôle du navigateur si tu visites un site piégé.",
      "patch_status": "✅ Patch officiel disponible.",
      "impact": "📲 Concerne ton Mac et ton iPhone. Il te suffit de faire la dernière mise à jour Safari/iOS."
    }}
  ],
  "telegram_summary": "• 🔴 CVE-2026-XXXX — Zero-Day Chrome & iOS\\n• 🔴 CVE-2026-YYYY — Bypass Auth VPN"
}}
"""
    try:
        response = model.generate_content(prompt)
        text = response.text
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ [GEMINI WEEKLY TOP ERROR] Échec de la génération du Top hebdo : {e}")
        return None

# ---------------------------------------------------------------------------
# 6. CRÉATION & FORMATAGE DE LA PAGE NOTION
# ---------------------------------------------------------------------------
def parse_markdown_to_rich_text(text):
    """
    Transforme du texte contenant du Markdown **gras** en liste de rich_text pour Notion.
    """
    parts = re.split(r"(\*\*.*?\*\*)", text)
    rich_text = []
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            clean_content = part[2:-2]
            if clean_content:
                rich_text.append({
                    "type": "text",
                    "text": {"content": clean_content},
                    "annotations": {"bold": True}
                })
        else:
            if part:
                rich_text.append({
                    "type": "text",
                    "text": {"content": part}
                })
    return rich_text

def create_notion_journal_page(today_str, gemini_data, failed_feeds, existing_page_id=None, weekly_top_data=None):
    print("📝 [NOTION] Création / Remplacement de la page Journal Notion...")
    target_id = os.getenv("NOTION_DATABASE_ID") or os.getenv("NOTION_PAGE_ID")
    headers = get_notion_headers()
    
    if existing_page_id:
        print(f"🧹 [NOTION CLEANUP] Archivage de l'ancienne page du jour ({existing_page_id})...")
        archive_url = f"https://api.notion.com/v1/pages/{existing_page_id}"
        requests.patch(archive_url, headers=headers, json={"archived": True})
        
    page_title = f"Veille Tech - {today_str}"
    blocks = []
    
    # 1. BLOC APPEL EN TÊTE - FLUX RSS INDISPONIBLES (CONSERVÉ STRICTEMENT)
    if failed_feeds:
        failed_list = ", ".join([f.split('/')[2] for f in failed_feeds if '/' in f])
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"emoji": "⚠️"},
                "color": "yellow_background",
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"Information : {len(failed_feeds)} flux RSS n'ont pas pu être joints aujourd'hui ({failed_list}). La collecte s'est poursuivie normalement sur les autres sources."}
                }]
            }
        })

    # Calcul du temps de lecture global
    categories = gemini_data.get("categories", {})
    total_words = sum([len(a.get("summary", "").split()) for c in categories.values() for a in c])
    reading_time = max(1, math.ceil(total_words / 200))

    # 2. BLOC CALLOUT EN-TÊTE - METADONNÉES (TEMPS DE LECTURE & MOTS-CLÉS)
    blocks.append({
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"emoji": "📌"},
            "color": "gray_background",
            "rich_text": [
                {"type": "text", "text": {"content": f"⏱️ Temps de lecture estimé : {reading_time} min\n"}},
                {"type": "text", "text": {"content": "🏷️ Mots-clés du jour : #Cybersecurity #ZeroDay #AI #CloudNative #Hardware #DevOps"}}
            ]
        }
    })

    # 3. BLOC CALLOUT TOP FAILLES DE LA SEMAINE (UNIQUEMENT LE DIMANCHE)
    if weekly_top_data and weekly_top_data.get("top_failles"):
        top_list = weekly_top_data.get("top_failles", [])
        count = weekly_top_data.get("count", len(top_list))
        
        callout_texts = [{"type": "text", "text": {"content": f"🚨 TOP FAILLES CRITIQUES DE LA SEMAINE ({count})\n\n"}}]
        
        for idx, item in enumerate(top_list, 1):
            callout_texts.append({"type": "text", "text": {"content": f"{idx}. {item.get('title', '')}\n"}, "annotations": {"bold": True}})
            callout_texts.append({"type": "text", "text": {"content": f"• En gros : {item.get('en_gros', '')}\n"}})
            callout_texts.append({"type": "text", "text": {"content": f"• Statut du patch : {item.get('patch_status', '')}\n"}})
            callout_texts.append({"type": "text", "text": {"content": f"• Impact pour toi : {item.get('impact', '')}\n\n"}})
            
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"emoji": "🚨"},
                "color": "red_background",
                "rich_text": callout_texts
            }
        })
        
    # 4. SECTION EN BREF (AVEC PARSING DU MARROWDOWN **GRAS**)
    en_bref_items = gemini_data.get("en_bref", [])
    if en_bref_items:
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🚀 En bref"}}]
            }
        })
        for item in en_bref_items:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": parse_markdown_to_rich_text(item)
                }
            })

    # 5. SECTION CATEGORIES / TOGGLES (NUMÉROTÉES ET EN GRAS)
    cat_idx = 1
    for cat_name, articles in categories.items():
        if not articles:
            continue
            
        toggle_children = []
        for art in articles:
            title = art.get("title", "Article")
            link = art.get("link", "")
            summary = art.get("summary", "")
            
            rich_title = []
            if link:
                rich_title.append({
                    "type": "text",
                    "text": {"content": title, "link": {"url": link}},
                    "annotations": {"bold": True, "color": "blue"}
                })
            else:
                rich_title.append({
                    "type": "text",
                    "text": {"content": title},
                    "annotations": {"bold": True}
                })
                
            toggle_children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": rich_title,
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": summary}}]
                            }
                        }
                    ]
                }
            })
            
        blocks.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"{cat_idx}. {cat_name}"},
                    "annotations": {"bold": True}
                }],
                "children": toggle_children
            }
        })
        cat_idx += 1

    # CRÉATION DE LA PAGE DANS NOTION (Page parent, puis Database parent si échec)
    create_url = "https://api.notion.com/v1/pages"
    
    payload_page = {
        "parent": {"page_id": target_id},
        "properties": {
            "title": [{"type": "text", "text": {"content": page_title}}]
        },
        "children": blocks[:100]
    }
    
    res = requests.post(create_url, headers=headers, json=payload_page)
    
    if res.status_code != 200:
        print("⚠️ [NOTION] Tentative sous format database_id...")
        payload_db = {
            "parent": {"database_id": target_id},
            "properties": {
                "Name": {
                    "title": [{"type": "text", "text": {"content": page_title}}]
                }
            },
            "children": blocks[:100]
        }
        res = requests.post(create_url, headers=headers, json=payload_db)
        
    if res.status_code == 200:
        page_data = res.json()
        page_id_raw = page_data.get("id", "").replace("-", "")
        page_url = f"https://notion.so/{page_id_raw}"
        
        print(f"✅ [NOTION] Page créée avec succès : {page_url}")
        return page_url, reading_time
    else:
        print(f"❌ [NOTION ERROR] Échec de la création de la page. Statut HTTP {res.status_code} : {res.text}")
        return f"https://notion.so/{target_id.replace('-', '')}", reading_time

# ---------------------------------------------------------------------------
# 7. TELEGRAM PUSH NOTIFICATION
# ---------------------------------------------------------------------------
def send_telegram_notification(today_str, articles_count, reading_time, page_url, weekly_top_data=None):
    print("📲 [TELEGRAM] Envoi de la notification push...")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    msg = f"📊 *Veille Tech du {today_str}*\n\n"
    msg += f"• *{articles_count} articles* synthétisés\n"
    msg += f"• Temps de lecture : *~{reading_time} min*\n\n"
    
    if weekly_top_data and weekly_top_data.get("telegram_summary"):
        msg += "🚨 *FAILLES CRITIQUES DE LA SEMAINE*\n"
        msg += weekly_top_data.get("telegram_summary") + "\n\n"
        
    msg += f"🔗 [Consulter le journal complet sur Notion]({page_url})"
    
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("✅ [TELEGRAM] Notification envoyée avec succès sur iPhone !")
        else:
            print(f"⚠️ [TELEGRAM WARNING] Échec Markdown (HTTP {resp.status_code}). Tentative en texte brut...")
            plain_msg = f"📊 Veille Tech du {today_str}\n\n• {articles_count} articles synthétisés\n• Temps de lecture : ~{reading_time} min\n\n"
            if weekly_top_data and weekly_top_data.get("telegram_summary"):
                plain_msg += f"🚨 FAILLES CRITIQUES DE LA SEMAINE :\n{weekly_top_data.get('telegram_summary')}\n\n"
            plain_msg += f"Consulter le journal sur Notion : {page_url}"
            
            resp_fallback = requests.post(url, json={"chat_id": chat_id, "text": plain_msg}, timeout=10)
            if resp_fallback.status_code == 200:
                print("✅ [TELEGRAM] Notification fallback envoyée avec succès !")
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

    # Détection du jour (6 = Dimanche)
    is_sunday = (paris_time.weekday() == 6)
    weekly_top_data = None
    
    if is_sunday:
        print("📅 [SUNDAY DETECTED] Dimanche détecté. Lancement de l'analyse hebdo des failles critiques...")
        weekly_history_text = get_weekly_notion_history()
        if weekly_history_text:
            weekly_top_data = process_weekly_top_with_gemini(weekly_history_text)

    memory_j_minus_1, existing_today_page_id = manage_notion_pages(today_str, yesterday_str)

    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    is_manual = (event_name == "workflow_dispatch" or not event_name)

    if existing_today_page_id:
        if not is_manual:
            print(f"ℹ️ [IDEMPOTENCE] La page Notion 'Veille Tech - {today_str}' (ou du {today_str}) existe déjà ({existing_today_page_id}).")
            print("✅ Exécution automatique (cron) arrêtée proprement pour éviter les doublons.")
            sys.exit(0)
        else:
            print("⚡ [MANUAL OVERRIDE] Relance manuelle / test détectée. L'ancienne page du jour sera archivée et remplacée.")

    raw_articles, failed_feeds = asyncio.run(collect_rss_articles_async())
    gemini_data = process_with_gemini(raw_articles, memory_j_minus_1)

    page_url, reading_time = create_notion_journal_page(
        today_str, 
        gemini_data, 
        failed_feeds, 
        existing_page_id=(existing_today_page_id if is_manual else None),
        weekly_top_data=weekly_top_data
    )

    articles_count = sum([len(arts) for arts in gemini_data.get("categories", {}).values()])
    
    send_telegram_notification(
        today_str, 
        articles_count, 
        reading_time, 
        page_url,
        weekly_top_data=weekly_top_data
    )
    
    print("🎉 [SUCCESS] Pipeline exécuté et terminé avec succès !")

if __name__ == "__main__":
    main()