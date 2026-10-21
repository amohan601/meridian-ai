"""Text -> vector conversion, used both when indexing documents and when searching.

The SAME model must be used for indexing and for querying, so the model follows APP_MODE:

    local  -> gemini-embedding-001 through the Gemini API (only GOOGLE_API_KEY needed)
    cloud  -> text-embedding-005 through Vertex AI (Google Cloud credentials)

Both produce 768-dimensional vectors. In cloud mode that number is fixed by the
Vector Search index (see .github/workflows/deploy.yml).

LangChain v1 note: `VertexAIEmbeddings` is deprecated. `GoogleGenerativeAIEmbeddings`
covers both the Gemini API and Vertex AI (vertexai=True), so one class serves both modes.
"""

from functools import lru_cache
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config.settings import settings

@lru_cache
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Google GenAI Embedding model"""
    # TODO add cloud settings later
    return GoogleGenerativeAIEmbeddings(
        model=settings.local_embedding_model_name,
        google_api_key=settings.GOOGLE_API_KEY,
        output_dimensionality=settings.embedding_dimensions,
    ) 