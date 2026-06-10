import uuid
from src.graph.neo4j_client import get_neo4j_client


class GraphService:
    def __init__(self):
        self.neo4j = get_neo4j_client()

    async def get_entity_context(
        self, tenant_id: uuid.UUID, entity_names: list[str], depth: int = 2
    ) -> list[dict]:
        if not entity_names:
            return []

        # Use WHERE clause instead of IN in node pattern (Cypher limitation)
        query = f"""
        MATCH (t:Tenant {{id: $tenant_id}})
        MATCH (e:Entity {{tenant_id: $tenant_id}})
        WHERE e.name IN $names
        OPTIONAL MATCH path = (e)-[*1..{depth}]-(related)
        WHERE related.tenant_id = $tenant_id
        RETURN
            e.name as entity,
            e.type as entity_type,
            related.name as related_name,
            related.type as related_type,
            relationships(path) as rels,
            length(path) as distance
        LIMIT 50
        """

        try:
            results = await self.neo4j.execute(query, {
                "tenant_id": str(tenant_id),
                "names": entity_names,
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


def get_graph_service() -> GraphService:
    return GraphService()
