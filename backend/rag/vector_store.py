"""The vector database that stores our embeddings. Which one depends on APP_MODE.

    local  -> Chroma, a vector database that saves to a folder on your disk
    cloud  -> Vertex AI Vector Search, Google's managed vector database

Both are LangChain `VectorStore`s, so the rest of the code (ingestion, retrieval)
calls the same methods (`add_documents`, `as_retriever`) and never knows which one it got.
"""

from langchain_core.vectorstores import VectorStore
from exceptions import ConfigurationError
from config.settings import settings
from functools import lru_cache
from rag.embeddings import get_embeddings
from logger import GLOBAL_LOGGER as log

def _local_store() -> VectorStore:
    from langchain_chroma import Chroma  # imported here so cloud images do not need it loaded
    log.info("Using local Chroma vector store", path=settings.chroma_dir)
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir,
    )

def _cloud_store() -> VectorStore:  
    """return a Vertex AI Vector Search vector store, or raise ConfigurationError if not configured."""
    from google.cloud import aiplatform
    from langchain_google_vertexai import VectorSearchVectorStore

    missing = settings.missing_cloud_settings()
    if missing:
        raise ConfigurationError(f"APP_MODE=cloud but these settings are empty: {', '.join(missing)}")
    
    log.info("Using Vertex AI Vector Search", index_id=settings.vector_search_index_id)
    aiplatform.init(project=settings.gcp_project_id, location=settings.gcp_region)
    return VectorSearchVectorStore.from_components(
        project_id=settings.gcp_project_id  ,
        region=settings.gcp_region,
        embedding=get_embeddings(),  # NOTE: singular "embedding", not "embeddings"
        index_id=settings.vector_search_index_id,
        endpoint_id=settings.vector_search_index_endpoint_id,
        gcs_bucket_name=settings.gcs_bucket_name,
        stream_update=True,
    )


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    """Connect on first use, so the API can start (e.g. /api/health) before anything is configured."""
    if settings.is_cloud:
        return _cloud_store()   
    return _local_store()