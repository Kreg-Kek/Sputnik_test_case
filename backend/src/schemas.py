from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FileItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    original_name: str
    mime_type: str
    size: int = Field(ge=0)
    processing_status: str
    scan_status: Optional[str] = None
    scan_details: Optional[str] = None
    metadata_json: Optional[dict] = None
    requires_attention: bool = False
    created_at: datetime
    updated_at: datetime


class FileUpdate(BaseModel):
    title: str = Field(..., min_length=1)


class AlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: str
    level: str
    message: str
    created_at: datetime
