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

---

### 💡 Filtre Anti-Bruit Sémantique & Score de Pertinence Sur-Mesure

- **Statut :** 🟡 À l'étude
- **Priorité :** 🔴 Haute
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Faible (`main.py` + fichier `config/interest_matrix.json`)

#### Description
Mettre en place une matrice d'intérêt personnalisée pour filtrer le bruit médiatique et éviter la surpolluer la veille quotidienne. Gemini attribue à chaque sujet collecté un score de pertinence (0 à 100) en s'appuyant sur vos sujets prioritaires et thèmes à ignorer. Seuls les articles dépassant un seuil défini (ex: > 70/100) sont publiés dans Notion et Telegram.

#### Approche Technique Pressentie
- Créer un fichier de configuration JSON `config/interest_matrix.json` définissant :
  - **Mots-clés / Domaines prioritaires** (ex: *Cyber, DevOps, IA, Rust, Architecture*).
  - **Mots-clés / Domaines à ignorer** (ex: *Hardware/Bons plans, Rumeurs smartphone, Finance/Crypto*).
  - **Seuil minimal de pertinence** (ex: `70`).
- Adapter le prompt système de Gemini dans `main.py` pour qu'il calcule et retourne la note de pertinence ainsi que le motif de rétention pour chaque article.

---

