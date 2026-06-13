import uuid
from src.graph.neo4j_client import get_neo4j_client
from src.graph.entity_extractor import EntityExtractor, Entity, get_entity_extractor


class GraphSyncService:
    def __init__(self):
        self.neo4j = get_neo4j_client()
        self.extractor = get_entity_extractor()

    async def sync_document(
        self, tenant_id: uuid.UUID, doc_id: uuid.UUID, chunks: list[dict],
        department_id: uuid.UUID | None = None,
    ):
        # Create/merge tenant
        await self.neo4j.execute(
            "MERGE (t:Tenant {id: $tenant_id}) ON CREATE SET t.created_at = datetime()",
            {"tenant_id": str(tenant_id)},
        )

        # Create/merge document
        await self.neo4j.execute(
            """
            MERGE (t:Tenant {id: $tenant_id})
            MERGE (d:Document {id: $doc_id})
            MERGE (t)-[:OWNS]->(d)
            """,
            {"tenant_id": str(tenant_id), "doc_id": str(doc_id)},
        )

        # Create/merge department and link to document
        if department_id:
            await self.neo4j.execute(
                """
                MERGE (t:Tenant {id: $tenant_id})
                MERGE (dep:Department {id: $department_id, tenant_id: $tenant_id})
                ON CREATE SET dep.created_at = datetime()
                MERGE (d:Document {id: $doc_id})
                SET d.department_id = $department_id
                MERGE (d)-[:BELONGS_TO]->(dep)
                MERGE (dep)-[:IN_TENANT]->(t)
                """,
                {
                    "tenant_id": str(tenant_id),
                    "department_id": str(department_id),
                    "doc_id": str(doc_id),
                },
            )

        all_entities_by_name: dict[str, Entity] = {}

        for chunk_data in chunks:
            chunk_id = chunk_data["id"]
            content = chunk_data["content"]

            await self.neo4j.execute(
                """
                MERGE (d:Document {id: $doc_id})
                MERGE (c:Chunk {id: $chunk_id})
                SET c.tenant_id = $tenant_id,
                    c.content = $content,
                    c.chunk_index = $chunk_index
                MERGE (d)-[:HAS_CHUNK]->(c)
                """,
                {
                    "tenant_id": str(tenant_id),
                    "doc_id": str(doc_id),
                    "chunk_id": str(chunk_id),
                    "content": content,
                    "chunk_index": chunk_data.get("chunk_index", 0),
                },
            )

            entities = self.extractor.extract(content)

            for entity in entities:
                await self.neo4j.execute(
                    """
                    MERGE (e:Entity {id: $entity_id, tenant_id: $tenant_id})
                    ON CREATE SET e.name = $name,
                                  e.type = $type,
                                  e.confidence = $confidence
                    MERGE (c:Chunk {id: $chunk_id})
                    MERGE (c)-[:MENTIONS {confidence: $confidence}]->(e)
                    MERGE (t:Tenant {id: $tenant_id})
                    MERGE (e)-[:BELONGS_TO]->(t)
                    """,
                    {
                        "tenant_id": str(tenant_id),
                        "entity_id": entity.id,
                        "name": entity.name,
                        "type": entity.type,
                        "confidence": entity.confidence,
                        "chunk_id": str(chunk_id),
                    },
                )
                all_entities_by_name[entity.name] = entity

        await self._create_cooccurrence_relations(tenant_id, all_entities_by_name)

    async def _create_cooccurrence_relations(
        self, tenant_id: uuid.UUID, entities: dict[str, Entity]
    ):
        entity_list = list(entities.values())
        # Build all cross-type pairs in a single batch query
        pairs = []
        for i, e1 in enumerate(entity_list):
            for e2 in entity_list[i + 1 :]:
                if e1.type != e2.type:
                    pairs.append((e1.id, e2.id, f"{e1.type}_TO_{e2.type}"))

        if not pairs:
            return

        # Single Cypher call with UNWIND for all co-occurrence relations
        await self.neo4j.execute(
            """
            UNWIND $pairs AS pair
            MATCH (a:Entity {id: pair.id1, tenant_id: $tenant_id}),
                  (b:Entity {id: pair.id2, tenant_id: $tenant_id})
            MERGE (a)-[r:CO_OCCURS_WITH {type: pair.rel_type}]->(b)
            ON CREATE SET r.confidence = 0.5
            """,
            {
                "tenant_id": str(tenant_id),
                "pairs": pairs,
            },
        )


def get_graph_sync_service() -> GraphSyncService:
    return GraphSyncService()
