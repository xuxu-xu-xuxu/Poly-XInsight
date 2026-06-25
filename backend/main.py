from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.upload import router as upload_router
from backend.routes.papers import router as papers_router
from backend.routes.chat import router as chat_router
from backend.routes.extract import router as extract_router
from backend.routes.visualize import router as visualize_router
from backend.routes.entities import router as entities_router
from backend.routes.analytics import router as analytics_router
from backend.routes.auth import router as auth_router
from backend.routes.conversations import router as conversations_router
from backend.routes.domains import router as domains_router
from backend.routes.downloads import router as downloads_router
from backend.routes.knowledge_graph import router as knowledge_graph_router
from backend.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception:
        pass
    yield


app = FastAPI(title="Poly XInsight API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(papers_router)
app.include_router(chat_router)
app.include_router(extract_router)
app.include_router(visualize_router)
app.include_router(entities_router)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(domains_router)
app.include_router(downloads_router)
app.include_router(knowledge_graph_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
