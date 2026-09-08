import logging  # noqa: I001
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from youtube.apps.video.routes import router as video_router
from youtube.apps.video.playlist_routes import router as playlist_router
from youtube.apps.user.routes import user_router
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
        title='youtube API',
        version='0.1.0',
    )
    api_v1_router = APIRouter(prefix='/v1')
    api_v1_router.include_router(user_router)
    api_v1_router.include_router(video_router)
    api_v1_router.include_router(playlist_router)
    api_v1_router.include_router(comment_router)

    from youtube.contrib.healthcheck.router import router as health_router

    main_api_router = APIRouter(prefix='/api')
    main_api_router.include_router(api_v1_router)
    main_api_router.include_router(health_router)

    app.include_router(main_api_router)

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
