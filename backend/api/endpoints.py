
from fastapi import APIRouter, UploadFile, File,HTTPException
import os
import shutil
from config.settings import settings   
from fastapi.concurrency import run_in_threadpool
from rag import document_store
from rag.retrieval import ask_question
from rag.data_ingestion import ingest_pdf
import tempfile
from api.schemas import  QueryRequest, QueryResponse, AuditRequest, AuditResponse
from agent.agents import ProcurementSupervisor
from functools import lru_cache


health_router = APIRouter(prefix="/api", tags=["Health"])
rag_router = APIRouter(prefix="/api/rag", tags=["RAG"])
agent_router = APIRouter(prefix="/api/agent", tags=["Agent"])

# ---------------------------------------------------------------------------
# Health & status
# ---------------------------------------------------------------------------

@health_router.get("/health")
def health():
    return {"status": "ok", "mode": settings.app_mode}


# ---------------------------------------------------------------------------
# Health & status
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_supervisor() -> ProcurementSupervisor:
    """Build the agents on the first audit request, not when the server starts."""
    return ProcurementSupervisor()


@agent_router.post("/audit", response_model=AuditResponse)
def audit_request(payload: AuditRequest):
    try:
        return AuditResponse(**get_supervisor().run_audit(payload.request_text))
    # TODO custom exception
    except Exception as e:
        print("Audit failed")
        print(e)
        raise HTTPException(status_code=500, detail=str(e))



# ---------------------------------------------------------------------------
# RAG - upload document
# ---------------------------------------------------------------------------
# In-memory upload tracker (reset on restart)
_UPLOAD_HISTORY: list[dict] = []


@rag_router.post("/ask", response_model=QueryResponse)
def rag_query(payload: QueryRequest):
    """Ask a question; the answer comes only from the indexed documents."""
    try:
        return QueryResponse(answer = ask_question(payload.query, payload.retriever_type))
    # TODO CustomException
    except Exception as e:
        print("RAG query failed")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    """Accept one or more PDFs, keep a copy in the document store, then chunk, embed and index them."""
    print(f'inside upload_documents files present? {files}')
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    
    
    results = []
    tmp_dir = tempfile.mkdtemp()
    try:
        # Process each uploaded file
        for upload in files:
            print(f'upload filename {upload.filename}')
            # Here you would implement the logic to save the file, chunk it, embed it, and index it.
            filename = os.path.basename(upload.filename or "")
            if not filename.endswith(".pdf"):
                results.append({"filename": filename, "status": "skipped", "reason": "Only PDF files are supported."})
                continue

            # read and save file to a temporary directory
            # upload.read() does not extract readable text from the PDF. It reads the raw file bytes and then writes it back to temp file
            file_local_path = os.path.join(tmp_dir, filename)
            print(f'file_local_path {file_local_path}')
            with open(file_local_path, "wb") as f:
                f.write(await upload.read())

            # save the original pdf file to document store for local or cloud storage for cloud mode
            # ingest_pdf is slow and blocking, so run it in a worker thread to keep the server responsive
            try:
                print(f'initiating document_store.save for {file_local_path} {filename}')
                await run_in_threadpool(document_store.save, file_local_path, filename)
            except Exception as store_err:
                print("Could not store original file", filename=filename, error=str(store_err))

            print(f'initiating ingest_pdf for {file_local_path} {filename}')
            # trigger ingestion_pdf process that will perform chunking, embedding and saving in to vectorstore the file content
            summary = await run_in_threadpool(ingest_pdf, file_local_path,  f"upload://{filename}")

            if summary["chunks"] == 0:
                print(f"No chunks extracted, skipping indexing {filename}")
                results.append({"filename": filename, "status": "skipped",
                                "reason": "No extractable text found in PDF (may be a scanned/image-based PDF)."})
                continue

            print(f"Successfully ingested chunks {filename} {summary}")
            results.append({"filename": filename, "status": "ingested", **summary})
            pass  # Replace with actual processing logic

    # TODO CustomException        
    except Exception as e:
        print("Upload failed")
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        print("completed")
        shutil.rmtree(tmp_dir, ignore_errors=True)


    _UPLOAD_HISTORY.extend(results)
    print(_UPLOAD_HISTORY)
    return {"results": results}

@rag_router.get("/uploads")
def list_uploads():
    """Return the history of uploaded documents (in-memory, resets on restart)."""
    return {"uploads": _UPLOAD_HISTORY}


# @rag_router.post("/ingest")
# @rag_router.post("/ingest-gcs", include_in_schema=False)  # old name, kept so older frontends still work
# def trigger_store_ingestion():
#     """Index every PDF already in the document store (local folder or GCS bucket)."""
#     try:
#         totals = ingest_stored_pdfs()
#         return {"status": f"Ingestion complete ({settings.app_mode} mode)", **totals}
#     # TODO custom exception
#     except Exception as e:
#         print("Stored-document ingestion failed")
#         raise HTTPException(status_code=500, detail=str(e))