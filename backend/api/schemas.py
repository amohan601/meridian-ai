from pydantic import BaseModel

# ============================================================
# RAG  Schemas
# ============================================================

class QueryRequest(BaseModel):
    query: str
    retriever_type: str = "similarity"

class QueryResponse(BaseModel):
    answer: str
    