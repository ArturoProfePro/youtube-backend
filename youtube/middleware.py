"""
Module containing middleware.
"""

import time
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.cors import CORSMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


async def add_process_time_header(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    start_time = time.perf_counter()
    response = await call_next(request)
    response.headers['x-process-time'] = f'{time.perf_counter() - start_time}'
    return response


async def logging_middleware(request: Request, call_next):
    clear_contextvars()

    bind_contextvars(request_id=str(uuid4()))

    response = await call_next(request)
    return response


async def forwarded_proto_middleware(request: Request, call_next):
    if request.headers.get('x-forwarded-proto') == 'https':
        request.scope['scheme'] = 'https'
    response = await call_next(request)
    return response


async def set_guest_cookie_middleware(request: Request, call_next):
    response = await call_next(request)
    if hasattr(request.state, 'new_guest_id'):
        response.set_cookie(
            key='guest_id',
            value=request.state.new_guest_id,
            httponly=True,
            samesite='lax',
            path='/',
            max_age=60 * 60 * 24 * 15,
        )
    return response


def use_middleware(
    app: FastAPI,
    cors_origins: list[str],
    *,
    allow_methods: list[str] | None = None,
    allow_headers: list[str] | None = None,
) -> FastAPI:
    """
    Register middleware.
    """

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:3000', 'http://127.0.0.1:3000', *cors_origins],
        allow_credentials=True,
        allow_methods=allow_methods or ['*'],
        allow_headers=allow_headers or ['*', 'Access-Control-Allow-Origin', 'Content-Type', 'Authorization'],
    )

    app.middleware('http')(add_process_time_header)
    app.middleware('http')(logging_middleware)
    app.middleware('http')(forwarded_proto_middleware)
    app.middleware('http')(set_guest_cookie_middleware)
    return app
