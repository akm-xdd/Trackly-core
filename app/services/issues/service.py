from sqlalchemy.orm import Session, aliased
from typing import List, Optional
from fastapi import HTTPException
from datetime import datetime
import asyncio
from app.services.events import broadcaster
from app.models.events import IssueEvent, EventType
from app.schemas.issue_schema import IssueSchema
from app.schemas.user_schema import UserSchema
from app.models.issue import IssueCreate, IssueUpdate, IssueResponse, IssueStatus


class IssueService:

    @staticmethod
    def create_issue(db: Session, issue_data: IssueCreate, created_by: str) -> IssueResponse:
        try:
            db_issue = IssueSchema(
                title=issue_data.title,
                description=issue_data.description,
                severity=issue_data.severity,
                created_by=created_by,
                file_url=issue_data.file_url
            )

            db.add(db_issue)
            db.commit()
            db.refresh(db_issue)

            creator = db.query(UserSchema).filter(
                UserSchema.id == created_by).first()

            response = IssueResponse(
                id=db_issue.id,
                title=db_issue.title,
                description=db_issue.description,
                severity=db_issue.severity,
                status=db_issue.status,
                created_by=db_issue.created_by,
                created_by_name=creator.full_name if creator else None,
                updated_by=db_issue.updated_by,
                updated_by_name=None,
                file_url=db_issue.file_url,
                created_at=db_issue.created_at,
                updated_at=db_issue.updated_at
            )

            asyncio.create_task(
                broadcaster.broadcast_issue_event(
                    IssueEvent(
                        event_type=EventType.ISSUE_CREATED,
                        issue_id=db_issue.id,
                        user_id=created_by,
                        user_name=creator.full_name if creator else None,
                        timestamp=datetime.utcnow(),
                        data=response.dict()
                    )
                )
            )

            return response

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to create issue: {str(e)}")

    @staticmethod
    def get_issue_by_id(db: Session, issue_id: str) -> Optional[IssueResponse]:
        creator = aliased(UserSchema)
        updater = aliased(UserSchema)

        result = (db.query(
            IssueSchema,
            creator.full_name.label('creator_name'),
            updater.full_name.label('updater_name')
        )
            .join(creator, IssueSchema.created_by == creator.id)
            .outerjoin(updater, IssueSchema.updated_by == updater.id)
            .filter(IssueSchema.id == issue_id)
            .first())

        if not result:
            return None

        issue, creator_name, updater_name = result

        return IssueResponse(
            id=issue.id,
            title=issue.title,
            description=issue.description,
            severity=issue.severity,
            status=issue.status,
            created_by=issue.created_by,
            created_by_name=creator_name,
            updated_by=issue.updated_by,
            updated_by_name=updater_name,
            file_url=issue.file_url,
            created_at=issue.created_at,
            updated_at=issue.updated_at
        )

    @staticmethod
    def get_all_issues(db: Session, skip: int = 0, limit: int = 100) -> List[IssueResponse]:
        creator = aliased(UserSchema)
        updater = aliased(UserSchema)

        db_issues = (db.query(
            IssueSchema,
            creator.full_name.label('creator_name'),
            updater.full_name.label('updater_name')
        )
            .join(creator, IssueSchema.created_by == creator.id)
            .outerjoin(updater, IssueSchema.updated_by == updater.id)
            .order_by(IssueSchema.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all())

        return [
            IssueResponse(
                id=row[0].id,
                title=row[0].title,
                description=row[0].description,
                severity=row[0].severity,
                status=row[0].status,
                created_by=row[0].created_by,
                created_by_name=row[1],
                updated_by=row[0].updated_by,
                updated_by_name=row[2],
                file_url=row[0].file_url,
                created_at=row[0].created_at,
                updated_at=row[0].updated_at
            )
            for row in db_issues
        ]

    @staticmethod
    def get_issues_by_user(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[IssueResponse]:
        creator = aliased(UserSchema)
        updater = aliased(UserSchema)

        db_issues = (db.query(
            IssueSchema,
            creator.full_name.label('creator_name'),
            updater.full_name.label('updater_name')
        )
            .join(creator, IssueSchema.created_by == creator.id)
            .outerjoin(updater, IssueSchema.updated_by == updater.id)
            .filter(IssueSchema.created_by == user_id)
            .order_by(IssueSchema.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all())

        return [
            IssueResponse(
                id=row[0].id,
                title=row[0].title,
                description=row[0].description,
                severity=row[0].severity,
                status=row[0].status,
                created_by=row[0].created_by,
                created_by_name=row[1],
                updated_by=row[0].updated_by,
                updated_by_name=row[2],
                file_url=row[0].file_url,
                created_at=row[0].created_at,
                updated_at=row[0].updated_at
            )
            for row in db_issues
        ]

    @staticmethod
    def get_issues_by_status(db: Session, status: IssueStatus, skip: int = 0, limit: int = 100) -> List[IssueResponse]:
        creator = aliased(UserSchema)
        updater = aliased(UserSchema)

        db_issues = (db.query(
            IssueSchema,
            creator.full_name.label('creator_name'),
            updater.full_name.label('updater_name')
        )
            .join(creator, IssueSchema.created_by == creator.id)
            .outerjoin(updater, IssueSchema.updated_by == updater.id)
            .filter(IssueSchema.status == status)
            .order_by(IssueSchema.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all())

        return [
            IssueResponse(
                id=row[0].id,
                title=row[0].title,
                description=row[0].description,
                severity=row[0].severity,
                status=row[0].status,
                created_by=row[0].created_by,
                created_by_name=row[1],
                updated_by=row[0].updated_by,
                updated_by_name=row[2],
                file_url=row[0].file_url,
                created_at=row[0].created_at,
                updated_at=row[0].updated_at
            )
            for row in db_issues
        ]

    @staticmethod
    def update_issue(db: Session, issue_id: str, issue_data: IssueUpdate, updated_by: str) -> Optional[IssueResponse]:
        db_issue = db.query(IssueSchema).filter(
            IssueSchema.id == issue_id).first()

        if not db_issue:
            return None

        try:
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

            db_issue.updated_by = updated_by

            db.commit()
            db.refresh(db_issue)

            creator = db.query(UserSchema).filter(
                UserSchema.id == db_issue.created_by).first()
            updater = db.query(UserSchema).filter(
                UserSchema.id == updated_by).first()

            response = IssueResponse(
                id=db_issue.id,
                title=db_issue.title,
                description=db_issue.description,
                severity=db_issue.severity,
                status=db_issue.status,
                created_by=db_issue.created_by,
                created_by_name=creator.full_name if creator else None,
                updated_by=db_issue.updated_by,
                updated_by_name=updater.full_name if updater else None,
                file_url=db_issue.file_url,
                created_at=db_issue.created_at,
                updated_at=db_issue.updated_at
            )

            asyncio.create_task(
                broadcaster.broadcast_issue_event(
                    IssueEvent(
                        event_type=EventType.ISSUE_UPDATED,
                        issue_id=db_issue.id,
                        user_id=updated_by,
                        user_name=updater.full_name if updater else None,
                        timestamp=datetime.utcnow(),
                        data=response.dict()
                    )
                )
            )

            return response

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to update issue: {str(e)}")

    @staticmethod
    def delete_issue(db: Session, issue_id: str, deleted_by: str = None) -> bool:
        db_issue = db.query(IssueSchema).filter(
            IssueSchema.id == issue_id).first()

        if not db_issue:
            return False

        try:
            creator = db.query(UserSchema).filter(
                UserSchema.id == db_issue.created_by).first()

            issue_data = {
                "id": db_issue.id,
                "title": db_issue.title,
                "created_by": db_issue.created_by,
                "created_by_name": creator.full_name if creator else None
            }

            db.delete(db_issue)
            db.commit()

            if deleted_by:
                deleter = db.query(UserSchema).filter(
                    UserSchema.id == deleted_by).first()
                asyncio.create_task(
                    broadcaster.broadcast_issue_event(
                        IssueEvent(
                            event_type=EventType.ISSUE_DELETED,
                            issue_id=issue_id,
                            user_id=deleted_by,
                            user_name=deleter.full_name if deleter else None,
                            timestamp=datetime.utcnow(),
                            data=issue_data
                        )
                    )
                )

            return True
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to delete issue: {str(e)}")
    

    @staticmethod
    def get_issues_count(db: Session, user_id: str = None, user_role: str = None) -> int:
        """Get total issues count with role-based filtering"""
        query = db.query(IssueSchema)
        
        if user_role == "REPORTER" and user_id:
            query = query.filter(IssueSchema.created_by == user_id)
        
        return query.count()

    @staticmethod
    def get_issues_count_by_status(db: Session, user_id: str = None, user_role: str = None) -> dict:
        """Get issues count grouped by status with role-based filtering"""
        from sqlalchemy import func

        query = db.query(IssueSchema.status, func.count(IssueSchema.id))
        
        if user_role == "REPORTER" and user_id:
            query = query.filter(IssueSchema.created_by == user_id)
        
        result = query.group_by(IssueSchema.status).all()
        return {status.value: count for status, count in result}

    @staticmethod
    def get_issues_count_by_severity(db: Session, user_id: str = None, user_role: str = None) -> dict:
        """Get issues count grouped by severity with role-based filtering"""
        from sqlalchemy import func

        query = db.query(IssueSchema.severity, func.count(IssueSchema.id))
        
        if user_role == "REPORTER" and user_id:
            query = query.filter(IssueSchema.created_by == user_id)
        
        result = query.group_by(IssueSchema.severity).all()
        return {severity.value: count for severity, count in result}