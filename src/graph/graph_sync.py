import uuid
from src.graph.neo4j_client import get_neo4j_client
from src.graph.entity_extractor import EntityExtractor, Entity, get_entity_extractor

# Maximum entities per chunk to create co-occurrence relations for (keeps graph lean)
MAX_CO_OCCURRENCE_ENTITIES = 20


class GraphSyncService:
    """Sync document chunks and extracted entities to Neo4j.

    Neo4j stores ONLY entity nodes and their relationships — no content duplication.
    Chunk nodes carry tenant_id, document_id, and department_id as properties
    (references back to PostgreSQL, the source of truth).
    """

    def __init__(self):
        self.neo4j = get_neo4j_client()
        self.extractor = get_entity_extractor()

    async def sync_document(
        self, tenant_id: uuid.UUID, doc_id: uuid.UUID, chunks: list[dict],
        department_id: uuid.UUID | None = None,
    ):
        dept_id_str = str(department_id) if department_id else None

        # Process all chunks in a single batch MERGE
        chunk_records = []
        all_entities: dict[str, Entity] = {}

        for chunk_data in chunks:
            chunk_id = chunk_data["id"]
            content = chunk_data["content"]
            chunk_index = chunk_data.get("chunk_index", 0)

            chunk_records.append({
                "chunk_id": str(chunk_id),
                "tenant_id": str(tenant_id),
                "document_id": str(doc_id),
                "department_id": dept_id_str,
                "chunk_index": chunk_index,
            })

            # Extract entities and track them globally
            for entity in self.extractor.extract(content):
                eid = entity.id
                if eid not in all_entities:
                    all_entities[eid] = entity
                # Record which chunk mentions which entity
                if not hasattr(entity, "_chunk_ids"):
                    entity._chunk_ids = []  # type: ignore
                    entity._chunk_ids.append(str(chunk_id))  # type: ignore

        # Batch 1: Create Chunk nodes (minimal — no content stored)
        if chunk_records:
            await self.neo4j.execute(
                """
                UNWIND $records AS rec
                MERGE (c:Chunk {id: rec.chunk_id})
                SET c.tenant_id = rec.tenant_id,
                    c.document_id = rec.document_id,
                    c.department_id = rec.department_id,
                    c.chunk_index = rec.chunk_index
                """,
                {"records": chunk_records},
            )

        # Batch 2: Create Entity nodes + MENTIONS relationships
        # Group entities by their chunk_ids for efficient MERGE
        entity_chunk_pairs = []
        for entity in all_entities.values():
            for chunk_id in getattr(entity, "_chunk_ids", []):  # type: ignore
                entity_chunk_pairs.append({
                    "chunk_id": chunk_id,
                    "entity_id": entity.id,
                    "tenant_id": str(tenant_id),
                    "name": entity.name,
                    "type": entity.type,
                    "confidence": entity.confidence,
                })

        if entity_chunk_pairs:
            await self.neo4j.execute(
                """
                UNWIND $pairs AS p
                MERGE (c:Chunk {id: p.chunk_id})
                MERGE (e:Entity {id: p.entity_id, tenant_id: p.tenant_id})
                ON CREATE SET e.name = p.name,
                              e.type = p.type,
                              e.confidence = p.confidence
                MERGE (c)-[:MENTIONS]->(e)
                """,
                {"pairs": entity_chunk_pairs},
            )

        # Batch 3: Co-occurrence relations (cross-type, limited to top entities)
        await self._create_cooccurrence_relations(
            str(tenant_id), list(all_entities.values())
        )

    async def delete_document(
        self, tenant_id: uuid.UUID, doc_id: uuid.UUID,
    ):
        """Remove all Chunk nodes and orphaned Entities for a document.

        Called when a document is deleted from PostgreSQL to keep Neo4j in sync.
        """
        # Delete all chunks belonging to this document
        await self.neo4j.execute(
            """
            MATCH (c:Chunk {tenant_id: $tenant_id, document_id: $doc_id})
            DETACH DELETE c
            """,
            {"tenant_id": str(tenant_id), "doc_id": str(doc_id)},
        )

        # Clean up entities no longer mentioned by any chunk in this tenant
        await self.neo4j.execute(
            """
            MATCH (e:Entity {tenant_id: $tenant_id})
            WHERE NOT EXISTS { (e)<-[:MENTIONS]-(:Chunk) }
            DETACH DELETE e
            """,
            {"tenant_id": str(tenant_id)},
        )

    async def _create_cooccurrence_relations(
        self, tenant_id: str, entities: list[Entity]
    ):
        """Create CO_OCCURS_WITH relations between cross-type entities.

        Limited to top-K entities by confidence to avoid O(N^2) explosion.
        Uses UNWIND for a single batched Cypher call.
        """
        # Sort by confidence, take top N only
        top_entities = sorted(
            entities, key=lambda e: e.confidence, reverse=True
        )[:MAX_CO_OCCURRENCE_ENTITIES]

        pairs = []
        for i, e1 in enumerate(top_entities):
            for e2 in top_entities[i + 1 :]:
                if e1.type != e2.type:
                    pairs.append((e1.id, e2.id, f"{e1.type}_TO_{e2.type}"))

        if not pairs:
            return

        await self.neo4j.execute(
            """
            UNWIND $pairs AS pair
            MATCH (a:Entity {id: pair.id1, tenant_id: $tenant_id}),
                  (b:Entity {id: pair.id2, tenant_id: $tenant_id})
            MERGE (a)-[r:CO_OCCURS_WITH {type: pair.rel_type}]->(b)
            ON CREATE SET r.count = 1
            ON MATCH SET r.count = r.count + 1
            """,
            {"tenant_id": tenant_id, "pairs": pairs},
        )


def get_graph_sync_service() -> GraphSyncService:
    return GraphSyncService()
