from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from fastapi import HTTPException

from app.schemas.user_schema import UserSchema
from app.models.user import User, UserCreate, UserUpdate, UserResponse
from app.utils.auth import hash_password


class UserService:
    """User CRUD operations"""
    
    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> UserResponse:
        """Create new user"""
        try:
            
            hashed_password = hash_password(user_data.password)  

            # Create user schema object
            db_user = UserSchema(
                email=user_data.email,
                password=hashed_password,
                full_name=user_data.full_name,
                role=user_data.role
            )
            
            # Save to database
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            # Convert to response
            return UserResponse(
                id=db_user.id,
                email=db_user.email,
                full_name=db_user.full_name,
                role=db_user.role,
                created_at=db_user.created_at
            )
            
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Email already exists")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[UserResponse]:
        """Get user by ID"""
        db_user = db.query(UserSchema).filter(UserSchema.id == user_id).first()
        
        if not db_user:
            return None
            
        return UserResponse(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            created_at=db_user.created_at
        )
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[UserResponse]:
        """Get user by email"""
        db_user = db.query(UserSchema).filter(UserSchema.email == email).first()
        
        if not db_user:
            return None
            
        return UserResponse(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            created_at=db_user.created_at
        )
    
    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """Get all users with pagination"""
        db_users = db.query(UserSchema).offset(skip).limit(limit).all()
        
        return [
            UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                created_at=user.created_at
            )
            for user in db_users
        ]
    
    @staticmethod
    def update_user(db: Session, user_id: str, user_data: UserUpdate) -> Optional[UserResponse]:
        """Update user"""
        db_user = db.query(UserSchema).filter(UserSchema.id == user_id).first()
        
        if not db_user:
            return None
        
        try:
            # Update only provided fields
            if user_data.full_name is not None:
                db_user.full_name = user_data.full_name
            if user_data.role is not None:
                db_user.role = user_data.role
            
            db.commit()
            db.refresh(db_user)
            
            return UserResponse(
                id=db_user.id,
                email=db_user.email,
                full_name=db_user.full_name,
                role=db_user.role,
                created_at=db_user.created_at
            )
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")
    
    @staticmethod
    def delete_user(db: Session, user_id: str) -> bool:
        """Delete user"""
        db_user = db.query(UserSchema).filter(UserSchema.id == user_id).first()
        
        if not db_user:
            return False
        
        try:
            db.delete(db_user)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")
    
    @staticmethod
    def get_users_count(db: Session) -> int:
        """Get total users count"""
        return db.query(UserSchema).count()