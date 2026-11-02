from rag.vector_store import get_vector_store


def test_get_vector_store_finds_indexed_documents(indexed_documents):
    docs = get_vector_store().similarity_search("procurement policy approval thresholds", k=1)

    assert len(docs) == 1
    assert docs[0].page_content.strip()
