from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Optional


class FileStatus(str, Enum):
    """File status"""
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


# Request and Response Models

class FileUploadRequest(BaseModel):
    """File upload request (for multipart form data)"""
    uploaded_by: str 


class FileUploadResponse(BaseModel):
    """File upload response"""
    file_id: str
    file_url: str
    original_filename: str
    file_size: int
    content_type: str
    upload_timestamp: datetime


class FileResponse(BaseModel):
    """File response"""
    file_id: str
    original_filename: str
    file_size: int
    content_type: str
    file_url: str
    uploaded_by: str
    uploaded_by_name: Optional[str]
    status: FileStatus
    upload_timestamp: datetime


class FileListResponse(BaseModel):
    """File list response with pagination"""
    files: list[FileResponse]
    total: int
    skip: int
    limit: int


# Base File Model

class File(BaseModel):
    """Internal file model"""
    file_id: str
    original_filename: str
    file_size: int
    content_type: str
    file_url: str
    uploaded_by: str
    status: FileStatus = FileStatus.ACTIVE
    upload_timestamp: datetime = None
    
    def __init__(self, **data):
        if not data.get('upload_timestamp'):
            data['upload_timestamp'] = datetime.utcnow()
        super().__init__(**data)
    
    def to_response(self) -> FileResponse:
        """Convert to response"""
        return FileResponse(
            file_id=self.file_id,
            original_filename=self.original_filename,
            file_size=self.file_size,
            content_type=self.content_type,
            file_url=self.file_url,
            uploaded_by=self.uploaded_by,
            status=self.status,
            upload_timestamp=self.upload_timestamp
        )