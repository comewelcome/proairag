from neo4j import AsyncGraphDatabase
from src.config import get_settings


class Neo4jClient:
    def __init__(self):
        settings = get_settings()
        self.driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    async def close(self):
        await self.driver.close()

    async def execute(self, query: str, parameters: dict | None = None):
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            return await result.data()

    async def execute_write(self, query: str, parameters: dict | None = None):
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            return await result.single()

    async def initialize_schema(self):
        constraints = [
            "CREATE CONSTRAINT tenant_unique IF NOT EXISTS FOR (t:Tenant) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT document_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT entity_unique IF NOT EXISTS FOR (e:Entity) REQUIRE (e.id, e.tenant_id) IS UNIQUE",
        ]
        for constraint in constraints:
            await self.execute(constraint)

        indexes = [
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type, e.tenant_id)",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name, e.tenant_id)",
            "CREATE INDEX chunk_id IF NOT EXISTS FOR (c:Chunk) ON (c.id, c.tenant_id)",
        ]
        for index in indexes:
            await self.execute(index)


_neo4j_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client
