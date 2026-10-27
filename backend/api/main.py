from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings    
from exceptions import ConfigurationError,IngestionError
from api.endpoints import health_router,rag_router,agent_router,status_router
from logger import GLOBAL_LOGGER as log
from logger import _LOGGER_INSTANCE
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Meridian AI starting", mode=settings.app_mode, llm=settings.llm_model_name)
    yield  # the app runs here
    # Shutdown (cloud mode only): flush logs to GCS, because Cloud Run's disk disappears
    # TODO invoke flush w

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent procurement audit & RAG document intelligence backend.",
    lifespan = lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(rag_router)
app.include_router(agent_router)
app.include_router(status_router)


@app.exception_handler(ConfigurationError)
async def configuration_error(_:Request, exc: ConfigurationError):
    """A missing setting is not a crash: tell the caller exactly what to set."""
    log.error("Configuration error", error=str(exc))
    return JSONResponse(status_code = 503, content={"detail": str(exc)})



@app.exception_handler(IngestionError)
async def ingestion_error(_: Request, exc: IngestionError):
    log.error("Ingestion error", error=str(exc))
    return JSONResponse(status_code=422, content={"detail": str(exc)})