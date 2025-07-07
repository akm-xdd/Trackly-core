from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.databases.postgres import get_db
from app.models.issue import IssueCreate, IssueUpdate, IssueResponse, IssueStatus, IssueSeverity
from app.services.issues.service import IssueService
from app.middlewares.auth import (
    require_admin,
    require_maintainer_or_admin,
    require_any_role,
    get_current_user_required,
    can_access_issue_resource,
    can_modify_issue,
    can_delete_issue
)
from app.models.user import UserResponse, UserRole

import asyncio
import json
from fastapi.responses import StreamingResponse
from app.services.events import broadcaster
from app.models.events import IssueEvent, EventType

router = APIRouter(prefix="/issues", tags=["issues"])


@router.post("/", response_model=IssueResponse)
async def create_issue(
    issue_data: IssueCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Create a new issue (Any authenticated user)"""
    # All users can create issues, but they are automatically the creator
    return IssueService.create_issue(db, issue_data, current_user.id)


@router.get("/", response_model=List[IssueResponse])
async def get_issues(
    skip: int = Query(0, ge=0, description="Number of issues to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Number of issues to return"),
    status: Optional[IssueStatus] = Query(
        None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get issues with role-based filtering"""
    if status:
        all_issues = IssueService.get_issues_by_status(
            db, status, skip=skip, limit=limit)
    else:
        all_issues = IssueService.get_all_issues(db, skip=skip, limit=limit)

    # REPORTER can only see their own issues
    if current_user.role == UserRole.REPORTER:
        filtered_issues = [
            issue for issue in all_issues
            if issue.created_by == current_user.id
        ]
        return filtered_issues

    # MAINTAINER and ADMIN can see all issues
    return all_issues


@router.get("/events")
async def issue_events_stream(
    token: str = Query(..., description="JWT token for authentication")
):
    """Server-Sent Events stream for real-time issue updates (ADMIN only)"""
    
    # Manually verify token since EventSource doesn't support headers
    from app.utils.auth import verify_token
    from app.services.auth.service import AuthService
    from app.databases.postgres import SessionLocal
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    
    # Get user and verify ADMIN role
    db = SessionLocal()
    try:
        current_user = AuthService.get_current_user(db, user_id)
        if not current_user:
            raise HTTPException(status_code=401, detail="User not found")
    finally:
        db.close()
    
    async def event_stream():
        queue = await broadcaster.connect()
        try:
            # Send initial connection confirmation
            initial_event = {
                "type": "connected",
                "message": f"Connected as {current_user.role.value}",
                "timestamp": datetime.utcnow().isoformat(),
                "user_role": current_user.role.value
            }
            yield f"data: {json.dumps(initial_event)}\n\n"
            
            # Stream all events (no filtering needed since ADMIN-only)
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    try:

                        event_data = json.loads(message.replace("data: ", "").strip())
                        if should_send_event_to_user(event_data, current_user):
                            
                            yield message
                        
                    except json.JSONDecodeError:
                        yield message
                except asyncio.TimeoutError:
                    # Send heartbeat
                    heartbeat = {
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(heartbeat)}\n\n"
                except Exception:
                    break
        finally:
            broadcaster.disconnect(queue)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


def should_send_event_to_user(event_data: dict, user: UserResponse) -> bool:
    """Check if user should receive this event based on RBAC rules"""
    
    # System events (connected, heartbeat) - send to everyone
    if event_data.get("type") in ["connected", "heartbeat"]:
        return True
    
    # ADMIN and MAINTAINER can see all issue events
    if user.role in [UserRole.ADMIN, UserRole.MAINTAINER]:
        return True
    
    # REPORTER can only see events for issues they created
    if user.role == UserRole.REPORTER:
        # Check if this is their issue
        issue_data = event_data.get("data", {})
        created_by = issue_data.get("created_by")
        
        # For create/update events, check created_by field
        if created_by == user.id:
            return True
            
        # For delete events, check if they were the one who deleted it
        if event_data.get("type") == "issue_deleted":
            if event_data.get("user_id") == user.id:
                return True
    
    return False


@router.get("/events/stats")
async def get_sse_stats(
    current_user: UserResponse = Depends(require_admin)
):
    """Get SSE connection statistics (ADMIN only)"""
    return {
        "active_connections": broadcaster.get_connection_count(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(
    issue_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get issue by ID with role-based access control"""
    issue = IssueService.get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Check if user can access this issue
    if not can_access_issue_resource(current_user, issue.created_by):
        raise HTTPException(
            status_code=403, detail="Access denied to this issue")

    return issue


@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: str,
    issue_data: IssueUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Update issue with role-based permissions"""
    # First check if issue exists
    existing_issue = IssueService.get_issue_by_id(db, issue_id)
    if not existing_issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Check if user can modify this issue
    if not can_modify_issue(current_user, existing_issue.created_by):
        raise HTTPException(
            status_code=403, detail="Access denied to modify this issue")

    # REPORTER can only modify title and description of their own issues
    if current_user.role == UserRole.REPORTER:
        # Prevent REPORTER from changing status or severity
        if issue_data.status is not None or issue_data.severity is not None:
            raise HTTPException(
                status_code=403,
                detail="Reporters can only update title and description of their own issues"
            )

    issue = IssueService.update_issue(
        db, issue_id, issue_data, current_user.id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.delete("/{issue_id}")
async def delete_issue(
    issue_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Delete issue with role-based permissions"""
    # First check if issue exists
    existing_issue = IssueService.get_issue_by_id(db, issue_id)
    if not existing_issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Check if user can delete this issue
    if not can_delete_issue(current_user, existing_issue.created_by):
        raise HTTPException(
            status_code=403,
            detail="Only admins or issue creators can delete issues"
        )

    success = IssueService.delete_issue(db, issue_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"message": "Issue deleted successfully"}


@router.get("/user/{user_id}", response_model=List[IssueResponse])
async def get_user_issues(
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of issues to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Number of issues to return"),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get issues created by specific user"""
    # REPORTER can only see their own issues
    if current_user.role == UserRole.REPORTER and current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="Reporters can only view their own issues")

    return IssueService.get_issues_by_user(db, user_id, skip=skip, limit=limit)


@router.get("/stats/count")
async def get_issues_count(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get total issues count (role-based)"""
    count = IssueService.get_issues_count(
        db, 
        user_id=current_user.id, 
        user_role=current_user.role.value
    )
    return {"total_issues": count}


@router.get("/stats/by-status")
async def get_issues_by_status_stats(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get issues count grouped by status (role-based)"""
    stats = IssueService.get_issues_count_by_status(
        db, 
        user_id=current_user.id, 
        user_role=current_user.role.value
    )
    return {"issues_by_status": stats}


@router.get("/stats/by-severity")
async def get_issues_by_severity_stats(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_any_role)
):
    """Get issues count grouped by severity (role-based)"""
    stats = IssueService.get_issues_count_by_severity(
        db, 
        user_id=current_user.id, 
        user_role=current_user.role.value
    )
    return {"issues_by_severity": stats}
