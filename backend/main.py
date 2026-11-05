import os
from fastapi import FastAPI
from src.auth.adapters.api.auth_routes import auth_router
from src.electricity.adapters.api.electricity_routes import electricity_router
from fastapi.middleware.cors import CORSMiddleware
from src.prediction.adapters.api.prediction_routes import prediction_router


app=FastAPI()

# Ajout du middleware CORS à mon app

app.add_middleware(
    middleware_class=CORSMiddleware,
    # Origines autorisées, séparées par des virgules. Inutile si le frontend est servi sur le même domaine que l'API.
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
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