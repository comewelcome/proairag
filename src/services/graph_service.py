import uuid
from src.graph.neo4j_client import get_neo4j_client


class GraphService:
    """Neo4j graph queries for semantic reasoning.

    Neo4j schema:
        Chunk {id, tenant_id, document_id, department_id, chunk_index}
          |
          +--[:MENTIONS]--> Entity {id, tenant_id, name, type, confidence}
                              |
                              +--[:CO_OCCURS_WITH]--> Entity

    PostgreSQL remains the source of truth for all relational data.
    Neo4j is used ONLY for entity relationship reasoning.
    """

    def __init__(self):
        self.neo4j = get_neo4j_client()

    async def get_entity_context(
        self, tenant_id: uuid.UUID, entity_names: list[str], depth: int = 2,
        department_ids: list[uuid.UUID] | None = None,
    ) -> list[dict]:
        """Find entities by name and traverse their relationship graph.

        Department filtering works via the chunk.department_id property
        (no Department nodes in Neo4j).
        """
        if not entity_names:
            return []

        # Build department filter on chunk property
        dept_filter = ""
        dept_params: dict = {}
        if department_ids:
            dept_uuids = [str(d) for d in department_ids]
            dept_filter = "AND c.department_id IN $department_ids"
            dept_params["department_ids"] = dept_uuids

        query = f"""
        MATCH (e:Entity)
        WHERE e.tenant_id = $tenant_id
          AND e.confidence > 0.6
          AND any(name IN $names WHERE toLower(name) = toLower(e.name))
        OPTIONAL MATCH (e)<-[:MENTIONS]-(c:Chunk)
        WHERE c.tenant_id = $tenant_id
          {dept_filter}
        WITH e, collect(distinct c) as chunks
        WHERE size(chunks) > 0
        WITH collect(e) as entities
        UNWIND entities as start_node
        OPTIONAL MATCH path = (start_node)-[*1..{depth}]-(related:Entity)
        WHERE related.tenant_id = $tenant_id
        RETURN
            start_node.name as entity,
            start_node.type as entity_type,
            related.name as related_name,
            related.type as related_type,
            relationships(path) as rels,
            length(path) as distance
        LIMIT 30
        """

        try:
            results = await self.neo4j.execute(query, {
                "tenant_id": str(tenant_id),
                "names": entity_names,
                **dept_params,
            })
        except Exception:
            return []

        context = []
        for row in results:
            rn = row.get("related_name")
            if rn:
                context.append({
                    "entity": row["entity"],
                    "entity_type": row.get("entity_type", ""),
                    "related_name": rn,
                    "related_type": row.get("related_type", ""),
                    "distance": row.get("distance", 1),
                })
        return context

    async def get_knowledge_graph_summary(
        self, tenant_id: uuid.UUID, top_entities: int = 20
    ) -> dict:
        """Return top connected entities for a tenant."""
        result = await self.neo4j.execute(
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
            {"tenant_id": str(tenant_id), "top": top_entities},
        )

        return {
            "top_entities": [
                {"name": r["name"], "type": r["type"], "connections": r["connections"]}
                for r in result
            ]
        }

    async def find_related_concepts(
        self, tenant_id: uuid.UUID, concept: str
    ) -> list[dict]:
        """Find CONCEPT-type entities related to a given entity."""
        result = await self.neo4j.execute(
            """
            MATCH (e:Entity {tenant_id: $tenant_id, name: $concept})
            MATCH (e)-[r]-(related:Entity {tenant_id: $tenant_id})
            WHERE related.type = 'CONCEPT'
            RETURN related.name, related.type, count(r) as weight
            ORDER BY weight DESC
            LIMIT 10
            """,
            {"tenant_id": str(tenant_id), "concept": concept},
        )
        return [{"name": r["related.name"], "weight": r["weight"]} for r in result]

    async def get_documents_for_entity(
        self, tenant_id: uuid.UUID, entity_name: str
    ) -> list[str]:
        """Return document_ids that mention a given entity.

        Useful for the dashboard: 'Which documents talk about X?'.
        Works via Chunk.document_id property — no Document nodes needed.
        """
        result = await self.neo4j.execute(
            """
            MATCH (e:Entity {tenant_id: $tenant_id, name: $entity_name})
            <-[:MENTIONS]-(c:Chunk)
            RETURN DISTINCT c.document_id AS doc_id, count(c) AS chunk_count
            ORDER BY chunk_count DESC
            LIMIT 20
            """,
            {"tenant_id": str(tenant_id), "entity_name": entity_name},
        )
        return [row["doc_id"] for row in result]


def get_graph_service() -> GraphService:
    return GraphService()
