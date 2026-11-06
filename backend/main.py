import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.auth.adapters.api.auth_routes import auth_router
from src.electricity.adapters.api.electricity_routes import electricity_router
from fastapi.middleware.cors import CORSMiddleware
from src.prediction.adapters.api.prediction_routes import prediction_router, preload_timestral


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # TIMESTRAL_PRELOAD=true : charge Timestral en tâche de fond, sans retarder le démarrage ni la sonde de santé
    if os.getenv("TIMESTRAL_PRELOAD", "false").lower() in ("1", "true", "yes"):
        threading.Thread(target=preload_timestral, daemon=True).start()
    yield


app=FastAPI(lifespan=lifespan)

# Ajout du middleware CORS à mon app

app.add_middleware(
    middleware_class=CORSMiddleware,
    # Origines autorisées, séparées par des virgules. Inutile si le frontend est servi sur le même domaine que l'API.
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    # En développement (ALLOWED_ORIGINS non défini), tout port de localhost est accepté : Vite change de port si 5173 est pris.
    allow_origin_regex=None if os.getenv("ALLOWED_ORIGINS") else r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/")
def root():
    return {"message": "API Electricité"}


@app.get("/health")
def health():
    """Sonde de santé pour le reverse proxy et Docker (sans authentification, sans donnée)."""
    return {"status": "ok"}


app.include_router(router=electricity_router)

app.include_router(router=prediction_router)

app.include_router(router=auth_router)