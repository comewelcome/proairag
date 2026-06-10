# ProAiRag - Hybrid Multi-Tenant RAG System with Dashboard

ProAiRag est une plateforme RAG (Retrieval-Augmented Generation) multi-tenant avec isolation stricte des donnees, combinant **PostgreSQL + pgvector** pour la recherche vectorielle et **Neo4j** pour le raisonnement par graphe de connaissances.

Le projet inclut un **dashboard web complet** (React + Vite + TailwindCSS) pour gerer les entreprises, services, documents et conversations.

## Fonctionnalites

- **RAG hybride** : Recherche vectorielle (pgvector HNSW) + contexte graphe (Neo4j) fusionnes dans un prompt LLM
- **Multi-tenant** : Isolation complete au niveau application et base de donnees (RLS PostgreSQL)
- **Dashboard web** : Interface SPA avec gestion des entreprises, services, documents et chat
- **Upload de fichiers** : Support PDF, TXT, DOCX avec parsing automatique
- **Chat avec sessions** : Conversations persistantes avec sources et contexte graphe
- **Parametrage RAG** : Configuration par tenant (chunk size, LLM provider, etc.)
- **LLM configurable** : OpenAI-compatible API (par defaut sur localhost:1234) ou Ollama

## Architecture

```
+------------------------------------------------------------------+
|                    Docker Compose                                |
|                                                                  |
|  +------------+   +--------------------------------------------+ |
|  |   Nginx    |-->|              FastAPI (port 8000)           | |
|  |  (port 80) |   |  +-------------+  +----------------------+ | |
|  |            |   |  |  Frontend   |  |  /api/* (REST endpoints)| |
|  |            |   |  |  (SPA)      |  |                      | | |
|  +------------+   |  +-------------+  +----------------------+ | |
|                   +------------------+-------------------------+ |
|                                  |                              |
|                    +-------------+-------------+                |
|                    v                           v                |
|             +-------------+           +-------------+           |
|             |  PostgreSQL |           |    Neo4j    |           |
|             |  + pgvector |           |             |           |
|             +-------------+           +-------------+           |
+------------------------------------------------------------------+
```

## Quick Start

### 1. Installer les dependances

```bash
pip install -e ".[dev]"
```

### 2. Lancer l'infrastructure

```bash
docker compose up -d postgres neo4j
```

### 3. Configurer l'environnement

```bash
cp .env.example .env
# Editer .env avec vos valeurs
```

### 4. Lancer l'application

```bash
# Backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (dev)
cd frontend && npm run dev
# Dashboard sur http://localhost:5173 (proxy vers :8000)
```

### 5. Docker (production)

```bash
cd frontend && npm run build
docker compose up --build -d
# Dashboard sur http://localhost
```

## Dashboard

Le dashboard web offre les fonctionnalites suivantes :

- **Login** : Authentification JWT avec email + mot de passe
- **Dashboard** : Vue d'ensemble avec statistiques et actions rapides
- **Services** : CRUD des departements (services de l'entreprise)
- **Documents** : Upload par drag & drop (PDF, TXT, DOCX), liste avec filtres
- **Chat** : Interface de conversation style ChatGPT avec sessions et sources
- **Parametres** : Configuration RAG (chunk size, top K, LLM provider, etc.)

## API Endpoints

| Endpoint | Methode | Description |
|----------|---------|-------------|
| `/api/tenants/` | GET | Lister les tenants |
| `/api/tenants/` | POST | Creer un tenant |
| `/api/auth/login` | POST | Login (JWT) |
| `/api/departments/` | GET/POST | Lister/creer des services |
| `/api/documents/` | GET | Lister les documents |
| `/api/documents/upload` | POST | Upload de fichier |
| `/api/documents/{id}` | DELETE | Supprimer un document |
| `/api/rag/query` | POST | Query RAG hybride |
| `/api/chat/sessions/` | GET/POST | Lister/creer sessions |
| `/api/chat/sessions/{id}` | GET | Récupérer les messages |
| `/api/chat/sessions/{id}/send` | POST | Envoyer un message |
| `/api/settings/` | GET/PUT | Parametres RAG |
| `/api/settings/stats` | GET | Statistiques systeme |

## Configuration LLM

Par defaut, le systeme utilise un **API OpenAI-compatible sur localhost:1234** :

```bash
LLM_PROVIDER=openai
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_MODEL=gpt-4o-mini
```

Pour utiliser Ollama a la place :

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

## Structure du projet

```
proairag/
├── src/
│   ├── main.py                  # FastAPI app + SPA serving
│   ├── config.py                # Settings (LLM, RAG, DB)
│   ├── api/                     # REST API routes (8 routers)
│   ├── models/                  # SQLAlchemy ORM (8 models)
│   ├── schemas/                 # Pydantic v2 schemas
│   ├── services/               # Business logic (11 services)
│   ├── graph/                  # Neo4j integration
│   ├── middleware/             # JWT + API key auth
│   └── db/                     # Async SQLAlchemy
├── frontend/                    # React + Vite + Tailwind
│   ├── src/
│   │   ├── pages/              # 6 pages (Login, Dashboard, Services, Documents, Chat, Settings)
│   │   ├── components/         # Layout + common UI
│   │   ├── hooks/             # Auth context
│   │   ├── lib/               # API client (Axios)
│   │   └── types/             # TypeScript types
│   └── dist/                   # Build output
├── migrations/
│   ├── sql/                    # PostgreSQL (8 files)
│   └── cypher/                 # Neo4j (3 files)
├── Dockerfile                  # Backend Docker image
├── docker-compose.yml          # Full stack (postgres, neo4j, api, nginx)
├── nginx.conf                  # Reverse proxy config
└── test_dashboard.py           # Integration tests (15/15 OK)
```

## Tests

```bash
# Lancer les tests d'integration
python test_dashboard.py
```

## License

MIT
