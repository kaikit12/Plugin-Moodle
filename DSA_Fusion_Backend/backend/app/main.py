import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import router
from app.api.submissions import router as submissions_router
from app.api.auth import router as auth_router
from app.api.admin_router import router as admin_router
from app.api.plagiarism_router import router as plagiarism_router
from app.api.rubric_router import router as rubric_router
from app.containers.container import get_container, reset_container
from app.core.config import (CORS_ALLOWED_ORIGINS, ENVIRONMENT, PORT,
                             check_and_log_config)
from app.services.job_store import start_job_cleanup, stop_job_cleanup
from app.utils.logging_config import setup_logging
from app.utils.sentry import init_sentry
from app.utils.auth import hash_password

# ---------------------------------------------------------------------------
# Logging & Sentry (module-level, runs once on first import)
# ---------------------------------------------------------------------------
setup_logging(level="INFO", log_format="text")
logger = logging.getLogger("dsa.main")
init_sentry(environment=ENVIRONMENT)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("=" * 60)
    logger.info("DSA AutoGrader — Starting...")
    logger.info("=" * 60)

    # Validate configuration
    check_and_log_config()

    # Initialise dependency-injection container
    logger.info("Initialising DI container...")
    try:
        container = get_container()
        logger.info("Container ready.")
    except Exception as exc:
        logger.error("Container init failed: %s", exc)
        raise

    # Background cleanup task
    start_job_cleanup()
    logger.info("Background job cleanup started.")

    # Seed demo accounts
    try:
        repo = container.get_repository()

        # Lecturer account
        if not repo.get_user_by_username("lecturer1"):
            logger.info("Creating lecturer account: lecturer1 / lec123")
            repo.create_user(
                username="lecturer1",
                password_hash=hash_password("lec123"),
                full_name="DSA Lecturer",
                role="LECTURER",
                email="lecturer@dsa.local"
            )
        else:
            logger.info("Lecturer account exists")

        # Student accounts
        students = [
            ("122000001", "sv123", "Nguyen Van A"),
            ("122000002", "sv123", "Tran Thi B"),
            ("122000003", "sv123", "Le Van C"),
        ]
        for student_id, password, name in students:
            if not repo.get_user_by_username(student_id):
                logger.info(f"Creating student account: {student_id} / {password}")
                repo.create_user(
                    username=student_id,
                    password_hash=hash_password(password),
                    full_name=name,
                    role="STUDENT",
                    email=f"{student_id}@dsa.local"
                )
            else:
                logger.info(f"Student account {student_id} exists")
    except Exception as exc:
        logger.warning("Seed demo account failed: %s", exc)

    logger.info("=" * 60)
    logger.info("Server is ready!")
    logger.info("  URL:  http://localhost:%s", PORT)
    logger.info("  Docs: http://localhost:%s/docs", PORT)
    logger.info("=" * 60)

    yield  # ---- application is running ----

    # Shutdown
    logger.info("Shutting down DSA AutoGrader...")
    await stop_job_cleanup()
    if container:
        try:
            container.shutdown()
        except Exception as exc:
            logger.error("Container shutdown error: %s", exc)
    reset_container()
    logger.info("DSA AutoGrader shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DSA AutoGrader",
    description="Automatic DSA Assignment Grading System",
    version="Production",
    lifespan=lifespan,
)

# CORS
_cors_origins = (
    CORS_ALLOWED_ORIGINS.split(",") if CORS_ALLOWED_ORIGINS != "*" else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routers (registered FIRST to take priority)
# ---------------------------------------------------------------------------
app.include_router(router, prefix="/api")
app.include_router(submissions_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(plagiarism_router)
app.include_router(rubric_router)

# ---------------------------------------------------------------------------
# Frontend static files (SPA routing with trailingSlash support)
# ---------------------------------------------------------------------------
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
frontend_path = os.path.abspath(os.path.join(_backend_dir, "..", "frontend", "out"))

if os.path.exists(frontend_path):
    logger.info(f"Mounting frontend from: {frontend_path}")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """
        Serve Next.js static export with trailingSlash support.

        Next.js with trailingSlash: true produces:
        - /index.html (root - student page)
        - /login/index.html (login page)
        - /admin/index.html (admin page)

        This handler:
        1. Tries to serve the exact file if it exists
        2. For directory routes (/login), serves /login/index.html
        3. Falls back to root index.html for client-side routing
        """
        # Build file path
        file_path = Path(frontend_path) / full_path

        # If path ends with slash or is empty, look for index.html
        if full_path.endswith("/") or full_path == "":
            index_path = file_path / "index.html" if full_path else Path(frontend_path) / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))

        # Try to serve the exact file
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        # Try adding index.html for directory routes (e.g., /login -> /login/index.html)
        index_path = file_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        
        # Fallback to root index.html for SPA client-side routing
        root_index = Path(frontend_path) / "index.html"
        if root_index.exists():
            return FileResponse(str(root_index))
        
        # Last resort: 404
        return JSONResponse({"detail": "Not Found"}, status_code=404)
else:
    logger.warning(
        f"Frontend 'out' directory not found at {frontend_path}. "
        f"Build the Next.js app: cd frontend && npm run build"
    )
