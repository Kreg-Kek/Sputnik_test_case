import logging
import mimetypes
import os
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.models import Alert, StoredFile

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "files"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DB_URL = (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USER','')}:"
    f"{os.getenv('POSTGRES_PASSWORD','')}@{os.getenv('POSTGRES_HOST','localhost')}:"
    f"{os.getenv('PGPORT', int(os.getenv('POSTGRES_PORT', '5432')))}/{os.getenv('POSTGRES_DB','')}"
)
engine = create_async_engine(DB_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def list_files() -> List[StoredFile]:
    async with async_session_maker() as session:
        result = await session.execute(select(StoredFile).order_by(StoredFile.created_at.desc()))
        return list(result.scalars().all())


async def list_alerts() -> List[Alert]:
    async with async_session_maker() as session:
        result = await session.execute(select(Alert).order_by(Alert.created_at.desc()))
        return list(result.scalars().all())


async def get_file(file_id: str) -> StoredFile:
    async with async_session_maker() as session:
        file_item = await session.get(StoredFile, file_id)
        if not file_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return file_item


def _secure_filename(name: str) -> str:
    return Path(name).name or ""


async def create_file(title: str, upload_file: UploadFile) -> StoredFile:
    file_id = str(uuid4())
    suffix = Path(upload_file.filename or "").suffix
    stored_name = f"{file_id}{suffix}"
    stored_path = STORAGE_DIR / stored_name

    total_size = 0
    try:
        original_name = _secure_filename(upload_file.filename or stored_name)

        with stored_path.open("wb") as f:
            while True:
                chunk = await upload_file.read(1024 * 64)  # 64KB
                if not chunk:
                    break
                f.write(chunk)
                total_size += len(chunk)
    finally:
        try:
            await upload_file.close()
        except Exception:
            logger.debug("Failed to close UploadFile for %s", file_id, exc_info=True)

    if total_size == 0:
        if stored_path.exists():
            try:
                stored_path.unlink()
            except Exception:
                logger.debug("Failed to remove empty stored file %s", stored_path, exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")

    mime_type = upload_file.content_type or mimetypes.guess_type(stored_name)[0] or "application/octet-stream"

    file_item = StoredFile(
        id=file_id,
        title=title,
        original_name=original_name,
        stored_name=stored_name,
        mime_type=mime_type,
        size=total_size,
        processing_status="uploaded",
    )

    async with async_session_maker() as session:
        session.add(file_item)
        await session.commit()
        await session.refresh(file_item)

    return file_item


async def update_file(file_id: str, title: str) -> StoredFile:
    async with async_session_maker() as session:
        file_item = await session.get(StoredFile, file_id)
        if not file_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        file_item.title = title
        await session.commit()
        await session.refresh(file_item)
        return file_item


async def delete_file(file_id: str) -> None:
    async with async_session_maker() as session:
        file_item = await session.get(StoredFile, file_id)
        if not file_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        stored_path = STORAGE_DIR / file_item.stored_name
        if stored_path.exists():
            try:
                stored_path.unlink()
            except Exception:
                logger.exception("Failed to remove stored file %s", stored_path)
        await session.delete(file_item)
        await session.commit()


async def get_file_path(file_id: str) -> Tuple[StoredFile, Path]:
    file_item = await get_file(file_id)
    stored_path = STORAGE_DIR / file_item.stored_name
    if not stored_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")
    return file_item, stored_path


async def create_alert(file_id: str, level: str, message: str) -> Alert:
    alert = Alert(file_id=file_id, level=level, message=message)
    async with async_session_maker() as session:
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        return alert
