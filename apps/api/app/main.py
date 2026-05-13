from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_cors_origins, get_settings
from app.routers import (
    ai_drafts,
    clients,
    email_import_batches,
    email_messages,
    email_record_links,
    evidence_files,
    health,
    jobs,
    outlook_import,
    reminders,
    sites,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(clients.router)
    app.include_router(sites.router)
    app.include_router(jobs.router)
    app.include_router(outlook_import.router)
    app.include_router(reminders.router)
    app.include_router(evidence_files.router)
    app.include_router(email_import_batches.router)
    app.include_router(email_messages.router)
    app.include_router(email_record_links.router)
    app.include_router(ai_drafts.router)
    return app


app = create_app()
