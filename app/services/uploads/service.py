from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, BinaryIO
from fastapi import HTTPException, UploadFile

from app.schemas.file_schema import FileSchema
from app.models.uploads import FileResponse, FileUploadResponse, FileListResponse, FileStatus
from app.utils.file_id import generate_file_id
from app.databases.azure_blob import azure_client


class UploadService:
    """File upload CRUD operations"""
    
    @staticmethod
    def upload_file(db: Session, file: UploadFile, uploaded_by: str) -> FileUploadResponse:
        """Upload file to Azure and save metadata to database"""
        try:
            # Generate unique file ID
            file_id = generate_file_id()
            
            # Check for duplicate file_id (very unlikely but safety check)
            existing_file = db.query(FileSchema).filter(FileSchema.file_id == file_id).first()
            while existing_file:
                file_id = generate_file_id()
                existing_file = db.query(FileSchema).filter(FileSchema.file_id == file_id).first()
            
            # Get file content
            file_content = file.file
            original_filename = file.filename or "unknown"
            content_type = file.content_type or "application/octet-stream"
            
            # Get file size
            file_content.seek(0, 2)  # Seek to end
            file_size = file_content.tell()
            file_content.seek(0)  # Reset to beginning
            
            # Upload to Azure
            file_url = azure_client.upload_file(
                file_content=file_content,
                filename=f"{file_id}_{original_filename}",  # Prefix with file_id for uniqueness
                uploaded_by=uploaded_by,
                content_type=content_type
            )
            
            # Create file schema object
            db_file = FileSchema(
                file_id=file_id,
                original_filename=original_filename,
                file_size=file_size,
                content_type=content_type,
                file_url=file_url,
                uploaded_by=uploaded_by,
                status=FileStatus.ACTIVE
            )
            
            # Save to database
            db.add(db_file)
            db.commit()
            db.refresh(db_file)
            
            # Convert to response
            return FileUploadResponse(
                file_id=db_file.file_id,
                file_url=db_file.file_url,
                original_filename=db_file.original_filename,
                file_size=db_file.file_size,
                content_type=db_file.content_type,
                upload_timestamp=db_file.upload_timestamp
            )
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    @staticmethod
    def get_file_by_id(db: Session, file_id: str) -> Optional[FileResponse]:
        """Get file by ID"""
        db_file = db.query(FileSchema).filter(
            FileSchema.file_id == file_id,
            FileSchema.status == FileStatus.ACTIVE
        ).first()
        
        if not db_file:
            return None
            
        return FileResponse(
            file_id=db_file.file_id,
            original_filename=db_file.original_filename,
            file_size=db_file.file_size,
            content_type=db_file.content_type,
            file_url=db_file.file_url,
            uploaded_by=db_file.uploaded_by,
            status=db_file.status,
            upload_timestamp=db_file.upload_timestamp
        )
    
    @staticmethod
    def get_all_files(db: Session, skip: int = 0, limit: int = 100) -> FileListResponse:
        """Get all files with pagination"""
        # Get total count
        total = db.query(FileSchema).filter(FileSchema.status == FileStatus.ACTIVE).count()
        
        # Get files
        db_files = (db.query(FileSchema)
                   .filter(FileSchema.status == FileStatus.ACTIVE)
                   .order_by(FileSchema.upload_timestamp.desc())
                   .offset(skip)
                   .limit(limit)
                   .all())
        
        files = [
            FileResponse(
                file_id=file.file_id,
                original_filename=file.original_filename,
                file_size=file.file_size,
                content_type=file.content_type,
                file_url=file.file_url,
                uploaded_by=file.uploaded_by,
                status=file.status,
                upload_timestamp=file.upload_timestamp
            )
            for file in db_files
        ]
        
        return FileListResponse(
            files=files,
            total=total,
            skip=skip,
            limit=limit
        )
    
    @staticmethod
    def delete_file(db: Session, file_id: str) -> bool:
        """Delete file (soft delete in DB, hard delete from Azure)"""
        db_file = db.query(FileSchema).filter(
            FileSchema.file_id == file_id,
            FileSchema.status == FileStatus.ACTIVE
        ).first()
        
        if not db_file:
            return False
        
        try:
            # Delete from Azure Blob Storage
            azure_client.delete_file(db_file.file_url)
            
            # Soft delete in database
            db_file.status = FileStatus.DELETED
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
    
    @staticmethod
    def get_files_count(db: Session) -> int:
        """Get total active files count"""
        return db.query(FileSchema).filter(FileSchema.status == FileStatus.ACTIVE).count()
    
    @staticmethod
    def get_file_url_by_id(db: Session, file_id: str) -> Optional[str]:
        """Get file URL by file ID (helper method for issues)"""
        db_file = db.query(FileSchema).filter(
            FileSchema.file_id == file_id,
            FileSchema.status == FileStatus.ACTIVE
        ).first()
        
        return db_file.file_url if db_file else None