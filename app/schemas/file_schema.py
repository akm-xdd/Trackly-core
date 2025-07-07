from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum
from sqlalchemy.sql import func
from app.databases.postgres import Base
from app.models.uploads import FileStatus
import uuid


class FileSchema(Base):
    """File table schema"""
    __tablename__ = "files"

    file_id = Column(String, primary_key=True)
    original_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    uploaded_by = Column(String, nullable=False)
    status = Column(
        SQLEnum(FileStatus),
        nullable=False,
        default=FileStatus.ACTIVE)
    upload_timestamp = Column(
        DateTime(
            timezone=True),
        server_default=func.now())

    def __repr__(self):
        return f"<File(file_id={self.file_id}, filename={self.original_filename}, status={self.status})>"
