import logging  # noqa: I001
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

# New JWT-based routes
from youtube.apps.user.auth_routes import auth_router, verify_router
from youtube.apps.user.profile_routes import user_router, watch_history_router
from youtube.apps.video.public_routes import public_video_router, channel_router
from youtube.apps.video.studio_routes import studio_router
from youtube.apps.video.upload_routes import upload_router
from youtube.apps.video.playlist_routes import router as playlist_router
from youtube.apps.comment.routes import comment_router
from youtube.container import ContainerManager

from youtube.exceptions import use_exceptions_handlers
from youtube.loggers import use_logging
from youtube.middleware import use_middleware
from youtube.settings import AppSettingsSchema


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info('Application starting')
    yield
    logging.info('Application stopping')
    await ContainerManager.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title='YouTube Clone API',
        version='2.0.0',
        lifespan=lifespan,
    )

    routers = [
        auth_router,
        verify_router,
        user_router,
        watch_history_router,
        public_video_router,
        channel_router,
        studio_router,
        upload_router,
        playlist_router,
        comment_router,
    ]

    for r in routers:
        app.include_router(r)

    api_v1_router = APIRouter(prefix='/api')
    for r in routers:
        api_v1_router.include_router(r)

    from youtube.contrib.healthcheck.router import router as health_router
    app.include_router(health_router)
    api_v1_router.include_router(health_router)

    app.include_router(api_v1_router)

    ContainerManager.init_for_fastapi(app)
    settings = AppSettingsSchema()
    use_exceptions_handlers(app, settings)
    use_middleware(app, settings.cors_origins)
    use_logging(settings)

    # Serve storage files locally if provider is local
    from fastapi.staticfiles import StaticFiles
    import os

    if settings.storage.provider == 'local':
        storage_dir = settings.storage.dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        app.mount('/storage', StaticFiles(directory=storage_dir), name='storage')

    return app


app = create_app()
