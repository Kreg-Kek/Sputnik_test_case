from pathlib import Path
import logging
from typing import List

from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from starlette import status

from src.schemas import AlertItem, FileItem, FileUpdate
from src.service import (
    create_file,
    delete_file,
    get_file,
    list_alerts,
    list_files,
    update_file,
    STORAGE_DIR,
)
from src.tasks import scan_file_for_threats

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/files", response_model=List[FileItem])
async def list_files_view() -> List[FileItem]:
    return await list_files()


@app.get("/alerts", response_model=List[AlertItem])
async def list_alerts_view() -> List[AlertItem]:
    return await list_alerts()


@app.post("/files", response_model=FileItem, status_code=status.HTTP_201_CREATED)
async def create_file_view(
    title: str = Form(...),
    file: UploadFile = File(...),
) -> FileItem:
    """
    Create a new file record and enqueue a background scan.
    Ensures uploaded file is properly closed on error.
    """
    try:
        file_item = await create_file(title=title, upload_file=file)
    except Exception as exc:
        try:
            await file.close()
        except Exception:
            logger.debug("Failed to close upload file after create_file error", exc_info=True)
        logger.exception("Failed to create file")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    try:
        scan_file_for_threats.delay(file_item.id)
    except Exception:
        logger.exception("Failed to enqueue scan task for file %s", file_item.id)
    return file_item


@app.get("/files/{file_id}", response_model=FileItem)
async def get_file_view(file_id: str) -> FileItem:
    try:
        return await get_file(file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    except Exception as exc:
        logger.exception("Error fetching file %s", file_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.patch("/files/{file_id}", response_model=FileItem)
async def update_file_view(file_id: str, payload: FileUpdate) -> FileItem:
    try:
        return await update_file(file_id=file_id, title=payload.title)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    except Exception as exc:
        logger.exception("Error updating file %s", file_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@app.get("/files/{file_id}/download")
async def download_file(file_id: str):
    try:
        file_item = await get_file(file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    except Exception as exc:
        logger.exception("Error fetching file for download %s", file_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    stored_path: Path = STORAGE_DIR / file_item.stored_name
    if not stored_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")

    return FileResponse(
        path=str(stored_path),
        media_type=file_item.mime_type,
        filename=file_item.original_name,
    )


@app.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_view(file_id: str):
    try:
        await delete_file(file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    except Exception as exc:
        logger.exception("Error deleting file %s", file_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)