### 💡 Watchlist de Releases & Monitoring de Dépendances Open-Source

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟠 Moyenne
- **Complexité :** 🛠️ Moyenne
- **Impact Codebase :** Moyen (`main.py` / intégration d'un module de collecte de releases)

#### Description
Surveiller automatiquement les nouvelles versions et mises à jour majeures des bibliothèques, frameworks et outils essentiels utilisés dans vos projets (ex: *Python, Docker, Next.js, FastAPI, Linux*). En cas de mise à jour majeure ou de correctif de sécurité critique lié à ces outils, le rapport génère un encadré d'alerte spécifique.

#### Approche Technique Pressentie
- Exploiter les flux RSS de releases GitHub (`https://github.com/{owner}/{repo}/releases.atom`) ou l'API GitHub Releases.
- Parser le CHANGELOG et les notes de version pour détecter les *breaking changes* et failles de sécurité via Gemini.
- Intégration d'un toggle dédié "📦 Releases & Dépendances" dans la page Notion et d'un résumé dans le push Telegram.

---

### 💡 Mode "Deep Dive & Plan d'Action" pour Failles Critiques

- **Statut :** 🟡 À l'étude
- **Priorité :** 🔴 Haute
- **Complexité :** 🛠️ Moyenne
- **Impact Codebase :** Moyen (`main.py`)

#### Description
Lorsque Gemini identifie une faille de sécurité 🔴 `[CRITIQUE]`, le pipeline déclenche automatiquement un second appel ciblé pour produire un guide d'impact comprenant les versions applicatives vulnérables, le niveau de sévérité CVSS, les commandes de mitigation ou patchs à appliquer immédiatement, et une procédure de contournement (*workaround*).

#### Approche Technique Pressentie
- Ajouter un second prompt Gemini conditionnel exécuté uniquement si un sujet 🔴 `[CRITIQUE]` est détecté.
- Générer un bloc Callout d'alerte spécifique dans Notion ainsi qu'un encadré prioritaire dans la notification Telegram.

---

### 💡 Détection des Projets Émergents (GitHub Trending & Stars Velocity)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟠 Moyenne
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Moyen (`main.py`)

#### Description
Interroger chaque jour l'API GitHub pour découvrir et suivre les nouveaux projets open-source connaissant une croissance rapide de stars (*velocity*) dans des domaines stratégiques (ex: *DevTools, AI Agents, CLI, Security*).

#### Approche Technique Pressentie
- Effectuer des requêtes sur l'API REST `api.github.com/search/repositories` avec filtrage par date de création récente et tri par stars.
- Faire synthétiser par Gemini l'utilité du repository en 2 phrases et son cas d'usage principal.

---

### 💡 Archivage Auto-Hébergé & Backup Git Markdown

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟢 Basse
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Faible (`main.py` + `.github/workflows/daily_veille.yml`)

#### Description
Conserver un historique local et auto-hébergé au format Markdown de toutes les synthèses quotidiennes générées, organisées par sous-dossiers mensuels (`archives/YYYY-MM/JJ-MM-AAAA.md`).

#### Approche Technique Pressentie
- Écrire un fichier `.md` propre à la fin de l'exécution du script `main.py`.
- Ajouter une étape `git commit & push` automatique dans le workflow GitHub Actions pour pousser l'archive sur le dépôt.

---

### 💡 Synthèse Automatique des Vidéos & Transcriptions Tech (YouTube)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟢 Basse
- **Complexité :** 🏗️ Élevée
- **Impact Codebase :** Moyen à Élevé (`main.py` + dépendance `youtube-transcript-api`)

#### Description
Extraire automatiquement les transcriptions texte des nouvelles vidéos publiées par une sélection de chaînes YouTube de référence (ex: *Fireship, Theo - t3.gg, The Primeagen*) afin que Gemini résume l'essentiel de la vidéo sous forme de points clés sans nécessiter de visionnage.

#### Approche Technique Pressentie
- Surveiller les flux RSS des chaînes YouTube (`https://www.youtube.com/feeds/videos.xml?channel_id=...`).
- Récupérer les sous-titres/transcriptions via `youtube-transcript-api` et les passer au moteur Gemini pour extraction synthétique.

---

### 💡 Health Check & Auto-Healing des Flux RSS

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟠 Moyenne
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Faible (`main.py`)

#### Description
Vérifier l'état de santé des flux RSS lors de chaque exécution quotidienne. Si un flux renvoie une erreur HTTP persistante (404, 500, SSL) ou ne publie aucun article depuis plus de 30 jours, le script émet une alerte Telegram dédiée recommandant sa désactivation ou son remplacement.

#### Approche Technique Pressentie
- Enregistrer les métadonnées de statut HTTP et les timestamps du dernier article par flux.
- Ajouter un test d'inactivité/erreur à la fin du traitement RSS et envoyer une notification synthétique à l'administrateur du bot.

---

### 💡 Graph de Connaissances & Cartographie des Technos (Mermaid / Obsidian)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟢 Basse
- **Complexité :** 🏗️ Élevée
- **Impact Codebase :** Moyen à Élevé (`main.py`)

#### Description
Cartographier visuellement les interconnexions entre les outils, langages et concepts cités dans vos veilles (ex: *Docker ➔ Kubernetes ➔ Helm*). Générer un diagramme dynamique au format Mermaid inséré directement dans Notion ou sous forme de liens wiki `[[Techno]]` compatibles Obsidian.

#### Approche Technique Pressentie
- Demander à Gemini d'extraire des paires de relations structurées JSON (`concept_source` -> `relation` -> `concept_cible`).
- Convertir le JSON en bloc de code `mermaid` et l'injecter dans la page Notion quotidienne ou l'archive Markdown.

---

### 💡 Moteur de Recherche Sémantique (RAG & Base Vectorielle ChromaDB)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟠 Moyenne
- **Complexité :** 🏗️ Élevée
- **Impact Codebase :** Moyen à Élevé (`main.py` + stockage vectoriel)

#### Description
Créer un moteur de recherche sémantique indexant l'historique complet des synthèses de veille au format vectoriel (embeddings). Permet d'interroger la base de connaissance en langage naturel (ex: *"Quelles sont les failles critiques révélées sur Linux cette année ?"*) et d'extraire les passages pertinents même si les mots-clés exacts ne correspondent pas.

#### Approche Technique Pressentie
- Générer des vector embeddings avec l'API Gemini ou SentenceTransformers lors de la publication de chaque page.
- Stocker les vecteurs dans une base légère (ex: ChromaDB local ou Qdrant Cloud).
- Interroger la base vectorielle avant la génération pour enrichir le contexte d'apprentissage.

---

### 💡 Déduplication Intra-Jour Avancée par Similarité Cosinus

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟠 Moyenne
- **Complexité :** 🛠️ Moyenne
- **Impact Codebase :** Faible à Moyen (`main.py`)

#### Description
Calculer la similarité cosinus sémantique entre les titres et contenus des articles collectés le jour même par les différents flux RSS. Permet de fusionner les doublons avant l'appel à l'IA pour réduire la consommation de tokens et éviter la répétition du même sujet sous des angles légèrement différents.

#### Approche Technique Pressentie
- Vectoriser rapidement les titres/résumés d'articles à la fin du scraping RSS.
- Appliquer un filtre de similarité avec un seuil de coupure (ex: `similarity > 0.85`) pour regrouper les articles connexes en une seule entrée avant le prompt Gemini.

---

### 💡 Auto-Maintenance & Dependabot pour le Pipeline Veille-Techno

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟢 Basse
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Faible (`.github/dependabot.yml`)

#### Description
Mettre en place la surveillance et la mise à jour automatique des dépendances Python du projet (`aiohttp`, `requests`, `feedparser`, `google-genai`) afin de prévenir les pannes causées par des ruptures d'API ou des failles dans les packages d'ingestion.

#### Approche Technique Pressentie
- Créer le fichier de configuration `.github/dependabot.yml` avec stratégie d'analyse hebdomadaire du fichier `requirements.txt`.
- Configurer les Pull Requests automatiques avec vérification par les workflows CI/CD.

---

### 💡 Index de Crédibilité des Sources & Pondération des Flux

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟠 Moyenne
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Faible (`main.py`)

#### Description
Attribuer un score de réputation/fiabilité à chaque flux RSS (ex: blogs officiels d'éditeurs AWS/Kubernetes = score 100 vs blogs d'actualités génériques = score 70). Les actualités provenant de sources officielles prioritaires bénéficient d'une mise en avant préférentielle dans Notion et Telegram.

#### Approche Technique Pressentie
- Ajouter un champ `weight` numérique dans la liste de configuration des flux RSS.
- Transmettre la note de réputation de la source à Gemini pour pondérer la note d'urgence et le tri d'affichage.

---

### 💡 Indicateur de Complexité Technique & Temps de Lecture Estimé

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟢 Basse
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Faible (`main.py`)

#### Description
Ajouter à chaque sujet récapitulé deux métadonnées pratiques : le temps de lecture estimé de l'article d'origine (ex: ⏱️ 4 min) et son niveau de technicité (🟢 Vulgarisé / 🟠 Intermédiaire / 🔴 Expert Deep Tech).

#### Approche Technique Pressentie
- Calculer le temps de lecture estimé basé sur le nombre de mots du corps de l'article (`word_count / 200`).
- Demander à Gemini de qualifier le niveau d'expertise technique requis (1 à 3) et l'afficher sous forme d'un badge dans le header Notion.

---

### 💡 Multi-LLM Redundancy & Fallback Automatique (Gemini / Groq / DeepSeek)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🔴 Haute
- **Complexité :** 🛠️ Moyenne
- **Impact Codebase :** Moyen (`main.py`)

#### Description
Mettre en place un basculement automatique (*failover*) vers une seconde API d'IA gratuite (ex: Groq API avec Llama 3 ou DeepSeek) en cas d'erreur de quota (`429 Rate Limit`) ou d'indisponibilité temporaire du service Google AI Studio.

#### Approche Technique Pressentie
- Créer une classe d'abstraction `LLMClient` enveloppant l'appel Gemini dans un bloc `try/except`.
- En cas d'exception HTTP 429 ou 5xx, basculer sur un second provider configuré via des secrets d'environnement (`GROQ_API_KEY` ou `DEEPSEEK_API_KEY`).

---

### 💡 Traduction Bilingue & Glossaire Technique Anglais/Français

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟢 Basse
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Faible (`main.py`)

#### Description
Pour l'ensemble des articles issus de flux anglophones, générer la synthèse en français tout en enrichissant chaque section d'un toggle dépliant "📖 Glossaire & Vocabulaire Tech" listant les termes, acronymes et expressions techniques d'origine avec leur traduction et explication.

#### Approche Technique Pressentie
- Ajouter des instructions spécifiques dans le prompt système de Gemini pour extraire une liste de paires `mot_cle_en`: `traduction_fr_et_contexte`.
- Restituer cette liste sous forme d'un composant Toggle dépliant Notion dédié.

---

### 💡 Ingestion & Transcription de Podcasts Tech Audio (RSS Audio)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟢 Basse
- **Complexité :** 🏗️ Élevée
- **Impact Codebase :** Moyen à Élevé (`main.py` + traitement audio)

#### Description
Étendre la collecte de veille aux flux RSS de podcasts audio spécialisés (ex: *NoLimitSecu, Software Engineering Daily*). Le script télécharge le fichier audio du nouvel épisode et utilise Gemini Audio ou Whisper API pour générer automatiquement un compte-rendu synthétique structuré.

#### Approche Technique Pressentie
- Parser les balises `<enclosure url="..." type="audio/mpeg">` dans les flux RSS audio.
- Envoyer le fichier audio MP3 ou l'URL directement à l'API multimodal Gemini pour extraire un résumé écrit en 5 points clés.

---

### 💡 Benchmark & Suivi Métrique du Moteur IA (Tokens & Latence)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟢 Basse
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Faible (`main.py`)

#### Description
Enregistrer à chaque exécution du pipeline les métadonnées de performance du modèle d'IA : nombre de tokens d'entrée et de sortie consommés, temps de latence de la réponse (en secondes) et estimation du coût financier.

#### Approche Technique Pressentie
- Récupérer l'objet `usage_metadata` (prompt_token_count, candidates_token_count) retourné par l'API Gemini.
- Formater un callout de métriques techniques à la fin de la page Notion et enregistrer l'historique dans un journal de performance.

---

### 💡 Détecteur de Breaking Changes & APIs Dépréciées (Breaking Change Guard)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🔴 Haute
- **Complexité :** 🛠️ Moyenne
- **Impact Codebase :** Moyen (`main.py`)

#### Description
Lors de la détection de nouvelles versions d'outils, langages ou frameworks, faire analyser par Gemini le changelog pour extraire la liste explicite des méthodes et signatures d'APIs supprimées/dépréciées (*Deprecation Warnings*), ainsi que les étapes d'adaptation indispensables pour vos projets.

#### Approche Technique Pressentie
- Configurer une étape d'analyse ciblée sur les sections "Breaking Changes" et "Deprecated" des Release Notes.
- Formater un encadré d'avertissement rouge dans la page Notion et générer une alerte spécifique dans la notification Telegram.

---

### 💡 Croisement Automatique avec le Catalogue CISA KEV (Failles Exploitées in the Wild)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🔴 Haute
- **Complexité :** 🛠️ Moyenne
- **Impact Codebase :** Moyen (`main.py`)

#### Description
Interroger le catalogue officiel CISA KEV (*Known Exploited Vulnerabilities*) pour vérifier si les failles de sécurité recensées dans votre veille font l'objet d'exploitations actives dans le monde réel par des groupes d'attaquants.

#### Approche Technique Pressentie
- Télécharger et mettre en cache le flux JSON public de la CISA (`known_exploited_vulnerabilities.json`).
- Croiser les identifiants CVE extraits des articles me avec le catalogue CISA KEV et ajouter le tag "⚠️ ACTIVE EXPLOITATION" dans Notion et Telegram en cas de correspondance.

---

### 💡 Privacy Guard & Anonymisation Pré-IA

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟢 Basse
- **Complexité :** ⚡ Faible
- **Impact Codebase :** Faible (`main.py`)

#### Description
Mettre en place un module de filtrage Regex automatique avant tout envoi de contenu vers l'API Gemini ou Notion. Ce filtre masque les données sensibles accidentelles (clés d'API de test divulguées dans des articles, adresses IP privées, tokens JWT ou emails personnels) pour garantir la confidentialité et la sécurité du pipeline.

