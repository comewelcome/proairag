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
        user_id: uuid.UUID | None = None,
        is_tenant_admin: bool = False,
        conversation_history: list[dict] | None = None,
    ) -> RAGResponse:
        # Resolve user departments for filtering
        department_ids: list[uuid.UUID] | None = None
        if user_id and not is_tenant_admin:
            from src.services.department_service import get_department_service
            dept_service = get_department_service(self.db)
            department_ids = await dept_service.get_user_department_ids(user_id)

        vector_results = await self.vector_service.search(
            query=rag_query.query,
            tenant_id=tenant_id,
            top_k=rag_query.top_k,
            department_ids=department_ids,
            is_tenant_admin=is_tenant_admin,
        )

        graph_context = []
        query_entities = []
        if rag_query.include_graph_context:
            query_entities = self._extract_query_entities(rag_query.query)
            if query_entities:
                import asyncio
                try:
                    graph_context = await asyncio.wait_for(
                        self.graph_service.get_entity_context(
                            tenant_id=tenant_id,
                            entity_names=query_entities,
                            depth=rag_query.graph_depth,
                            department_ids=department_ids,
                        ),
                        timeout=10,
                    )
                except asyncio.TimeoutError:
                    graph_context = []
                except Exception:
                    graph_context = []

        context_parts = self._build_context(vector_results, graph_context)
        answer = await self._generate_answer(rag_query.query, context_parts, conversation_history)

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

    async def _generate_answer(self, query: str, context: str, conversation_history: list[dict] | None = None) -> str:
        from src.services.llm_service import get_llm_provider

        system_prompt = (
            "You are a research assistant. Answer questions based on the provided context. "
            "Provide a direct, clear, and concise answer. "
            "IMPORTANT: DO NOT show your reasoning, thinking process, or analysis steps. "
            "DO NOT use numbered lists like '1. Analyze the Request' or '2. Scan Context'. "
            "DO NOT use bold headers like **Analyze the Request:** or **Scan Context for...**. "
            "DO NOT structure your response as a reasoning chain. "
            "DO NOT include any meta-commentary about how you are thinking. "
            "Just provide the final answer directly. Cite sources when possible. "
            "If the context does not contain enough information, clearly state what is missing."
        )

        # Build prompt with conversation history for multi-turn context
        history_text = ""
        if conversation_history:
            history_parts = []
            for msg in conversation_history:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                history_parts.append(f"{role_label}: {msg['content']}")
            history_text = "\n\n=== CONVERSATION HISTORY ===\n" + "\n".join(history_parts)

        prompt = f"Context:\n\n{context}\n\n{history_text}\n\nQuestion: {query}\n\nAnswer:"
        llm = get_llm_provider()
        try:
            raw_answer = await llm.generate(prompt, system_prompt=system_prompt)
            # Strip thinking/reasoning tags that some models output
            return self._clean_thinking_tags(raw_answer)
        except Exception:
            return f"[LLM unavailable] Based on the context provided, here is the answer to: {query}"

    @staticmethod
    def _clean_thinking_tags(text: str) -> str:
        """Remove thinking/reasoning tags and extract the final answer from LLM output.

        Handles structured reasoning blocks like:
        1. **Analyze the Request:** ...
        2. **Scan Context:** ...
        3. **Final Answer:** ...

        Extracts the content from the "Final Answer" or "Answer" block,
        or falls back to the last block if no explicit answer block exists.
        """
        import re

        # Remove <think>...</think> and <thinking>...</thinking> tags
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Check if text has structured reasoning blocks
        header_pattern = re.compile(r"^(\d+)\.\s+\*\*(.+):\*\*")
        lines = text.split("\n")

        blocks = []
        current_header = None
        current_content = []

        for line in lines:
            header_match = header_pattern.match(line)
            if header_match:
                if current_header is not None:
                    blocks.append((current_header, "\n".join(current_content)))
                current_header = (header_match.group(1), header_match.group(2))
                current_content = []
            elif current_header is not None:
                current_content.append(line)

        if current_header is not None:
            blocks.append((current_header, "\n".join(current_content)))

        if not blocks:
            # No structured blocks found, return cleaned text as-is
            cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
            return cleaned or "I don't have enough context to answer this question."

        # Extract answer with priority:
        # 1. Look for "Final Answer" block
        # 2. Look for "Answer" block
        # 3. Use the last block
        answer = None
        for _num, (header, content) in enumerate(blocks):
            header_lower = header[1].lower().strip()
            if header_lower == "final answer":
                answer = content.strip()
                break

        if answer is None:
            for _num, (header, content) in enumerate(blocks):
                header_lower = header[1].lower().strip()
                if header_lower == "answer" or header_lower.startswith("answer:"):
                    answer = content.strip()
                    break

        if answer is None:
            answer = blocks[-1][1].strip()

        answer = re.sub(r"\n{3,}", "\n\n", answer).strip()
        return answer or "I don't have enough context to answer this question."

def get_rag_service(db: AsyncSession) -> RAGService:
    return RAGService(db)
