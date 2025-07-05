from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.databases.postgres import get_db
from app.models.issue import IssueCreate, IssueUpdate, IssueResponse, IssueStatus, IssueSeverity
from app.services.issues.service import IssueService

router = APIRouter(prefix="/issues", tags=["issues"])


@router.post("/", response_model=IssueResponse)
def create_issue(
    issue_data: IssueCreate, 
    created_by: str = Query(..., description="User ID who creates the issue"),
    db: Session = Depends(get_db)
):
    """Create a new issue"""
    return IssueService.create_issue(db, issue_data, created_by)


@router.get("/", response_model=List[IssueResponse])
def get_issues(
    skip: int = Query(0, ge=0, description="Number of issues to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of issues to return"),
    status: Optional[IssueStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get all issues with optional status filter"""
    if status:
        return IssueService.get_issues_by_status(db, status, skip=skip, limit=limit)
    return IssueService.get_all_issues(db, skip=skip, limit=limit)


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(issue_id: str, db: Session = Depends(get_db)):
    """Get issue by ID"""
    issue = IssueService.get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.put("/{issue_id}", response_model=IssueResponse)
def update_issue(
    issue_id: str, 
    issue_data: IssueUpdate, 
    updated_by: str = Query(..., description="User ID who is updating the issue"),
    db: Session = Depends(get_db)
):
    """Update issue"""
    issue = IssueService.update_issue(db, issue_id, issue_data, updated_by)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.delete("/{issue_id}")
def delete_issue(issue_id: str, db: Session = Depends(get_db)):
    """Delete issue"""
    success = IssueService.delete_issue(db, issue_id)
    if not success:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"message": "Issue deleted successfully"}


@router.get("/user/{user_id}", response_model=List[IssueResponse])
def get_user_issues(
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of issues to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of issues to return"),
    db: Session = Depends(get_db)
):
    """Get issues created by specific user"""
    return IssueService.get_issues_by_user(db, user_id, skip=skip, limit=limit)


@router.get("/stats/count")
def get_issues_count(db: Session = Depends(get_db)):
    """Get total issues count"""
    count = IssueService.get_issues_count(db)
    return {"total_issues": count}


@router.get("/stats/by-status")
def get_issues_by_status_stats(db: Session = Depends(get_db)):
    """Get issues count grouped by status"""
    stats = IssueService.get_issues_count_by_status(db)
    return {"issues_by_status": stats}


@router.get("/stats/by-severity")
def get_issues_by_severity_stats(db: Session = Depends(get_db)):
    """Get issues count grouped by severity"""
    stats = IssueService.get_issues_count_by_severity(db)
    return {"issues_by_severity": stats}