#!/usr/bin/env python3
"""
notion_ideas.py - Script de gestion & synchronisation de la Boîte à Idées avec Notion.

Supporte la détection d'ID de base de données inline depuis un ID de Page parent,
et l'extraction propre des 21 idées depuis le fichier Markdown.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_IDEAS_DATABASE_ID = os.getenv("NOTION_IDEAS_DATABASE_ID")
NOTION_VERSION = "2022-06-28"

# Cache global pour l'ID de base résolu
RESOLVED_DATABASE_ID = None


def get_headers():
    if not NOTION_TOKEN:
        raise ValueError("Erreur: La variable d'environnement NOTION_TOKEN est introuvable.")
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def make_notion_request(url, method="GET", payload=None):
    headers = get_headers()
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)
    except urllib.error.HTTPError as e:
        error_content = e.read().decode("utf-8")
        print(f"❌ Erreur HTTP {e.code} Notion API: {error_content}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"❌ Erreur réseau Notion API: {e.reason}", file=sys.stderr)
        raise


def resolve_database_id(target_id=None):
    global RESOLVED_DATABASE_ID
    if RESOLVED_DATABASE_ID and not target_id:
        return RESOLVED_DATABASE_ID

    raw_id = target_id or NOTION_IDEAS_DATABASE_ID
    if not raw_id:
        raise ValueError("Erreur: NOTION_IDEAS_DATABASE_ID non définie.")

    clean_id = raw_id.replace("-", "")

    # Tenter de requêter directement la base de données
    try:
        url = f"https://api.notion.com/v1/databases/{clean_id}"
        make_notion_request(url, method="GET")
        RESOLVED_DATABASE_ID = clean_id
        return clean_id
    except urllib.error.HTTPError as e:
        if e.code == 400:
            # L'ID fourni est probablement une Page contenant une base inline
            print("ℹ️ ID de Page détecté. Recherche automatique de la base de données inline associée...")
            children_url = f"https://api.notion.com/v1/blocks/{clean_id}/children"
            res = make_notion_request(children_url, method="GET")

            for block in res.get("results", []):
                if block.get("type") == "child_database":
                    db_id = block.get("id").replace("-", "")
                    print(f"✅ Base de données inline trouvée : {db_id}")
                    RESOLVED_DATABASE_ID = db_id
                    return db_id

            raise ValueError("Aucune base de données inline trouvée dans la page spécifiée.")
        raise


def get_database_schema(database_id=None):
    db_id = resolve_database_id(database_id)
    url = f"https://api.notion.com/v1/databases/{db_id}"
    return make_notion_request(url, method="GET")


def find_property_name(properties, target_names, prop_type=None):
    for target in target_names:
        for key, prop in properties.items():
            if key.lower() == target.lower():
                if prop_type is None or prop.get("type") == prop_type:
                    return key
    for target in target_names:
        for key, prop in properties.items():
            if target.lower() in key.lower():
                if prop_type is None or prop.get("type") == prop_type:
                    return key
    return None


def add_idea(title, status="🟡 À l'étude", priority="🟠 Moyenne", complexity="🛠️ Moyenne", impact="", description="", approach="", database_id=None):
    db_id = resolve_database_id(database_id)
    db_meta = get_database_schema(db_id)
    props_schema = db_meta.get("properties", {})

    title_prop = find_property_name(props_schema, ["Titre", "Title", "Nom", "Name"], "title") or "Titre"
    status_prop = find_property_name(props_schema, ["Statut", "Status", "État", "State"], "select") or "Statut"
    priority_prop = find_property_name(props_schema, ["Priorité", "Priority"], "select") or "Priorité"
    complexity_prop = find_property_name(props_schema, ["Complexité", "Complexity"], "select") or "Complexité"
    impact_prop = find_property_name(props_schema, ["Impact Codebase", "Impact", "Codebase"], "rich_text")
    desc_prop = find_property_name(props_schema, ["Description", "Résumé"], "rich_text")
    approach_prop = find_property_name(props_schema, ["Approche Technique", "Approche", "Technique"], "rich_text")

    status_options = props_schema.get(status_prop, {}).get("select", {}).get("options", [])
    matched_status = status
    for opt in status_options:
        opt_name = opt.get("name", "")
        clean_opt = re.sub(r"^[🔴🟠🟢🔵🟡✅\s]+", "", opt_name).strip().lower()
        clean_target = re.sub(r"^[🔴🟠🟢🔵🟡✅\s]+", "", status).strip().lower()
        if clean_opt == clean_target:
            matched_status = opt_name
            break

    payload_props = {
        title_prop: {
            "title": [{"text": {"content": title}}]
        },
        status_prop: {
            "select": {"name": matched_status}
        }
    }

    if priority_prop and priority_prop in props_schema:
        payload_props[priority_prop] = {"select": {"name": priority}}

    if complexity_prop and complexity_prop in props_schema:
        payload_props[complexity_prop] = {"select": {"name": complexity}}

    if impact_prop and impact:
        payload_props[impact_prop] = {"rich_text": [{"text": {"content": impact[:1000]}}]}

    if desc_prop and description:
        payload_props[desc_prop] = {"rich_text": [{"text": {"content": description[:1990]}}]}

    if approach_prop and approach:
        payload_props[approach_prop] = {"rich_text": [{"text": {"content": approach[:1990]}}]}

    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": db_id},
        "properties": payload_props
    }

    res = make_notion_request(url, method="POST", payload=payload)
    return res.get("id"), res.get("url")


def list_ideas(database_id=None):
    db_id = resolve_database_id(database_id)
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    res = make_notion_request(url, method="POST", payload={})
    results = res.get("results", [])

    ideas = []
    for page in results:
        props = page.get("properties", {})
        title_val = "Sans titre"
        for k, v in props.items():
            if v.get("type") == "title" and v.get("title"):
                title_val = v["title"][0].get("text", {}).get("content", "Sans titre")
                break

        ideas.append({
            "id": page.get("id"),
            "title": title_val,
            "url": page.get("url"),
        })

    return ideas


def parse_markdown_ideas(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Fichier introuvable : {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Ne traiter que les en-têtes ### (H3)
    raw_blocks = re.split(r"\n(?=### )", content)
    parsed_ideas = []

    for block in raw_blocks:
        if not block.strip().startswith("### "):
            continue

        lines = block.strip().split("\n")
        raw_title_line = lines[0].replace("### ", "").strip()

        clean_title = re.sub(r"<[^>]+>", "", raw_title_line).strip()
        clean_title = re.sub(r"^[🔴🟠🟢🔵🟣💡\s]+", "", clean_title).strip()
        if not clean_title or clean_title.startswith("[Titre") or "Modèle" in clean_title:
            continue

        status = "🟡 À l'étude"
        priority = "🟠 Moyenne"
        complexity = "🛠️ Moyenne"
        impact = ""

        current_section = None
        desc_lines = []
        app_lines = []

        for line in lines[1:]:
            line_str = line.strip()

            if "Statut :" in line_str:
                match = re.search(r"Statut :[\*\s\`>]*([^\`\|\n]+)", line_str)
                if match:
                    status = match.group(1).strip()
            elif "Priorité :" in line_str:
                match = re.search(r"Priorité :[\*\s\`>]*([^\`\|\n]+)", line_str)
                if match:
                    priority = match.group(1).strip()
            elif "Complexité :" in line_str:
                match = re.search(r"Complexité :[\*\s\`>]*([^\`\|\n]+)", line_str)
                if match:
                    complexity = match.group(1).strip()
            elif "Impact Codebase :" in line_str:
                match = re.search(r"Impact Codebase :[\*\s\`>]*([^\`\n]+)", line_str)
                if match:
                    impact = match.group(1).strip()

            elif line_str.startswith("#### Description") or line_str.startswith("#### 📖 Description"):
                current_section = "desc"
            elif line_str.startswith("#### Approche") or line_str.startswith("#### 🛠️ Approche"):
                current_section = "app"
            elif line_str.startswith("#### "):
                current_section = None
            elif current_section == "desc" and line_str and not line_str.startswith(">"):
                desc_lines.append(line_str)
            elif current_section == "app" and line_str and not line_str.startswith(">"):
                app_lines.append(line_str)

        parsed_ideas.append({
            "title": clean_title,
            "status": status,
            "priority": priority,
            "complexity": complexity,
            "impact": impact,
            "description": "\n".join(desc_lines).strip(),
            "approach": "\n".join(app_lines).strip(),
        })

    return parsed_ideas


def import_ideas_to_notion(filepath, database_id=None):
    ideas = parse_markdown_ideas(filepath)
    print(f"Extracting {len(ideas)} ideas from {filepath}. Starting import to Notion...")

    success_count = 0
    for idx, idea in enumerate(ideas, start=1):
        try:
            page_id, url = add_idea(
                title=idea["title"],
                status=idea["status"],
                priority=idea["priority"],
                complexity=idea["complexity"],
                impact=idea["impact"],
                description=idea["description"],
                approach=idea["approach"],
                database_id=database_id
            )
            print(f"  [OK] [{idx}/{len(ideas)}] Added : {idea['title']}")
            success_count += 1
            time.sleep(0.4)
        except Exception as e:
            print(f"  [FAIL] [{idx}/{len(ideas)}] Failed for {idea['title']}: {e}")

    print(f"\nImport finished : {success_count}/{len(ideas)} ideas created successfully.")


def main():
    parser = argparse.ArgumentParser(description="Script de synchronisation des idées avec Notion")
    parser.add_argument("--list", action="store_true", help="Lister les idées de la base Notion")
    parser.add_argument("--import-md", type=str, help="Importer un fichier Markdown dans Notion")
    parser.add_argument("--add-title", type=str, help="Titre d'une nouvelle idée à ajouter")
    parser.add_argument("--desc", type=str, default="", help="Description de l'idée")
    parser.add_argument("--priority", type=str, default="🟠 Moyenne", help="Priorité")

    args = parser.parse_args()

    if args.list:
        try:
            ideas = list_ideas()
            print(f"\nTotal : {len(ideas)} ideas in Notion\n")
            for idea in ideas:
                print(f"- {idea['title']}")
        except Exception as e:
            print(f"Error : {e}")

    elif args.import_md:
        try:
            import_ideas_to_notion(args.import_md)
        except Exception as e:
            print(f"Error importing : {e}")

    elif args.add_title:
        try:
            page_id, url = add_idea(title=args.add_title, priority=args.priority, description=args.desc)
            print(f"Idea added successfully ! URL: {url}")
        except Exception as e:
            print(f"Error adding : {e}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
