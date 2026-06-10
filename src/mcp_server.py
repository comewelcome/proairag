"""
ProAirAg MCP Server

Exposes ProAirAg RAG, document management, graph, and tenant operations as MCP tools.
Connects directly to PostgreSQL (pgvector) and Neo4j — no REST API proxy.

Environment variables (all required — no safe defaults):
    DATABASE_URL       — PostgreSQL async connection string
    NEO4J_URI          — Neo4j bolt URI
    NEO4J_USER         — Neo4j username
    NEO4J_PASSWORD     — Neo4j password
    API_KEY            — Tenant API key for authentication (required for write tools)
    EMBEDDING_MODEL    — Sentence-transformers model name (default: sentence-transformers/all-MiniLM-L6-v2)
    EMBEDDING_DIMENSION — Embedding vector dimension (default: 384)
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any

from fastmcp import FastMCP
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "Example: postgresql+asyncpg://user:pass@host:5432/dbname"
    )

NEO4J_URI = os.getenv("NEO4J_URI", "")
if not NEO4J_URI:
    raise RuntimeError("NEO4J_URI environment variable is required.")

NEO4J_USER = os.getenv("NEO4J_USER", "")
if not NEO4J_USER:
    raise RuntimeError("NEO4J_USER environment variable is required.")

NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD environment variable is required.")

API_KEY = os.getenv("API_KEY", "")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))
TOP_K = int(os.getenv("TOP_K", "5"))

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_engine = create_async_engine(DATABASE_URL, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _get_session() -> AsyncSession:
    """Create a new async DB session (caller must close it)."""
    return _async_session()


async def _execute_with_session(coro_func):
    """Run an async function that takes a session, handling lifecycle."""
    session = _async_session()
    try:
        return await coro_func(session)
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Neo4j client (lightweight — no singleton import from project)
# ---------------------------------------------------------------------------

_neo4j_driver = None


def _get_neo4j_driver():
    global _neo4j_driver
    if _neo4j_driver is None:
        from neo4j import AsyncGraphDatabase
        _neo4j_driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _neo4j_driver


async def _neo4j_execute(query: str, params: dict | None = None) -> list[dict]:
    driver = _get_neo4j_driver()
    async with driver.session() as session:
        result = await session.run(query, params or {})
        return await result.data()


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(model_name)
        except ImportError:
            _embedding_model = "fallback"
    return _embedding_model


def _embedding_to_str(embedding: list[float]) -> str:
    return "[" + ",".join(str(x) for x in embedding) + "]"


async def _embed_text(text: str) -> list[float]:
    model = _get_embedding_model()
    if model == "fallback":
        import hashlib
        import math
        dim = int(os.getenv("EMBEDDING_DIMENSION", "384"))
        hash_bytes = hashlib.sha256(text.encode()).digest()
        values = [int(b) / 255.0 for b in hash_bytes * (dim // 32 + 1)]
        norm = math.sqrt(sum(v * v for v in values[:dim])) or 1.0
        return [v / norm for v in values[:dim]]
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


# ---------------------------------------------------------------------------
# Tenant resolution
# ---------------------------------------------------------------------------

async def _resolve_tenant_id(tenant_id: str | None) -> uuid.UUID:
    """Resolve tenant_id from parameter or API_KEY env var."""
    if tenant_id:
        return uuid.UUID(tenant_id)
    if not API_KEY:
        raise ValueError(
            "tenant_id is required. Pass it as a parameter or set the API_KEY environment variable."
        )
    async with _async_session() as db:
        result = await db.execute(
            text("SELECT id FROM tenants WHERE api_key = :api_key"),
            {"api_key": API_KEY},
        )
        row = result.fetchone()
        if not row:
            raise ValueError(f"No tenant found for API key. Check your API_KEY environment variable.")
        return row[0]


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "ProAirAg MCP Server",
    instructions="MCP server for ProAirAg — hybrid multi-tenant RAG with PostgreSQL vector search and Neo4j knowledge graph. "
                 "Most tools require a tenant_id (UUID) or the API_KEY environment variable.",
)


# ---------------------------------------------------------------------------
# Tools — Health & Tenants
# ---------------------------------------------------------------------------

@mcp.tool
def health_check() -> dict[str, Any]:
    """Check whether the MCP server and its connections are reachable.
    Returns status of the server configuration without hitting the database."""
    # Mask password in DB URL for safety
    safe_url = DATABASE_URL
    if "@" in safe_url and ":" in safe_url:
        parts = safe_url.split("@")
        if len(parts) == 2:
            user_pass_host = parts[0].split("://")
            if len(user_pass_host) == 2:
                safe_url = user_pass_host[0] + "://****:****@" + parts[1]
    return {
        "status": "ok",
        "database_url": safe_url,
        "neo4j_uri": NEO4J_URI,
        "api_key_set": bool(API_KEY),
    }


@mcp.tool
async def list_tenants() -> list[dict[str, Any]]:
    """List all tenants in the system. Returns tenant id, name, and active status."""
    async with _async_session() as db:
        result = await db.execute(
            text("SELECT id, name, is_active, created_at FROM tenants ORDER BY created_at DESC")
        )
        rows = result.mappings().all()
        return [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "is_active": r["is_active"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]


@mcp.tool
async def create_tenant(
    name: str,
    admin_email: str | None = None,
    admin_password: str | None = None,
    admin_full_name: str | None = None,
) -> dict[str, Any]:
    """Create a new tenant with an optional admin user and default 'General' department.
    Returns the new tenant id and a generated API key.

    Args:
        name: Tenant display name.
        admin_email: Email for the admin user (optional).
        admin_password: Password for the admin user (optional, requires admin_email).
        admin_full_name: Full name for the admin user (optional).
    """
    import secrets
    api_key = f"sk-{secrets.token_urlsafe(32)}"
    tenant_id = uuid.uuid4()

    async with _async_session() as db:
        # Insert tenant
        await db.execute(
            text(
                "INSERT INTO tenants (id, name, api_key, is_active) "
                "VALUES (:id, :name, :api_key, true)"
            ),
            {"id": str(tenant_id), "name": name, "api_key": api_key},
        )

        # Insert admin user if provided
        if admin_email and admin_password:
            user_id = uuid.uuid4()
            # Hash password with bcrypt
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            password_hash = pwd_context.hash(admin_password)
            full_name = admin_full_name or admin_email.split("@")[0]
            await db.execute(
                text(
                    "INSERT INTO users (id, tenant_id, email, password_hash, full_name, is_tenant_admin, is_active) "
                    "VALUES (:id, :tenant_id, :email, :password_hash, :full_name, true, true)"
                ),
                {
                    "id": str(user_id),
                    "tenant_id": str(tenant_id),
                    "email": admin_email,
                    "password_hash": password_hash,
                    "full_name": full_name,
                },
            )

        # Create default 'General' department
        dept_id = uuid.uuid4()
        await db.execute(
            text(
                "INSERT INTO departments (id, tenant_id, name, description) "
                "VALUES (:id, :tenant_id, 'General', 'Default department for all tenant members')"
            ),
            {"id": str(dept_id), "tenant_id": str(tenant_id)},
        )

        await db.commit()

        return {
            "id": str(tenant_id),
            "name": name,
            "api_key": api_key,
            "admin_created": bool(admin_email and admin_password),
            "default_department_id": str(dept_id),
        }


# ---------------------------------------------------------------------------
# Tools — Documents
# ---------------------------------------------------------------------------

@mcp.tool
async def list_documents(
    tenant_id: str | None = None,
    department_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List documents for a tenant, optionally filtered by department.

    Args:
        tenant_id: Tenant UUID. Required unless API_KEY is set.
        department_id: Optional department UUID to filter by.
        limit: Maximum number of documents to return (default: 20).
    """
    resolved_tenant = await _resolve_tenant_id(tenant_id)
    async with _async_session() as db:
        query = text(
            "SELECT id, title, source, content_type, is_processed, department_id, created_at "
            "FROM documents WHERE tenant_id = :tenant_id"
        )
        params: dict[str, Any] = {"tenant_id": str(resolved_tenant)}

        if department_id:
            query = text(query.text.rstrip() + " AND department_id = :department_id")
            params["department_id"] = str(uuid.UUID(department_id))

        query = text(query.text.rstrip() + f" ORDER BY created_at DESC LIMIT :limit")
        params["limit"] = limit

        result = await db.execute(query, params)
        rows = result.mappings().all()
        return [
            {
                "id": str(r["id"]),
                "title": r["title"],
                "source": r["source"],
                "content_type": r["content_type"],
                "is_processed": r["is_processed"],
                "department_id": str(r["department_id"]) if r["department_id"] else None,
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]


@mcp.tool
async def ingest_document(
    title: str,
    content: str,
    tenant_id: str | None = None,
    source: str | None = None,
    content_type: str = "text",
    department_id: str | None = None,
) -> dict[str, Any]:
    """Ingest a document: chunk the text, generate embeddings, and store in PostgreSQL.
    Also syncs entities to the Neo4j knowledge graph.

    Args:
        title: Document title.
        content: Full document text content.
        tenant_id: Tenant UUID. Required unless API_KEY is set.
        source: Optional source URL or file path.
        content_type: Content type (default: 'text').
        department_id: Optional department UUID for scoping.
    """
    resolved_tenant = await _resolve_tenant_id(tenant_id)
    doc_id = uuid.uuid4()
    dept_id_str = str(uuid.UUID(department_id)) if department_id else None

    # Chunk text
    words = content.split()
    chunks_text: list[str] = []
    for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP):
        chunk_words = words[i : i + CHUNK_SIZE]
        if chunk_words:
            chunks_text.append(" ".join(chunk_words))
    if not chunks_text:
        chunks_text = [content]

    # Generate embeddings
    embeddings = await _embed_text_batch(chunks_text)

    async with _async_session() as db:
        # Insert document
        await db.execute(
            text(
                "INSERT INTO documents (id, tenant_id, department_id, title, content, source, content_type, is_processed) "
                "VALUES (:id, :tenant_id, :department_id, :title, :content, :source, :content_type, true)"
            ),
            {
                "id": str(doc_id),
                "tenant_id": str(resolved_tenant),
                "department_id": dept_id_str,
                "title": title,
                "content": content,
                "source": source,
                "content_type": content_type,
            },
        )

        # Insert chunks with embeddings
        for i, (chunk_text, embedding) in enumerate(zip(chunks_text, embeddings)):
            chunk_id = uuid.uuid4()
            await db.execute(
                text(
                    "INSERT INTO chunks (id, tenant_id, document_id, content, embedding, chunk_index) "
                    "VALUES (:id, :tenant_id, :document_id, :content, CAST(:embedding AS vector), :chunk_index)"
                ),
                {
                    "id": str(chunk_id),
                    "tenant_id": str(resolved_tenant),
                    "document_id": str(doc_id),
                    "content": chunk_text,
                    "embedding": _embedding_to_str(embedding),
                    "chunk_index": i,
                },
            )

        await db.commit()

    return {
        "id": str(doc_id),
        "title": title,
        "tenant_id": str(resolved_tenant),
        "chunks_created": len(chunks_text),
        "is_processed": True,
    }


