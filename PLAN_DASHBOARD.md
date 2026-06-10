# ProAiRag Dashboard - Plan d'Action Detaille

## ETAAT : TOUTES LES PHASES COMPLETEES (2026-06-10)

### Resultat des tests : 15/15 OK
- Health, SPA, Tenants (CRUD + list), Login, Departments, Documents (upload + list + delete)
- RAG query (avec fallback LLM), Chat (create + send + list)
- Settings (get + update + stats)
- PostgreSQL: connecté | Neo4j: connecté

## Vision du Dashboard

Application web monopage (SPA) React intégrée au backend FastAPI existant, offrant
une interface visuelle complète pour gérer les entreprises (tenants), services (departments),
documents, et conversations RAG — le tout configurable via une section paramètres.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Docker Compose                            │
│                                                                 │
│  ┌──────────────┐   ┌───────────────────────────────────────┐   │
│  │   Nginx      │   │         FastAPI (port 8000)           │   │
│  │ (port 80)    │──▶│  ┌──────────┐  ┌──────────────────┐  │   │
│  │              │   │  │ /docs    │  │ /api/*            │  │   │
│  │              │   │  │ (React   │  │   (REST endpoints)│  │   │
│  │              │   │  │  build)  │  │                   │  │   │
│  │              │   │  └──────────┘  └──────────────────┘  │   │
│  └──────────────┘   └──────────────┬──────────────────────┘   │
│                                    │                           │
│                         ┌──────────┴──────────┐               │
│                         ▼                     ▼               │
│                  ┌─────────────┐      ┌─────────────┐         │
│                  │  PostgreSQL │      │    Neo4j    │         │
│                  │  + pgvector │      │             │         │
│                  └─────────────┘      └─────────────┘         │
│                                                                 │
│  Frontend source: frontend/                                    │
│  Build output: frontend/dist/ → monté dans src/static/         │
└─────────────────────────────────────────────────────────────────┘
```

### Flux de navigation

```
Landing / Login
       │
       ▼
  Selection du tenant (si multi-tenant)
       │
       ▼
┌──────┴──────┐
│  Sidebar    │
│  ┌────────┐ │
│  │ Projet │ ├──────── Main Content Area ────────┐
│  │ Services│ │                                  │
│  │ Documents│ │                                  │
│  │  Chat   │ │                                  │
│  │ Paramètres│ │                                  │
│  └────────┘ │                                  │
└─────────────┘                                  │
```

---

## Phases d'implémentation

### Phase 1 : Squelette Frontend + Intégration FastAPI (2-3h)

#### 1.1 Initialisation du projet React
```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── tsconfig.json
├── tsconfig.node.json
├── src/
│   ├── main.tsx                    # Entry point
│   ├── App.tsx                     # Router + layout principal
│   ├── index.css                   # Tailwind directives + custom styles
│   ├── lib/
│   │   └── api.ts                  # Axios client (base URL, JWT interceptor)
│   ├── hooks/
│   │   └── useAuth.ts              # Context auth (login/logout/tenant)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx         # Navigation latérale
│   │   │   ├── Header.tsx          # Header avec nom du tenant + user
│   │   │   └── Layout.tsx          # Layout global (sidebar + content)
│   │   └── ui/                     # Shadcn/UI components (copiés depuis shadcn)
│   │       ├── button.tsx
│   │       ├── input.tsx
│   │       ├── dialog.tsx
│   │       ├── card.tsx
│   │       ├── select.tsx
│   │       ├── textarea.tsx
│   │       ├── dropdown-menu.tsx
│   │       ├── tabs.tsx
│   │       ├── toast.tsx
│   │       └── badge.tsx
│   ├── pages/
│   │   ├── Login.tsx               # Page de connexion
│   │   ├── TenantSelect.tsx        # Selection du tenant
│   │   ├── Dashboard.tsx           # Page d'accueil (sumé du projet)
│   │   ├── Services.tsx            # CRUD des services (departments)
│   │   ├── Documents.tsx           # Upload + liste des documents
│   │   ├── Chat.tsx                # Interface de chat RAG
│   │   └── Settings.tsx            # Paramètres RAG
│   └── types/
│       └── index.ts                # Types TypeScript partagés
├── components.json                 # Shadcn config
└── .env                            # VITE_API_URL=http://localhost:8000
```

**Commandes:**
```bash
cd /home/yo/Desktop/code/proairag
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install axios @tanstack/react-router class-variance-authority clsx tailwind-merge lucide-react react-dropzone sonner
npx shadcn@latest init  # pour les composants UI
```

#### 1.2 Configuration Vite
- `server.proxy` pour rediriger `/api/*` vers `http://localhost:8000` (dev)
- Build output → `dist/`
- Base path configurable (`/` en prod, `/dashboard` si besoin)

#### 1.3 Intégration FastAPI
Fichier modifié: `src/main.py`
```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# After routers:
static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Fallback: serve index.html for any non-API route (SPA routing)"""
    if full_path.startswith(("api", "docs", "redoc", "openapi.json", "health")):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"error": "Frontend not built. Run: cd frontend && npm run build"}
```

Fichier modifié: `src/middleware/tenant.py`
- Ajouter exclusion des routes statiques (`/assets/*`, `/index.html`) du middleware tenant
- Le middleware ne s'applique qu'aux routes `/api/*`

#### 1.4 API Client + Auth Context
```typescript
// src/lib/api.ts
import axios from 'axios';
const api = axios.create({ baseURL: '/api' });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
export default api;
```

```typescript
// src/hooks/useAuth.ts
interface AuthContextType {
  user: User | null;
  tenant: Tenant | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  selectTenant: (tenantId: string) => void;
  loading: boolean;
}
// Context + provider avec persistence localStorage
```

#### 1.5 Routing
```typescript
// App.tsx
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/tenants" element={<ProtectedRoute><TenantSelect /></ProtectedRoute>} />
  <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
    <Route path="/" element={<Dashboard />} />
    <Route path="/services" element={<Services />} />
    <Route path="/documents" element={<Documents />} />
    <Route path="/documents/:id" element={<DocumentDetail />} />
    <Route path="/chat" element={<Chat />} />
    <Route path="/chat/:sessionId" element={<Chat />} />
    <Route path="/settings" element={<Settings />} />
  </Route>
</Routes>
```

**Livrables Phase 1:**
- Projet React fonctionnel avec Vite + Tailwind + Shadcn
- FastAPI sert le build statique (SPA fallback)
- Page Login connectée à `/auth/login`
- Sidebar + Header avec nom du tenant
- Navigation fonctionnelle entre toutes les pages
- Auth context avec JWT persistence

---

### Phase 2 : Pages Principales — Tenant, Services, Dashboard (3-4h)

#### 2.1 Page Login (`src/pages/Login.tsx`)
- Formulaire email + mot de passe
- Bouton "Se connecter" → POST `/api/auth/login`
- Stockage JWT + user info dans localStorage
- Redirection vers `/tenants` si multi-tenant, ou `/` si single-tenant
- Design: centré, logo ProAiRag, fond dégradé sombre

#### 2.2 Page TenantSelect (`src/pages/TenantSelect.tsx`)
- GET `/api/tenants/` (liste les tenants accessibles)
- Grille de cartes avec nom du tenant, nombre de services, nombre de documents
- Bouton "Créer une entreprise" → modal de création tenant
- Clic sur une carte → `selectTenant()` → redirection vers `/`

#### 2.3 Page Dashboard (`src/pages/Dashboard.tsx`)
- Résumé du tenant actif:
  - Nombre de services
  - Nombre de documents totaux
  - Derniers documents uploadés
  - Dernières conversations
- Quick actions: "Ajouter un document", "Nouvelle conversation", "Créer un service"
- Statistiques sous forme de cartes avec icônes Lucide

#### 2.4 Page Services (`src/pages/Services.tsx`)
- GET `/api/departments/` → liste des services du tenant
- Tableau avec colonnes: Nom, Description, Nb documents, Actions
- Bouton "+ Nouveau service" → modal formulaire
  - Champs: nom (required), description (optional)
  - POST `/api/departments/`
- Actions: Éditer (PUT), Supprimer (DELETE avec confirmation)
- Modal de création/édition avec formulaire Shadcn

**Nouveaux endpoints backend nécessaires:**

```python
# src/api/tenants.py — ajouter
@router.get("/tenants/")  # List all tenants (admin)
async def list_tenants():
    ...

# src/api/documents.py — ajouter
@router.get("/documents/")  # List documents (tenant + optional dept filter)
async def list_documents(department_id: Optional[str] = None, limit: int = 50):
    ...

@router.delete("/documents/{doc_id}")  # Delete document + chunks + graph
async def delete_document(doc_id: str):
    ...
```

**Livrables Phase 2:**
- Login fonctionnel avec JWT
- Sélection multi-tenant
- Dashboard avec statistiques
- CRUD complet des services (departments)
- Liste des documents avec filtres

---

### Phase 3 : Upload de Documents (3-4h)

#### 3.1 Backend — Upload de fichiers
Nouveau fichier: `src/services/file_parser.py`
```python
# Support: PDF (pymupdf/pypdf), TXT, DOCX (python-docx), CSV, MD
class FileParser:
    async def parse(self, file: UploadFile, content_type: str) -> str:
        ...
```

Nouveau endpoint: `src/api/documents.py`
```python
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    department_id: Optional[str] = Form(None)
):
    """Upload a file, parse content, chunk, embed, store in graph."""
    content = await file_parser.parse(file, file.content_type)
    # Delegate to existing ingestion_service
    ...
```

Dépendances à ajouter dans `pyproject.toml`:
```
pymupdf>=1.24.0    # PDF parsing
python-docx>=1.1.0 # DOCX parsing
```

#### 3.2 Page Documents (`src/pages/Documents.tsx`)
```
┌─────────────────────────────────────────────────────────────┐
│  Filtres: [Service ▼]  [Type ▼]  [Rechercher...]           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                     │    │
│  │           📄 Glissez vos fichiers ici               │    │
│  │              ou cliquez pour sélectionner           │    │
│  │                                                     │    │
│  │        (PDF, TXT, DOCX, CSV, MD — max 50MB)        │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  Documents uploadés (triés par date)                        │
│  ┌───────────────────────────────────────────────────┐      │
│  │ 📄 Politique RH.pdf          2.3 MB   [RH]  [🗑] │      │
│  │ 📄 Manuel technique.docx     5.1 MB   [IT]  [🗑] │      │
│  │ 📄 Contrat fournisseur.pdf   1.8 MB   [Juridique] [🗑]│  │
│  └───────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

Fonctionnalités:
- Drag & Drop avec `react-dropzone`
- Barre de progression pendant l'upload
- Preview du nom du fichier + taille
- Sélection du service cible avant upload
- Liste des documents avec filtres par service et type
- Suppression avec confirmation (toast)
- Toast de succès/erreur via `sonner`

**Livrables Phase 3:**
- Upload de fichiers (PDF, TXT, DOCX) fonctionnel
- Parsing automatique du contenu
- Ingestion complète (chunking + embedding + graph sync)
- Interface drag & drop avec feedback visuel
- Liste des documents avec filtres et suppression

---

### Phase 4 : Interface Chat (4-5h)

#### 4.1 Backend — Chat avec sessions
Nouveau modèle: `src/models/conversation.py`
```python
class Conversation(Base):
    __tablename__ = "conversations"
    id: str (UUID PK)
    tenant_id: str (FK → tenants)
    department_id: str | null (FK → departments)
    title: str
    created_at: datetime
    updated_at: datetime
```

Nouveau modèle: `src/models/message.py`
```python
class Message(Base):
    __tablename__ = "messages"
    id: str (UUID PK)
    conversation_id: str (FK → conversations)
    role: str  # "user" | "assistant"
    content: str
    sources: str | null  # JSON array of source refs
    graph_context: str | null  # JSON array of graph entities
    created_at: datetime
```

Nouveau router: `src/api/chat.py`
```python
@router.post("/chat/sessions")          # Créer une nouvelle session
@router.get("/chat/sessions/")          # Lister les sessions d'un tenant
@router.get("/chat/sessions/{id}")      # Récupérer une session + messages
@router.delete("/chat/sessions/{id}")   # Supprimer une session
@router.post("/chat/sessions/{id}/send") # Envoyer un message + RAG response
@router.put("/chat/sessions/{id}/title") # Renommer une session
```

Nouveau fichier: `src/services/chat_service.py`
```python
class ChatService:
    async def send_message(self, session_id: str, user_message: str, department_id: str | None):
        # 1. Save user message
        # 2. Call RAG query (vector search scoped to tenant + dept)
        # 3. Save assistant response with sources + graph context
        # 4. Return response
        ...
```

Migration SQL: `migrations/sql/007_create_conversations.sql`
Migration Cypher: (aucune nécessaire pour les conversations — stockées en PostgreSQL)

#### 4.2 Page Chat (`src/pages/Chat.tsx`)
```
┌──────────────────┬──────────────────────────────────────────────────┐
│  SIDEBAR (240px) │                  MAIN CHAT                       │
│                  │                                                  │
│  [+ Nouvelle     │  ┌────────────────────────────────────────────┐  │
│   conversation]  │  │ Conversation: Politique de vacances         │  │
│                  │  └────────────────────────────────────────────┘  │
│  📁 RH           │                                                  │
│    ✓ Vacations   │  ┌────────────────────────────────────────────┐  │
│    · Congés      │  │ 💬 Vous: Combien de jours de vacances?        │  │
│                  │  │                                              │  │
│  📁 IT           │  │ 🤖 Assistant: Les employés ont droit à      │  │
│    · Sécurité    │  │    25 jours de congés payés par an...        │  │
│                  │  │                                              │  │
│  📁 Juridique    │  │    Sources:                                     │  │
│    · Contrats    │  │    📄 Politique RH.pdf (p.3) [0.89]           │  │
│                  │  │    📄 Manuel employés.pdf (p.12) [0.76]      │  │
│                  │  │    🔗 Graph: Company → Policy → Vacations    │  │
│                  │  └────────────────────────────────────────────┘  │
│                  │                                                  │
│                  │  ┌────────────────────────────────────────────┐  │
│                  │  │ [Message...]                    [Envoyer ↵] │  │
│                  │  └────────────────────────────────────────────┘  │
└──────────────────┴──────────────────────────────────────────────────┘
```

Fonctionnalités:
- Sidebar: liste des conversations groupées par service
- Bouton "Nouvelle conversation" (création session)
- Clic sur conversation → chargement de l'historique
- Zone de messages avec auto-scroll
- Input avec support multiline (Shift+Enter)
- Sources affichées en bas de chaque réponse (doc + score + entités graph)
- Filtre par service pour scoper le chat
- Renommer une session (édition du titre)
- Suppression avec confirmation

#### 4.3 Streaming (optionnel, si temps)
- Le endpoint `/chat/sessions/{id}/send` renvoie un SSE stream
- Le frontend affiche le texte caractère par caractère
- Fallback: réponse complète si SSE non supporté

**Livrables Phase 4:**
- Modèle Conversation + Message en base
- CRUD des sessions de chat
- Endpoint de messagerie avec RAG intégré
- Interface chat complète (sidebar + messages + sources)
- Persistance des conversations entre sessions
- Filtrage des résultats par service (department scoping)

---

### Phase 5 : Page Paramètres (2h)

#### 5.1 Page Settings (`src/pages/Settings.tsx`)
```
┌─────────────────────────────────────────────────────────────┐
│                     ⚙️ Paramètres                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─ Paramètres RAG ─────────────────────────────────────┐   │
│  │                                                      │   │
│  │  Taille des chunks (mots)       [  512  ]            │   │
│  │  Chevauchement (mots)           [  64   ]            │   │
│  │  Top K (résultats vectoriels)   [  5    ]            │   │
│  │                                                      │   │
│  │  Modèle d'embedding              [▼]                 │   │
│  │    ○ sentence-transformers/all-MiniLM-L6-v2          │   │
│  │    ○ sentence-transformers/all-mpnet-base-v2         │   │
│  │    ○ openai/text-embedding-3-small                   │   │
│  │                                                      │   │
│  │  Provider LLM                    [▼]                 │   │
│  │    ○ OpenAI (GPT-4o-mini)                                 │   │
│  │    ○ Ollama (llama3.1)                                  │   │
│  │    ○ Fallback (réponse basée sur le contexte seul)    │   │
│  │                                                      │   │
│  │  Clé API OpenAI               [sk-****************]  │   │
│  │  URL Ollama                   [http://localhost:...] │   │
│  │                                                      │   │
│  │                          [Annuler]  [Enregistrer ✓]  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ Informations du système ────────────────────────────┐   │
│  │  Tenant: Acme Corp                                    │   │
│  │  Documents indexés: 142                               │   │
│  │  Chunks en base: 1,284                                │   │
│  │  Entités dans le graph: 567                          │   │
│  │  PostgreSQL: connecté                                 │   │
│  │  Neo4j: connecté                                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2 Backend — Settings
Nouveau endpoint: `src/api/settings.py`
```python
@router.get("/settings/")           # Récupérer les paramètres actuels
@router.put("/settings/")           # Mettre à jour les paramètres RAG
@router.get("/settings/stats")      # Statistiques système (docs, chunks, entités)
```

Nouveau fichier: `src/services/settings_service.py`
- Stockage des paramètres personnalisés par tenant (table `tenant_settings`)
- Ou lecture/écriture dans `.env` (si single-tenant, pas recommandé pour la prod)
- Recommandation: table `tenant_settings` dans PostgreSQL

Migration: `migrations/sql/008_create_tenant_settings.sql`
```sql
CREATE TABLE tenant_settings (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
    chunk_size INTEGER DEFAULT 512,
    chunk_overlap INTEGER DEFAULT 64,
    top_k INTEGER DEFAULT 5,
    embedding_model TEXT,
    llm_provider TEXT DEFAULT 'openai',
    llm_model TEXT,
    openai_api_key TEXT,
    ollama_base_url TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Livrables Phase 5:**
- Page paramètres avec formulaire complet
- Persistance des paramètres par tenant
- Statistiques système affichées
- Application des paramètres aux requêtes RAG

---

### Phase 6 : Polissage UI/UX + Docker (2-3h)

#### 6.1 Design System
- Palette de couleurs: sombre/professionnel (inspiré Linear/Vercel)
- Variables CSS dans `src/index.css`:
  ```css
  :root {
    --bg: #0a0a0f;
    --bg-secondary: #12121a;
    --bg-card: #1a1a2e;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: #6366f1;
    --accent-hover: #818cf8;
    --border: #2a2a3e;
    --success: #10b981;
    --warning: #f59e0b;
    --error: #ef4444;
  }
  ```
- Animations: transitions douces, hover effects
- Responsive: sidebar collapsible sur mobile

#### 6.2 Composants réutilisables
- `ServiceSelector` — dropdown pour sélectionner un service
- `DocumentCard` — carte de document avec icône de type
- `ChatMessage` — message avec sources
- `LoadingSpinner` — animation de chargement
- `EmptyState` — état vide (pas de documents, pas de conversations)

#### 6.3 Docker Compose mis à jour
```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    ...

  neo4j:
    image: neo4j:5
    ...

  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://proairag:proairag@postgres:5432/proairag
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=proairag
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres
      - neo4j

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: builder
    volumes:
      - ./frontend/src:/app/src  # hot reload en dev

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - api
```

#### 6.4 Dockerfile backend
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY src/ src/
COPY frontend/dist/ src/static/
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 6.5 Dockerfile frontend
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

#### 6.6 Nginx config
```nginx
server {
    listen 80;

    # Frontend (servi par FastAPI)
    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket support (si streaming chat)
    location /api/chat/ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Livrables Phase 6:**
- Design cohérent et professionnel
- Composants réutilisables
- Docker Compose fonctionnel (1 command to run everything)
- Build pipeline automatisé
- Responsive design

---

## Dépendances à ajouter

### Backend (pyproject.toml)
```
pymupdf>=1.24.0
python-docx>=1.1.0
python-multipart>=0.0.9
```

### Frontend (package.json — dev)
```
@tanstack/react-router
@tanstack/router-plugin
axios
class-variance-authority
clsx
lucide-react
react-dropzone
sonner
tailwind-merge
```

---

## Résumé des nouveaux fichiers à créer

### Backend (~10 nouveaux fichiers)
```
src/api/chat.py                     # Router chat (sessions + messages)
src/api/settings.py                 # Router paramètres
src/services/chat_service.py        # Logique chat + RAG integration
src/services/file_parser.py         # Parsing PDF/TXT/DOCX
src/services/settings_service.py    # CRUD paramètres tenant
src/models/conversation.py          # Modèle Conversation
src/models/message.py               # Modèle Message
src/models/tenant_settings.py       # Modèle TenantSettings
migrations/sql/007_create_conversations.sql
migrations/sql/008_create_tenant_settings.sql
Dockerfile
nginx.conf
```

### Frontend (~25 fichiers)
```
frontend/ (entier projet Vite + React)
├── Configuration (6 fichiers)
├── src/lib/api.ts
├── src/hooks/useAuth.ts
├── src/types/index.ts
├── src/components/layout/ (3 fichiers)
├── src/components/ui/ (10+ fichiers shadcn)
├── src/components/common/ (5 fichiers réutilisables)
├── src/pages/ (7 fichiers)
└── src/index.css
```

### Modifications de fichiers existants
```
src/main.py                 # +StaticFiles, SPA fallback
src/middleware/tenant.py    # +exclusion routes statiques
src/api/documents.py        # +upload endpoint, +list endpoint
src/api/tenants.py          # +list endpoint
pyproject.toml              # +dépendances PDF/DOCX parsing
docker-compose.yml          # +services frontend + nginx
```

---

## Timeline estimée

| Phase | Description | Temps estimé |
|-------|-------------|-------------|
| 1 | Squelette Frontend + Intégration | 2-3h |
| 2 | Tenant, Services, Dashboard | 3-4h |
| 3 | Upload de Documents | 3-4h |
| 4 | Interface Chat | 4-5h |
| 5 | Page Paramètres | 2h |
| 6 | Polissage UI + Docker | 2-3h |
| **Total** | | **16-21h** |

---

## Ordre d'exécution recommandé

1. Phase 1 (squelette) → validation immédiate (le dashboard s'ouvre)
2. Phase 2 (tenant/services) → CRUD fonctionnel
3. Phase 3 (documents) → upload testable
4. Phase 4 (chat) → cœur du produit
5. Phase 5 (paramètres) → finition
6. Phase 6 (polissage) → production-ready

À chaque phase, on teste avant de passer à la suivante.
