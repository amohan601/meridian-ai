from fastapi import FastAPI
from config.settings import settings    
from fastapi.middleware.cors import CORSMiddleware

from api.endpoints import health_router,rag_router,agent_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-agent procurement audit & RAG document intelligence backend.",
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