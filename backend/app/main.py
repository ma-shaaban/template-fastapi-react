"""FastAPI backend: JSON API under /api/*, health at /healthz, and the built
React SPA served from ./static at / (API routes are registered first, so they
take precedence over the static mount)."""

import os
from pathlib import Path

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="fastapi-react-app")


def _db_conninfo() -> dict:
    """Connection parameters from the platform `app-db` Secret env contract."""
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "5432")),
        "dbname": os.environ.get("DB_NAME", "postgres"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "connect_timeout": 3,
    }


@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI"}


@app.get("/api/db-check")
def db_check():
    """Round-trip to the database: SELECT now(). 503 if the DB is unreachable."""
    try:
        with psycopg.connect(**_db_conninfo()) as conn, conn.cursor() as cur:
            cur.execute("SELECT now()")
            (now,) = cur.fetchone()
        return {"db": "ok", "now": now.isoformat()}
    except Exception as exc:  # surface the reason, keep the app alive
        return JSONResponse(status_code=503, content={"db": "error", "detail": str(exc)})


@app.get("/api/version")
def version():
    # APP_VERSION is baked into the image at build time (Dockerfile ARG VERSION);
    # "dev" outside the container.
    return {"version": os.environ.get("APP_VERSION", "dev")}


@app.get("/healthz")
def healthz():
    """Readiness: process is up. Deliberately DB-free — a brief DB outage must
    not take the pod out of rotation (the SPA and /api/hello still work)."""
    return {"status": "ok"}


# Mounted last so every /api/* + /healthz route above wins. html=True serves
# index.html at / and on 404s within the mount (SPA-friendly). The directory
# only exists in the container image (built by the Dockerfile frontend stage);
# in local dev run the Vite dev server instead (it proxies /api → :8080).
_static = Path(__file__).resolve().parent.parent / "static"
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="spa")
