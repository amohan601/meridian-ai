from config.settings import settings
from rag.embeddings import get_embeddings


def test_get_embeddings_returns_configured_dimensions():
    vector = get_embeddings().embed_query("industrial servo motor")

    assert len(vector) == settings.embedding_dimensions