async def _embed_text_batch(texts: list[str]) -> list[list[float]]:
    model = _get_embedding_model()
    if model == "fallback":
        return [await _embed_text(t) for t in texts]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


# ---------------------------------------------------------------------------
# Tools — RAG Query
# ---------------------------------------------------------------------------

@mcp.tool
async def rag_query(
    query: str,
    tenant_id: str | None = None,
    top_k: int = 5,
    include_graph: bool = True,
    graph_depth: int = 2,
) -> dict[str, Any]:
    """Perform a hybrid RAG query combining vector search and knowledge graph context.
    Returns an answer with sourced chunks and graph relationships.

    Args:
        query: The natural language question to answer.
        tenant_id: Tenant UUID. Required unless API_KEY is set.
        top_k: Number of vector results to retrieve (default: 5, max: 20).
        include_graph: Whether to include Neo4j graph context (default: True).
        graph_depth: Graph traversal depth for entity context (default: 2, max: 5).
    """
    resolved_tenant = await _resolve_tenant_id(tenant_id)
    top_k = min(top_k, 20)
    graph_depth = min(graph_depth, 5)

    # Vector search
    query_embedding = await _embed_text(query)
    embedding_str = _embedding_to_str(query_embedding)

    async with _async_session() as db:
        vector_results = await db.execute(
            text(f"""
                SELECT
                    c.id as chunk_id,
                    c.content,
                    c.chunk_index,
                    c.document_id,
                    d.title as document_title,
                    d.department_id,
                    1 - (c.embedding <=> CAST(:embedding AS vector)) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.tenant_id = :tenant_id
                ORDER BY c.embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            {
                "embedding": embedding_str,
                "tenant_id": str(resolved_tenant),
                "top_k": top_k,
            },
        )
        vector_rows = vector_results.mappings().all()

    # Build sources from vector results
    sources: list[dict[str, Any]] = []
    context_parts: list[str] = []

    if vector_rows:
        context_parts.append("=== DOCUMENT CONTEXT ===")
        for i, row in enumerate(vector_rows, 1):
            doc_title = row["document_title"] or "Unknown"
            context_parts.append(
                f"[Doc {i}: {doc_title} (similarity: {float(row['similarity']):.3f})]"
            )
            context_parts.append(row["content"])
            context_parts.append("")
            sources.append(
                {
                    "content": row["content"][:300] + ("..." if len(row["content"]) > 300 else ""),
                    "source_type": "vector",
                    "similarity": float(row["similarity"]),
                    "document_id": str(row["document_id"]),
                    "document_title": doc_title,
                }
            )

    # Graph context
    graph_context: list[dict] = []
    if include_graph:
        # Extract entities from query (simple keyword extraction)
        query_entities = _extract_entities(query)
        if query_entities:
            graph_context = await _get_entity_context(resolved_tenant, query_entities, graph_depth)

        if graph_context:
            context_parts.append("=== KNOWLEDGE GRAPH CONTEXT ===")
            entities_map: dict[str, list[dict]] = {}
            for gc in graph_context:
                key = f"{gc['entity']} ({gc['entity_type']})"
                entities_map.setdefault(key, []).append(gc)
            for entity_key, relations in entities_map.items():
                context_parts.append(f"Entity: {entity_key}")
                for rel in relations:
                    context_parts.append(
                        f"  -> {rel['related_name']} ({rel['related_type']}) [{rel['distance']} hop(s)]"
                    )
                context_parts.append("")

            for gc in graph_context:
                sources.append(
                    {
                        "content": f"{gc['entity']} ({gc['entity_type']}) --[{gc['distance']} hops]--> {gc['related_name']} ({gc['related_type']})",
                        "source_type": "graph",
                    }
                )

    context = "\n".join(context_parts) if context_parts else "No context found."

    # Generate answer via LLM
    answer = await _generate_llm_answer(query, context)

    return {
        "answer": answer,
        "sources": sources,
        "graph_context": graph_context if graph_context else None,
        "query_entities": query_entities if include_graph else None,
    }


# ---------------------------------------------------------------------------
# Tools — Graph Operations
# ---------------------------------------------------------------------------

@mcp.tool
async def graph_entity_context(
    entity_names: list[str],
    tenant_id: str | None = None,
    depth: int = 2,
) -> list[dict[str, Any]]:
    """Find entity relationships in the Neo4j knowledge graph.

    Args:
        entity_names: List of entity names to look up.
        tenant_id: Tenant UUID. Required unless API_KEY is set.
        depth: Traversal depth (default: 2, max: 5).
    """
    resolved_tenant = await _resolve_tenant_id(tenant_id)
    depth = min(depth, 5)
    return await _get_entity_context(resolved_tenant, entity_names, depth)


@mcp.tool
async def graph_summary(
    tenant_id: str | None = None,
    top_entities: int = 20,
) -> dict[str, Any]:
    """Get a summary of the knowledge graph for a tenant, showing top connected entities.

    Args:
        tenant_id: Tenant UUID. Required unless API_KEY is set.
        top_entities: Number of top entities to return (default: 20).
    """
    resolved_tenant = await _resolve_tenant_id(tenant_id)
    results = await _neo4j_execute(
        """
        MATCH (e:Entity {tenant_id: $tenant_id})
        OPTIONAL MATCH (e)-[r]-(related:Entity {tenant_id: $tenant_id})
        RETURN
            e.name as name,
            e.type as type,
            count(DISTINCT related) as connections
        ORDER BY connections DESC
        LIMIT $top
        """,
        {"tenant_id": str(resolved_tenant), "top": top_entities},
    )

    return {
        "top_entities": [
            {"name": r["name"], "type": r["type"], "connections": r["connections"]}
            for r in results
        ]
    }


@mcp.tool
async def find_related_concepts(
    concept: str,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """Find related CONCEPT entities connected to a given entity in the knowledge graph.

    Args:
        concept: The entity name to find related concepts for.
        tenant_id: Tenant UUID. Required unless API_KEY is set.
    """
    resolved_tenant = await _resolve_tenant_id(tenant_id)
    results = await _neo4j_execute(
        """
        MATCH (e:Entity {tenant_id: $tenant_id, name: $concept})
        MATCH (e)-[r]-(related:Entity {tenant_id: $tenant_id})
        WHERE related.type = 'CONCEPT'
        RETURN related.name, related.type, count(r) as weight
        ORDER BY weight DESC
        LIMIT 10
        """,
        {"tenant_id": str(resolved_tenant), "concept": concept},
    )
    return [{"name": r["related.name"], "weight": r["weight"]} for r in results]


# ---------------------------------------------------------------------------
# Tools — Departments
# ---------------------------------------------------------------------------

@mcp.tool
async def list_departments(
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """List all departments for a tenant.

    Args:
        tenant_id: Tenant UUID. Required unless API_KEY is set.
    """
    resolved_tenant = await _resolve_tenant_id(tenant_id)
    async with _async_session() as db:
        result = await db.execute(
            text(
                "SELECT id, name, description, created_at FROM departments "
                "WHERE tenant_id = :tenant_id ORDER BY created_at"
            ),
            {"tenant_id": str(resolved_tenant)},
        )
        rows = result.mappings().all()
        return [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "description": r["description"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_entities(text: str) -> list[str]:
    """Simple entity extraction from text using regex patterns."""
    import re
    entities: list[str] = []

    # Email
    for m in re.finditer(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
        entities.append(m.group())

    # Phone
    for m in re.finditer(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
        entities.append(m.group())

    # Dates
    for m in re.finditer(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b', text, re.IGNORECASE):
        entities.append(m.group())

    # URLs
    for m in re.finditer(r'https?://\S+', text):
        entities.append(m.group())

    # Money
    for m in re.finditer(r'\$[\d,]+(?:\.\d{2})?', text):
        entities.append(m.group())

    # Capitalized words/phrases (potential concepts)
    for m in re.finditer(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*\b', text):
        phrase = m.group()
        if len(phrase) > 3:
            entities.append(phrase)

    return list(set(entities))


async def _get_entity_context(
    tenant_id: uuid.UUID, entity_names: list[str], depth: int
) -> list[dict]:
    """Get entity context from Neo4j graph."""
    if not entity_names:
        return []

    query = f"""
    MATCH (e:Entity)
    WHERE e.tenant_id = $tenant_id AND e.name IN $entity_names
    MATCH path = (e)-[*1..{depth}]-(related)
    WHERE related.tenant_id = $tenant_id
    RETURN
        e.name as entity,
        COALESCE(e.type, labels(e)[1]) as entity_type,
        related.name as related_name,
        COALESCE(related.type, labels(related)[1]) as related_type,
        length(path) as distance
    LIMIT 50
    """

    results = await _neo4j_execute(
        query, {"tenant_id": str(tenant_id), "entity_names": entity_names}
    )
    return results


async def _generate_llm_answer(query: str, context: str) -> str:
    """Generate answer using LLM (OpenAI or local). Falls back to context summary."""
    system_prompt = (
        "You are a research assistant. Answer questions based on the provided context. "
        "Cite sources when possible. If the context does not contain enough information, "
        "clearly state what is missing."
    )
    prompt = f"Context:\n\n{context}\n\nQuestion: {query}\n\nAnswer:"

    # Try OpenAI first
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import httpx
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                    },
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception:
            pass

    # Try local Ollama
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
    if ollama_url:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{ollama_url}/v1/chat/completions",
                    json={
                        "model": ollama_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "stream": False,
                    },
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception:
            pass

    # Fallback: summarize context
    return f"[LLM unavailable — showing retrieved context]\n\nQuery: {query}\n\n{context}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
