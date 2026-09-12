"""
Upload file routes: /upload-file  (auth required)
  POST /upload-file              — multipart upload, ?folder=
  GET  /upload-file/status/{fileName}
"""
import asyncio
import os
import uuid
from pathlib import Path
from typing import Optional

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, File, Query, UploadFile, status

from youtube.apps.user.types import CurrentUser
from youtube.repositories import StorageRepositoryProtocol

upload_router = APIRouter(prefix='/upload-file', tags=['upload'], route_class=DishkaRoute)

# Simple in-memory status store (replace with Redis for production)
_processing_status: dict[str, int] = {}


@upload_router.post('', status_code=status.HTTP_200_OK)
async def upload_file(
    file: UploadFile = File(...),
    folder: Optional[str] = Query(default='uploads'),
    current_user: FromDishka[CurrentUser] = None,
    storage: FromDishka[StorageRepositoryProtocol] = None,
) -> list[dict]:
    """Upload a file (image/video). Returns [{url, name, maxResolution}]."""
    content = await file.read()
    filename = file.filename or f'{uuid.uuid4().hex}'
    ext = Path(filename).suffix.lower()
    unique_name = f'{uuid.uuid4().hex}{ext}'
    storage_path = f'{folder}/{unique_name}'

    await storage.write(storage_path, content)

    # For videos, register as processing
    if ext in ('.mp4', '.webm', '.mov', '.avi', '.mkv'):
        _processing_status[unique_name] = 0
        asyncio.create_task(_simulate_processing(unique_name))

    # Determine maxResolution for video files
    max_resolution = '1080p' if ext in ('.mp4', '.webm', '.mov') else None

    url = f'/storage/{storage_path}'
    return [{'url': url, 'name': unique_name, 'maxResolution': max_resolution}]


@upload_router.get('/status/{fileName}', status_code=status.HTTP_200_OK)
async def get_processing_status(
    fileName: str,
    current_user: FromDishka[CurrentUser] = None,
) -> int:
    """Return processing/conversion progress (0–100)."""
    return _processing_status.get(fileName, 100)


async def _simulate_processing(filename: str) -> None:
    """Simulate progressive video processing status."""
    import asyncio
    for progress in range(10, 101, 10):
        await asyncio.sleep(3)
        _processing_status[filename] = progress
    # Clean up after completion
    await asyncio.sleep(60)
    _processing_status.pop(filename, None)
