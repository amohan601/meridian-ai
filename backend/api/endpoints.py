
from fastapi import APIRouter, UploadFile, File,HTTPException
import os
import shutil
from config.settings import settings   
from fastapi.concurrency import run_in_threadpool
from rag import document_store
from rag.retrieval import ask_question
from rag.data_ingestion import ingest_pdf,ingest_stored_pdfs
import tempfile
from api.schemas import  QueryRequest, QueryResponse, AuditRequest, AuditResponse
from agent.agents import ProcurementSupervisor
from functools import lru_cache
from logger.custom_logger import GLOBAL_LOGGER as log
from exceptions import MeridianError
from datetime import datetime, timezone
import platform
import sys

health_router = APIRouter(prefix="/api", tags=["Health"])
rag_router = APIRouter(prefix="/api/rag", tags=["RAG"])
agent_router = APIRouter(prefix="/api/agent", tags=["Agent"])
status_router = APIRouter(prefix="/api", tags=["Status"])

_server_start_time = datetime.now(timezone.utc)

# ---------------------------------------------------------------------------
# Health & status
# ---------------------------------------------------------------------------

@health_router.get("/health")
def health():
    log.info(f"Performing healthcheck of meridian backend app \"status\": \"ok\", \"mode\": {settings.app_mode}")
    return {"status": "ok", "mode": settings.app_mode}

@status_router.get("/status")
def system_status():
    """Return system configuration and health information (makes no calls to Google)."""
    uptime_seconds = int((datetime.now(timezone.utc) - _server_start_time).total_seconds())
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    cloud = settings.is_cloud

    return{
        "mode": settings.app_mode,
        "backend":{
            "status": "healthy",
            "uptime": f"{hours:02d}h {minutes:02d}m {seconds:02d}s",
            "python_version": sys.version.split()[0],
            "platform": platform.system(),

        },
        "gcp": {
            "project_id": "TBD For Cloud" if cloud else "not used (local mode)",
            "region": "TBD For Cloud" if cloud else "NA",

        },
        "storage":{
            "location": document_store.location(),
            "gcs_bucket": "TBD For cloud" if cloud else "-",
            "gcs_prefix":  "TBD For cloud" if cloud else "-",

        },
        "vector_search":{
            "backend": "Vertex AI Vector Search" if cloud else "Chroma (local disk)",
            "index_id": ("TBD For cloud") if cloud else settings.chroma_dir,
            "endpoint_id": ("TBD For cloud") if cloud else "-",
            "stream_update": cloud,

        },
        "models": {
            "embedding": settings.local_embedding_model_name,
            "llm": settings.llm_model_name,
            "llm_framework": (
                "Gemini API (chat) + Vertex AI (embeddings) via LangChain v1" if cloud
                else "Gemini API (chat + embeddings) via LangChain v1"
            ),
        },
        "ingestion": {
            "uploads_this_session": len(_UPLOAD_HISTORY),
        },
    }

# ---------------------------------------------------------------------------
# api endpoints
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_supervisor() -> ProcurementSupervisor:
    """Build the agents on the first audit request, not when the server starts."""
    return ProcurementSupervisor()


@agent_router.post("/audit", response_model=AuditResponse)
def audit_request(payload: AuditRequest):
    try:
        log.info(f"inside /audit endpoint ")
        return AuditResponse(**get_supervisor().run_audit(payload.request_text))
    except MeridianError:
        raise  # handled in api/main.py
    except Exception as e:
        log.exception("Audit failed")
        raise HTTPException(status_code=500, detail=str(e))



# ---------------------------------------------------------------------------
# RAG - upload document
# ---------------------------------------------------------------------------
# In-memory upload tracker (reset on restart)
_UPLOAD_HISTORY: list[dict] = []


@rag_router.post("/ask", response_model=QueryResponse)
def rag_query(payload: QueryRequest):
    """Ask a question; the answer comes only from the indexed documents."""
    log.info(f"inside /ask endpoint for {payload.query} and retriever_type {payload.retriever_type}")
    try:
        return QueryResponse(answer = ask_question(payload.query, payload.retriever_type))
    except MeridianError:
        raise
    except Exception as e:
        log.exception("RAG query failed")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    """Accept one or more PDFs, keep a copy in the document store, then chunk, embed and index them."""
    log.info(f'inside upload_documents endpoint files present? {files}')
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    
    
    results = []
    tmp_dir = tempfile.mkdtemp()
    try:
        # Process each uploaded file
        for upload in files:
            log.info(f'upload filename {upload.filename}')
            # Here you would implement the logic to save the file, chunk it, embed it, and index it.
            filename = os.path.basename(upload.filename or "")
            if not filename.endswith(".pdf"):
                results.append({"filename": filename, "status": "skipped", "reason": "Only PDF files are supported."})
                continue

            # read and save file to a temporary directory
            # upload.read() does not extract readable text from the PDF. It reads the raw file bytes and then writes it back to temp file
            file_local_path = os.path.join(tmp_dir, filename)
            log.info(f'file_local_path {file_local_path}')
            with open(file_local_path, "wb") as f:
                f.write(await upload.read())

            # save the original pdf file to document store for local or cloud storage for cloud mode
            # ingest_pdf is slow and blocking, so run it in a worker thread to keep the server responsive
            try:
                log.info(f'initiating document_store.save for {file_local_path} {filename}')
                await run_in_threadpool(document_store.save, file_local_path, filename)
            except Exception as store_err:
                log.warning("Could not store original file", filename=filename, error=str(store_err))

            log.info(f'initiating ingest_pdf for {file_local_path} {filename}')
            # trigger ingestion_pdf process that will perform chunking, embedding and saving in to vectorstore the file content
            summary = await run_in_threadpool(ingest_pdf, file_local_path,  f"upload://{filename}")

            if summary["chunks"] == 0:
                log.warning("No chunks extracted, skipping indexing", filename=filename)
                results.append({"filename": filename, "status": "skipped",
                                "reason": "No extractable text found in PDF (may be a scanned/image-based PDF)."})
                continue

            log.info(f"Successfully ingested chunks {filename} {summary}")
            results.append({"filename": filename, "status": "ingested", **summary})
            pass  # Replace with actual processing logic

    except MeridianError:
        raise  
    except Exception as e:
        log.exception(f"Upload failed str(e)")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        log.info("completed")
        shutil.rmtree(tmp_dir, ignore_errors=True)


    _UPLOAD_HISTORY.extend(results)
    return {"results": results}

@rag_router.get("/uploads")
def list_uploads():
    """Return the history of uploaded documents (in-memory, resets on restart)."""
    log.info(f"inside /uploads endpoint ")
    return {"uploads": _UPLOAD_HISTORY}


@rag_router.post("/ingest")
@rag_router.post("/ingest-gcs")  # old name, kept so older frontends still work
def trigger_store_ingestion():
    """Index every PDF already in the document store (local folder or GCS bucket)."""
    log.info(f"inside /ingest endpoint ")
    try:
        totals = ingest_stored_pdfs()
        return {"status": f"Ingestion complete ({settings.app_mode} mode)", **totals}
    # TODO custom exception
    except Exception as e:
        print("Stored-document ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))