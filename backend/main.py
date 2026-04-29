"""FastAPI application entry point.

Main application factory with startup/shutdown hooks,
middleware configuration, and route registration.
"""
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from core.config import settings
from core.logging import get_logger, setup_logging
from core.middleware import ErrorHandlingMiddleware
from db.session import Base, engine
from services.alert_lifecycle_service import alert_lifecycle_manager
from services.websocket_service import ws_manager

setup_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description='Industrial IoT Monitoring System API',
        docs_url='/api/docs' if settings.DEBUG else None,
        redoc_url='/api/redoc' if settings.DEBUG else None,
        openapi_url='/api/openapi.json' if settings.DEBUG else None,
    )
    
    # CORS middleware - allows frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # Error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Register API routes
    app.include_router(api_router)
    
    # Health check endpoint
    @app.get('/health')
    async def health_check():
        """Health check endpoint for load balancers."""
        return {
            'status': 'healthy',
            'service': settings.APP_NAME,
            'version': settings.APP_VERSION
        }
    
    @app.on_event('startup')
    async def on_startup():
        """Initialize application on startup."""
        if settings.AUTO_CREATE_SCHEMA:
            Base.metadata.create_all(bind=engine)
            logger.warning('AUTO_CREATE_SCHEMA is enabled. Use Alembic in production.')
        ws_manager.start_pubsub_listener(asyncio.get_running_loop())
        alert_lifecycle_manager.start()
        logger.info('Application startup complete | env=%s', settings.APP_ENV)
    
    @app.on_event('shutdown')
    async def on_shutdown():
        """Cleanup on application shutdown."""
        await alert_lifecycle_manager.stop()
        ws_manager.stop_pubsub_listener()
        logger.info('Application shutdown complete')
    
    return app


app = create_app()
