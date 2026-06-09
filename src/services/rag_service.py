import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.vector_service import get_vector_service
from src.services.graph_service import get_graph_service
from src.graph.entity_extractor import get_entity_extractor
from src.schemas.rag import RAGQuery, RAGResponse, RAGSource
from src.config import get_settings


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_service = get_vector_service(db)
        self.graph_service = get_graph_service()
        self.entity_extractor = get_entity_extractor()
        self.settings = get_settings()

    async def query(
        self,
        tenant_id: uuid.UUID,
        rag_query: RAGQuery,
    ) -> RAGResponse:
        vector_results = await self.vector_service.search(
            query=rag_query.query,
            tenant_id=tenant_id,
            top_k=rag_query.top_k,
        )

        graph_context = []
        query_entities = []
        if rag_query.include_graph_context:
            query_entities = self._extract_query_entities(rag_query.query)
            if query_entities:
                graph_context = await self.graph_service.get_entity_context(
                    tenant_id=tenant_id,
                    entity_names=query_entities,
                    depth=rag_query.graph_depth,
                )

        context_parts = self._build_context(vector_results, graph_context)
        answer = await self._generate_answer(rag_query.query, context_parts)

        sources = []
        for vr in vector_results:
            sources.append(
                RAGSource(
                    content=vr["content"][:200] + "...",
                    source_type="vector",
                    similarity=vr.get("similarity"),
                    document_id=str(vr.get("document_id")),
                    document_title=vr.get("document_title"),
                )
            )

        for gc in graph_context:
            sources.append(
                RAGSource(
                    content=f"{gc['entity']} ({gc['entity_type']}) --[{gc['distance']} hops]--> {gc['related_name']} ({gc['related_type']})",
                    source_type="graph",
                )
            )

        return RAGResponse(
            answer=answer,
            sources=sources,
            graph_context=graph_context if graph_context else None,
            query_entities=query_entities if query_entities else None,
        )

    def _extract_query_entities(self, query: str) -> list[str]:
        entities = self.entity_extractor.extract(query)
        return [e.name for e in entities if e.confidence > 0.5]

    def _build_context(
        self, vector_results: list[dict], graph_context: list[dict]
    ) -> str:
        parts = []

        if vector_results:
            parts.append("=== DOCUMENT CONTEXT ===")
            for i, vr in enumerate(vector_results, 1):
                doc_title = vr.get("document_title", "Unknown")
                parts.append(f"[Doc {i}: {doc_title} (similarity: {vr.get('similarity', 0):.3f})]")
                parts.append(vr["content"])
                parts.append("")

        if graph_context:
            parts.append("=== KNOWLEDGE GRAPH CONTEXT ===")
            entities_map: dict[str, list[dict]] = {}
            for gc in graph_context:
                key = f"{gc['entity']} ({gc['entity_type']})"
                if key not in entities_map:
                    entities_map[key] = []
                entities_map[key].append(gc)

            for entity_key, relations in entities_map.items():
                parts.append(f"Entity: {entity_key}")
                for rel in relations:
                    parts.append(
                        f"  -> {rel['related_name']} ({rel['related_type']}) "
                        f"[{rel['distance']} hop(s)]"
                    )
                parts.append("")

        return "\n".join(parts) if parts else "No context found."

    async def _generate_answer(self, query: str, context: str) -> str:
        from src.services.llm_service import get_llm_provider

        system_prompt = """You are a research assistant. Answer questions based
        on the provided context. Cite sources when possible. If the context
        does not contain enough information, clearly state what is missing."""

        prompt = f"Context:\n\n{context}\n\nQuestion: {query}\n\nAnswer:"
        llm = get_llm_provider()
        try:
            return await llm.generate(prompt, system_prompt=system_prompt)
        except Exception:
            return f"[LLM unavailable] Based on the context provided, here is the answer to: {query}"


def get_rag_service(db: AsyncSession) -> RAGService:
    return RAGService(db)
