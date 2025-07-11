from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import time
import logging

from config import settings
from api.routes import results, references, auth, admin, social, stats, sessions
from database import engine, Base

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Créer les tables
Base.metadata.create_all(bind=engine)

# Initialiser FastAPI
app = FastAPI(
    title="Portail des Résultats d'Examens - Mauritanie",
    description="API complète pour la gestion et consultation des résultats d'examens mauritaniens",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Middleware de logging et métriques
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log des requêtes
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response

# Gestionnaire d'erreurs personnalisé
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error for {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Erreur de validation des données",
            "errors": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception for {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Erreur interne du serveur",
            "message": "Une erreur inattendue s'est produite"
        }
    )

# Routes de santé
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": time.time()
    }

@app.get("/")
async def root():
    return {
        "message": "Portail des Résultats d'Examens - Mauritanie",
        "docs": "/api/docs",
        "version": "1.0.0"
    }

@app.get("/health/redis")
async def redis_health_check():
    """Vérifier la santé de Redis"""
    try:
        from database import get_redis
        redis = await get_redis()
        await redis.ping()
        return {"redis": "healthy", "status": "connected"}
    except Exception as e:
        return {"redis": "unhealthy", "error": str(e), "status": "disconnected"}

@app.get("/health/cache")
async def cache_health_check():
    """Tester le cache Redis"""
    from core.cache import cache_manager
    try:
        # Test d'écriture/lecture
        test_key = "health_test"
        test_value = {"test": True, "timestamp": time.time()}
        
        await cache_manager.set(test_key, test_value, 10)
        cached_value = await cache_manager.get(test_key)
        
        if cached_value and cached_value.get("test"):
            return {"cache": "working", "test": "passed"}
        else:
            return {"cache": "not_working", "test": "failed"}
    except Exception as e:
        return {"cache": "error", "test": "failed", "error": str(e)}

# Inclure les routes
app.include_router(results.router)
app.include_router(references.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(social.router)
app.include_router(stats.router)
app.include_router(sessions.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )