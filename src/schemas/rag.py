from pydantic import BaseModel, Field


class RAGQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096)
    top_k: int = Field(default=5, ge=1, le=20)
    include_graph_context: bool = Field(default=True)
    graph_depth: int = Field(default=2, ge=1, le=5)


class RAGSource(BaseModel):
    content: str
    source_type: str  # "vector" | "graph"
    similarity: float | None = None
    document_id: str | None = None
    document_title: str | None = None


class RAGResponse(BaseModel):
    answer: str
    sources: list[RAGSource]
    graph_context: list[dict] | None = None
    query_entities: list[str] | None = None
