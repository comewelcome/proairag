# ProAirAg MCP Server

MCP (Model Context Protocol) server for ProAirAg — hybrid multi-tenant RAG system.
Exposes RAG queries, document management, graph operations, and tenant management as MCP tools.

## Quick Start

```bash
# Set environment variables (use your own credentials)
export DATABASE_URL="postgresql+asyncpg://YOUR_USER:YOUR_PASS@localhost:5432/proairag"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="YOUR_NEO4J_PASSWORD"
export API_KEY="sk-your-tenant-api-key"  # Optional — used for tenant resolution

# Run the server (stdio transport — default)
python src/mcp_server.py

# Or use the FastMCP CLI
fastmcp run src/mcp_server.py:mcp
```

## Tools

### Health & Tenants

| Tool | Description |
|------|-------------|
| `health_check()` | Check server status and connection configuration |
| `list_tenants()` | List all tenants (id, name, active status) |
| `create_tenant(name, admin_email?, admin_password?, admin_full_name?)` | Create a new tenant with optional admin user |

### Documents

| Tool | Description |
|------|-------------|
| `list_documents(tenant_id?, department_id?, limit=20)` | List documents for a tenant |
| `ingest_document(title, content, tenant_id?, source?, content_type?, department_id?)` | Ingest a document with chunking + embedding |

### RAG Query

| Tool | Description |
|------|-------------|
| `rag_query(query, tenant_id?, top_k=5, include_graph=True, graph_depth=2)` | Hybrid RAG query (vector + graph + LLM) |

### Graph Operations

| Tool | Description |
|------|-------------|
| `graph_entity_context(entity_names, tenant_id?, depth=2)` | Find entity relationships in Neo4j |
| `graph_summary(tenant_id?, top_entities=20)` | Top connected entities in knowledge graph |
| `find_related_concepts(concept, tenant_id?)` | Find related CONCEPT entities |

### Departments

| Tool | Description |
|------|-------------|
| `list_departments(tenant_id?)` | List departments for a tenant |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(required)* | PostgreSQL connection string |
| `NEO4J_URI` | *(required)* | Neo4j bolt URI |
| `NEO4J_USER` | *(required)* | Neo4j username |
| `NEO4J_PASSWORD` | *(required)* | Neo4j password |
| `API_KEY` | (empty) | Tenant API key for auth (optional — use tenant_id param instead) |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `EMBEDDING_DIMENSION` | `384` | Embedding vector dimension |
| `CHUNK_SIZE` | `512` | Document chunk size in words |
| `CHUNK_OVERLAP` | `64` | Chunk overlap in words |
| `TOP_K` | `5` | Default number of vector results |
| `OPENAI_API_KEY` | (empty) | OpenAI API key for LLM answers |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama base URL (fallback LLM) |
| `OLLAMA_MODEL` | `llama3.1` | Ollama model to use |

## Installing into MCP Clients

### Claude Code
```bash
fastmcp install claude-code src/mcp_server.py
```

### Claude Desktop
```bash
fastmcp install claude-desktop src/mcp_server.py
```

### Cursor
```bash
fastmcp install cursor src/mcp_server.py
```

### HTTP Transport (for any MCP client)
```bash
fastmcp run src/mcp_server.py:mcp --transport http --host 127.0.0.1 --port 9000
```

Then point your MCP client to `http://127.0.0.1:9000/mcp`.

## Testing

```bash
# Inspect the server
fastmcp inspect src/mcp_server.py:mcp

# List all tools
fastmcp list src/mcp_server.py

# Test health check
fastmcp call src/mcp_server.py health_check --json

# Test tenant listing
fastmcp call src/mcp_server.py list_tenants --json

# Test RAG query (with API_KEY set)
fastmcp call src/mcp_server.py rag_query query="What is RAG?" --json
```