#### Approche Technique Pressentie
- Implémenter une fonction de nettoyage de texte par expressions régulières (Regex) en amont du pipeline de traitement IA.
- Remplacer les patterns sensibles identifiés par des tokens génériques (ex: `[REDACTED_API_KEY]`, `[REDACTED_IP]`).

---

### 💡 Intégration n8n : Scraper Intelligent en Amont (Option 3)

- **Statut :** 🟡 À l'étude
- **Priorité :** 🟠 Moyenne
- **Complexité :** 🛠️ Moyenne
- **Impact Codebase :** main.py (adaptation de l'ingestion pour accepter un payload JSON en plus du RSS) + fichier YAML GitHub Actions (accepter input JSON).

#### Description
Utiliser n8n comme pré-traitement pour scraper des sources non-RSS (Discord, YouTube, Web) et envoyer les données au pipeline actuel via Webhook.

Actuellement, le script Python lit des flux RSS standard. n8n pourrait servir à collecter des données là où le RSS n'existe pas, pour les fournir au script Python.
- **Architecture :** n8n scrape des pages web complexes, écoute des canaux Discord/Slack spécifiques, ou extrait des données de vidéos YouTube. n8n formate ces données brutes en JSON et déclenche le webhook GitHub Actions en lui passant les datas en payload.
- **Avantages :** Élargit drastiquement les sources d'information au-delà du simple format RSS.
- **Inconvénients :** Ajoute une brique d'infrastructure supplémentaire avant l'exécution du script Python.

#### Approche Technique Pressentie
Scraping n8n en amont -> Webhook GitHub Actions payload JSON -> Ingestion Python
