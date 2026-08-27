import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import MEDIA_DIR
from .database import init_db
from .routers import auth, cases, persons

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Unidentified Body Identification System (UBIS)",
    version="0.1.0",
    description=(
        "AI-assisted decision support for identifying unidentified deceased "
        "persons. Produces an explainable ranked candidate list for authorized "
        "human verification. It does not make identification decisions."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # prototype only — restrict before any real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(persons.router)
app.include_router(cases.router)

# Prototype convenience: serve evidence images directly. In a real deployment
# these must be behind authentication (signed, short-lived URLs).
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health():
    from .ai import face, index, objects

    return {
        "status": "ok",
        "engines": {
            "face": face.engine_name(),
            "objects": objects.engine_name(),
            "retrieval": index.engine_name(),
        },
    }