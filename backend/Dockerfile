# API RTE Predictor. Image CPU uniquement : PyTorch CPU pèse environ 200 Mo, contre plus de 2 Go avec CUDA.
FROM python:3.14-slim AS deps

RUN pip install --no-cache-dir poetry poetry-plugin-export
WORKDIR /build
COPY pyproject.toml poetry.lock ./
# Dépendances de production (sans les tests), sans torch : installé à part, en version CPU
RUN poetry export --without-hashes --without dev -f requirements.txt -o requirements.txt \
    && grep -v -i '^torch' requirements.txt > requirements-notorch.txt

FROM python:3.14-slim

# libgomp : requis par LightGBM et scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=deps /build/requirements-notorch.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements-notorch.txt \
    && pip install --no-cache-dir "git+https://github.com/mistralai/timestral.git@a534bdbd244d64f3d9d743f46c7bf6fc330ed4ff"

# Code et résultats du benchmark (versionnés). data/ (modèle, normaliseurs, bases SQLite) est monté en volume.
COPY main.py ./
COPY src ./src
COPY benchmark ./benchmark

RUN useradd --create-home --uid 1000 app && mkdir -p /app/data && chown -R app /app
USER app

# Timestral 28M : poids téléchargés une fois depuis Hugging Face, puis gardés dans le volume data/ (survivent aux mises à jour)
ENV APP_ENV=production PYTHONUNBUFFERED=1 HF_HOME=/app/data/huggingface
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# --proxy-headers : lit la vraie adresse du visiteur (limites de tentatives par IP) derrière le reverse proxy
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
