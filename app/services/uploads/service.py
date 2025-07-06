from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, BinaryIO
from fastapi import HTTPException, UploadFile

from app.schemas.file_schema import FileSchema
from app.schemas.user_schema import UserSchema
from app.models.uploads import FileResponse, FileUploadResponse, FileListResponse, FileStatus
from app.utils.file_id import generate_file_id
from app.databases.azure_blob import azure_client


class UploadService:
    
    @staticmethod
    def upload_file(db: Session, file: UploadFile, uploaded_by: str) -> FileUploadResponse:
        try:
            file_id = generate_file_id()
            
            existing_file = db.query(FileSchema).filter(FileSchema.file_id == file_id).first()
            while existing_file:
                file_id = generate_file_id()
                existing_file = db.query(FileSchema).filter(FileSchema.file_id == file_id).first()
            
            file_content = file.file
            original_filename = file.filename or "unknown"
            content_type = file.content_type or "application/octet-stream"
            
            file_content.seek(0, 2)
            file_size = file_content.tell()
            file_content.seek(0)
            
            file_url = azure_client.upload_file(
                file_content=file_content,
                filename=f"{file_id}_{original_filename}",
                uploaded_by=uploaded_by,
                content_type=content_type
            )
            
            db_file = FileSchema(
                file_id=file_id,
                original_filename=original_filename,
                file_size=file_size,
                content_type=content_type,
                file_url=file_url,
                uploaded_by=uploaded_by,
                status=FileStatus.ACTIVE
            )
            
            db.add(db_file)
            db.commit()
            db.refresh(db_file)
            
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
        result = (db.query(FileSchema, UserSchema.full_name.label('uploader_name'))
                  .join(UserSchema, FileSchema.uploaded_by == UserSchema.id)
                  .filter(FileSchema.file_id == file_id, FileSchema.status == FileStatus.ACTIVE)
                  .first())
        
        if not result:
            return None
            
        db_file, uploader_name = result
        
        return FileResponse(
            file_id=db_file.file_id,
            original_filename=db_file.original_filename,
            file_size=db_file.file_size,
            content_type=db_file.content_type,
            file_url=db_file.file_url,
            uploaded_by=db_file.uploaded_by,
            uploaded_by_name=uploader_name,
            status=db_file.status,
            upload_timestamp=db_file.upload_timestamp
        )
    
    @staticmethod
    def get_all_files(db: Session, skip: int = 0, limit: int = 100) -> FileListResponse:
        total = db.query(FileSchema).filter(FileSchema.status == FileStatus.ACTIVE).count()
        
        db_files = (db.query(FileSchema, UserSchema.full_name.label('uploader_name'))
                   .join(UserSchema, FileSchema.uploaded_by == UserSchema.id)
                   .filter(FileSchema.status == FileStatus.ACTIVE)
                   .order_by(FileSchema.upload_timestamp.desc())
                   .offset(skip)
                   .limit(limit)
                   .all())
        
        files = [
            FileResponse(
                file_id=row[0].file_id,
                original_filename=row[0].original_filename,
                file_size=row[0].file_size,
                content_type=row[0].content_type,
                file_url=row[0].file_url,
                uploaded_by=row[0].uploaded_by,
                uploaded_by_name=row[1],
                status=row[0].status,
                upload_timestamp=row[0].upload_timestamp
            )
            for row in db_files
        ]
        
        return FileListResponse(
            files=files,
            total=total,
            skip=skip,
            limit=limit
        )
    
    @staticmethod
    def delete_file(db: Session, file_id: str) -> bool:
        db_file = db.query(FileSchema).filter(
            FileSchema.file_id == file_id,
            FileSchema.status == FileStatus.ACTIVE
        ).first()
        
        if not db_file:
            return False
        
        try:
            azure_client.delete_file(db_file.file_url)
            db_file.status = FileStatus.DELETED
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
    
    @staticmethod
    def get_files_count(db: Session) -> int:
        return db.query(FileSchema).filter(FileSchema.status == FileStatus.ACTIVE).count()
    
    @staticmethod
    def get_file_url_by_id(db: Session, file_id: str) -> Optional[str]:
        db_file = db.query(FileSchema).filter(
            FileSchema.file_id == file_id,
            FileSchema.status == FileStatus.ACTIVE
        ).first()
        
        return db_file.file_url if db_file else None