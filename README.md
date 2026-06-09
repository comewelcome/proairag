# ProAirAg - Hybrid Multi-Tenant RAG

Systeme RAG hybride combinant:
- **PostgreSQL + pgvector**: Stockage vectoriel securise avec Row-Level Security
- **Neo4j**: Knowledge graph pour la comprehension semantique des relations

## Architecture

La securite multi-tenant est garantie a DEUX niveaux:
1. **Application**: Le middleware extrait le tenant_id et l'injecte dans chaque requete
2. **Base de donnees**: Les politiques RLS PostgreSQL bloquent physiquement l'acces croise

Meme si une faille apparait au niveau application, le niveau RLS de PostgreSQL
empeche tout acces aux donnees d'un autre tenant.

## Structure du projet

```
proairag/
├── src/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── middleware/tenant.py    # Tenant context + API key validation
│   ├── models/                 # SQLAlchemy models (Tenant, Document, Chunk)
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic
│   │   ├── tenant_service.py
│   │   ├── embedding_service.py
│   │   ├── ingestion_service.py
│   │   ├── vector_service.py
│   │   ├── graph_service.py
│   │   ├── rag_service.py
│   │   └── llm_service.py
│   ├── graph/                  # Neo4j integration
│   │   ├── neo4j_client.py
│   │   ├── entity_extractor.py
│   │   └── graph_sync.py
│   └── api/                    # REST routes
│       ├── tenants.py
│       ├── documents.py
│       └── rag.py
├── migrations/
│   ├── sql/                    # PostgreSQL migrations + RLS policies
│   └── cypher/                 # Neo4j schema
├── tests/
├── docker-compose.yml
└── pyproject.toml
```

## Securite - Defense en Profondeur

| Niveau | Mecanisme | Garantie |
|---|---|---|
| API | X-API-Key validation | AuthN + tenant resolution |
| Middleware | Tenant context injection | tenant_id sur chaque requete |
| Service | tenant_id dans chaque query | Isolation applicative |
| SQL | WHERE tenant_id = $tenant_id | Filtre explicite |
| RLS | PostgreSQL policies | Garde ultime (moteur DB) |
| Graph | WHERE tenant_id sur chaque Cypher | Isolation Neo4j |
| FK | FOREIGN KEY + ON DELETE CASCADE | Integrite referentielle |

## Demarrage rapide

```bash
# 1. Copier la configuration
cp .env.example .env

# 2. Lancer l'infrastructure
docker-compose up -d

# 3. Installer les dependances
pip install -e ".[dev]"

# 3b. Pour les embeddings de qualite (optionnel, ~2Go avec torch) :
pip install -e ".[embedding]"
# Sans cela, un fallback hash-based est utilise (functional mais moins precis)

# 4. Lancer l'application
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 5. Tester
curl http://localhost:8000/health
```

## API

### Creer un tenant
```bash
curl -X POST http://localhost:8000/tenants/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Mon Entreprise"}'
# -> {"id": "...", "name": "Mon Entreprise", "api_key": "sk-...", ...}
```

### Ingester un document
```bash
curl -X POST http://localhost:8000/documents/ \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Politique RH",
    "content": "Notre politique de conges...",
    "source": "hr/policy.pdf"
  }'
```

### Poser une question RAG
```bash
curl -X POST http://localhost:8000/rag/query \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quelle est la politique de conges ?",
    "top_k": 5,
    "include_graph_context": true
  }'
```

## Flux RAG Hybride

```
QUERY
  |
  v
[1. Embedding de la requete]
  |
  v
[2a. Recherche vectorielle]    [2b. Extraction entites + graph context]
     (pgvector, tenant-isolated)      (Neo4j, tenant-isolated)
  |                                 |
  v                                 v
Chunks similaires              Relations semantiques
  |                                 |
  v                                 v
[3. Fusion du contexte enrichi]
  |
  v
[4. Generation LLM]
```

## Technologies

- Python 3.11+
- FastAPI
- PostgreSQL 15 + pgvector
- Neo4j 5.x
- SQLAlchemy 2.0 (async)
- sentence-transformers
- LangChain
- Docker + Docker Compose
