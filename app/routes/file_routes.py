from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from app.databases.postgres import get_db
from app.models.uploads import FileResponse, FileUploadResponse, FileListResponse
from app.services.uploads.service import UploadService
from app.middlewares.auth import (
    require_admin,
    require_maintainer_or_admin,
    require_any_role,
    get_current_user_required
)
from app.models.user import UserResponse

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Upload a file to Azure Blob Storage (Any authenticated user)"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    # Optional: Add file size validation
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413,
                            detail="File too large. Maximum size is 50MB")

    # Use current user's ID as uploaded_by
    return UploadService.upload_file(db, file, current_user.id)


@router.get("/", response_model=FileListResponse)
def get_files(
        skip: int = Query(
            0,
            ge=0,
            description="Number of files to skip"),
    limit: int = Query(
            100,
            ge=1,
            le=1000,
            description="Number of files to return"),
        db: Session = Depends(get_db),
        current_user: UserResponse = Depends(require_maintainer_or_admin)):
    """Get all files with pagination (MAINTAINER+ only)"""
    return UploadService.get_all_files(db, skip=skip, limit=limit)


@router.get("/{file_id}", response_model=FileResponse)
def get_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get file by ID (Any authenticated user can view files)"""
    file = UploadService.get_file_by_id(db, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@router.delete("/{file_id}")
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Delete file (Users can delete their own files, ADMIN can delete all)"""
    # Get file info first
    file_info = UploadService.get_file_by_id(db, file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    # Check permissions: ADMIN can delete any file, users can delete their own
    if current_user.role.value != "ADMIN" and file_info.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only delete your own files")

    success = UploadService.delete_file(db, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted successfully"}


@router.get("/stats/count")
def get_files_count(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_maintainer_or_admin)
):
    """Get total files count (MAINTAINER+ only)"""
    count = UploadService.get_files_count(db)
    return {"total_files": count}


@router.get("/url/{file_id}")
def get_file_url(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get file URL by file ID (Any authenticated user)"""
    file_url = UploadService.get_file_url_by_id(db, file_id)
    if not file_url:
        raise HTTPException(status_code=404, detail="File not found")
    return {"file_id": file_id, "file_url": file_url}
