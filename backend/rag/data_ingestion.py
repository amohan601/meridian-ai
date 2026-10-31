"""Getting documents INTO the vector database.

    PDF file -> pages -> chunks (~1000 characters) -> embeddings -> vector store

Two entry points share the same steps:
  * ingest_pdf()          - one PDF on disk (used by the upload endpoint)
  * ingest_stored_pdfs()  - every PDF in the document store
                            (local: .meridian/uploads/, cloud: the GCS bucket)
"""

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import hashlib
from rag.vector_store import get_vector_store
from rag import document_store
from logger import GLOBAL_LOGGER as log
from exceptions import IngestionError


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100  # neighbouring chunks share 100 characters so sentences are not cut off


def split_into_chunks(pages: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return splitter.split_documents(pages)

#-----------------
# Generate unique chunk id for same chunk and same index 
#------------------
def _generate_chunk_id(chunk: Document, index: int) -> str:
    """Stable ID per chunk: re-indexing the same file overwrites instead of duplicating."""
    text = chunk.page_content
    return hashlib.sha256(f"{index}:{text}".encode()).hexdigest()


def ingest_pdf(local_path: str, filename: str) -> dict:
    """
    Load one PDF, chunk it and store it. Returns {"pages", n, "chunks": n}
    `source` is saved in each chunk's metadata so answers can be traced back to a file.
    """
    try:

        log.info(f'initiating page creation for {filename}')
        pages = PyPDFLoader(local_path).load()
    except Exception as exc:  # pypdf raises many different error types
        #TODO
        log.error(f"Exception occured in PyPDFLoader {str(exc)}")
        raise IngestionError(f"Could not read PDF '{filename}': {exc}") from exc


    for page in pages:
        page.metadata["source"] = filename

    log.info(f'initiating chunk creation for {filename}')
    chunks = split_into_chunks(pages)

    if chunks:
        log.info(f"Embedding chunks and adding to vector store {filename} length of chunks: {len(chunks)}")
        # generate unique chunk ids for each chunk
        ids = [_generate_chunk_id(chunk, index) for index, chunk in enumerate(chunks)]
        # perform vector store operation that will embed the chunks and save them into vector store
        log.info(f"Embedding chunks and adding to vector store {filename} length of chunks: {len(chunks)}")
        
        collection = get_vector_store()._collection
        result = collection.get(ids=ids)

        existing_ids = set(result["ids"])

        for chunk_id in ids:
            if chunk_id in existing_ids:
                print(f"Chunk_id={chunk_id} exists")
            else:
                print(f"Chunk_id={chunk_id} does not exist")

        get_vector_store().add_documents(chunks, ids=ids)


    return {"pages": len(pages), "chunks": len(chunks)}

def ingest_stored_pdfs() -> dict:
    """Index every PDF already in the document store."""
    log.info("Indexing stored documents")
    totals = {"files": 0, "pages": 0, "chunks": 0}

    with document_store.pdfs() as files:
        for local_path, source in files:
            result = ingest_pdf(local_path, source)
            log.info("Ingested stored PDF")
            totals["files"] += 1
            totals["pages"] += result["pages"]
            totals["chunks"] += result["chunks"]

    if totals["files"] == 0:
        print("No PDF documents found in the document store")
    log.info("Ingestion complete")
    return totals