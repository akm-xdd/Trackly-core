from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException

from app.schemas.issue_schema import IssueSchema
from app.models.issue import IssueCreate, IssueUpdate, IssueResponse, IssueStatus


class IssueService:
    """Issue CRUD operations"""
    
    @staticmethod
    def create_issue(db: Session, issue_data: IssueCreate, created_by: str) -> IssueResponse:
        """Create new issue"""
        try:
            # Create issue schema object
            db_issue = IssueSchema(
                title=issue_data.title,
                description=issue_data.description,
                severity=issue_data.severity,
                created_by=created_by,
                file_url=issue_data.file_url
            )
            
            # Save to database
            db.add(db_issue)
            db.commit()
            db.refresh(db_issue)
            
            # Convert to response
            return IssueResponse(
                id=db_issue.id,
                title=db_issue.title,
                description=db_issue.description,
                severity=db_issue.severity,
                status=db_issue.status,
                created_by=db_issue.created_by,
                updated_by=db_issue.updated_by,
                file_url=db_issue.file_url,
                created_at=db_issue.created_at,
                updated_at=db_issue.updated_at
            )
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create issue: {str(e)}")
    
    @staticmethod
    def get_issue_by_id(db: Session, issue_id: str) -> Optional[IssueResponse]:
        """Get issue by ID"""
        db_issue = db.query(IssueSchema).filter(IssueSchema.id == issue_id).first()
        
        if not db_issue:
            return None
            
        return IssueResponse(
            id=db_issue.id,
            title=db_issue.title,
            description=db_issue.description,
            severity=db_issue.severity,
            status=db_issue.status,
            created_by=db_issue.created_by,
            updated_by=db_issue.updated_by,
            file_url=db_issue.file_url,
            created_at=db_issue.created_at,
            updated_at=db_issue.updated_at
        )
    
    @staticmethod
    def get_all_issues(db: Session, skip: int = 0, limit: int = 100) -> List[IssueResponse]:
        """Get all issues with pagination"""
        db_issues = db.query(IssueSchema).order_by(IssueSchema.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            IssueResponse(
                id=issue.id,
                title=issue.title,
                description=issue.description,
                severity=issue.severity,
                status=issue.status,
                created_by=issue.created_by,
                updated_by=issue.updated_by,
                file_url=issue.file_url,
                created_at=issue.created_at,
                updated_at=issue.updated_at
            )
            for issue in db_issues
        ]
    
    @staticmethod
    def get_issues_by_user(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[IssueResponse]:
        """Get issues created by specific user"""
        db_issues = (db.query(IssueSchema)
                    .filter(IssueSchema.created_by == user_id)
                    .order_by(IssueSchema.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                    .all())
        
        return [
            IssueResponse(
                id=issue.id,
                title=issue.title,
                description=issue.description,
                severity=issue.severity,
                status=issue.status,
                created_by=issue.created_by,
                updated_by=issue.updated_by,
                file_url=issue.file_url,
                created_at=issue.created_at,
                updated_at=issue.updated_at
            )
            for issue in db_issues
        ]
    
    @staticmethod
    def get_issues_by_status(db: Session, status: IssueStatus, skip: int = 0, limit: int = 100) -> List[IssueResponse]:
        """Get issues by status"""
        db_issues = (db.query(IssueSchema)
                    .filter(IssueSchema.status == status)
                    .order_by(IssueSchema.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                    .all())
        
        return [
            IssueResponse(
                id=issue.id,
                title=issue.title,
                description=issue.description,
                severity=issue.severity,
                status=issue.status,
                created_by=issue.created_by,
                updated_by=issue.updated_by,
                file_url=issue.file_url,
                created_at=issue.created_at,
                updated_at=issue.updated_at
            )
            for issue in db_issues
        ]
    
    @staticmethod
    def update_issue(db: Session, issue_id: str, issue_data: IssueUpdate, updated_by: str) -> Optional[IssueResponse]:
        """Update issue"""
        db_issue = db.query(IssueSchema).filter(IssueSchema.id == issue_id).first()
        
        if not db_issue:
            return None
        
        try:
            # Update only provided fields
            if issue_data.title is not None:
                db_issue.title = issue_data.title
            if issue_data.description is not None:
                db_issue.description = issue_data.description
            if issue_data.severity is not None:
                db_issue.severity = issue_data.severity
            if issue_data.status is not None:
                db_issue.status = issue_data.status
            if issue_data.file_url is not None:
                db_issue.file_url = issue_data.file_url
            
            # Always update the updated_by field
            db_issue.updated_by = updated_by
            
            db.commit()
            db.refresh(db_issue)
            
            return IssueResponse(
                id=db_issue.id,
                title=db_issue.title,
                description=db_issue.description,
                severity=db_issue.severity,
                status=db_issue.status,
                created_by=db_issue.created_by,
                updated_by=db_issue.updated_by,
                file_url=db_issue.file_url,
                created_at=db_issue.created_at,
                updated_at=db_issue.updated_at
            )
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update issue: {str(e)}")
    
    @staticmethod
    def delete_issue(db: Session, issue_id: str) -> bool:
        """Delete issue"""
        db_issue = db.query(IssueSchema).filter(IssueSchema.id == issue_id).first()
        
        if not db_issue:
            return False
        
        try:
            db.delete(db_issue)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete issue: {str(e)}")
    
    @staticmethod
    def get_issues_count(db: Session) -> int:
        """Get total issues count"""
        return db.query(IssueSchema).count()
    
    @staticmethod
    def get_issues_count_by_status(db: Session) -> dict:
        """Get issues count grouped by status"""
        from sqlalchemy import func
        
        result = (db.query(IssueSchema.status, func.count(IssueSchema.id))
                 .group_by(IssueSchema.status)
                 .all())
        
        return {status.value: count for status, count in result}
    
    @staticmethod
    def get_issues_count_by_severity(db: Session) -> dict:
        """Get issues count grouped by severity"""
        from sqlalchemy import func
        
        result = (db.query(IssueSchema.severity, func.count(IssueSchema.id))
                 .group_by(IssueSchema.severity)
                 .all())
        
        return {severity.value: count for severity, count in result}