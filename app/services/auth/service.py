from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from typing import Optional
from datetime import timedelta

from app.schemas.user_schema import UserSchema
from app.models.auth import LoginRequest, SignupRequest, LoginResponse, TokenResponse, RefreshResponse
from app.models.user import UserResponse, UserCreate
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.utils.metrics import track_login_attempt

class AuthService:
    """Authentication service"""

    @staticmethod
    def signup(db: Session, signup_data: SignupRequest) -> LoginResponse:
        """Register a new user and return login response"""
        try:
            # Hash the password
            hashed_password = hash_password(signup_data.password)

            # Create user in database
            db_user = UserSchema(
                email=signup_data.email,
                password=hashed_password,
                full_name=signup_data.full_name,
                role=signup_data.role
            )

            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            # Create tokens
            token_data = {
                "sub": db_user.id,
                "email": db_user.email,
                "role": db_user.role.value
            }

            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token({"sub": db_user.id})

            # Prepare response
            user_response = UserResponse(
                id=db_user.id,
                email=db_user.email,
                full_name=db_user.full_name,
                role=db_user.role,
                created_at=db_user.created_at
            )

            tokens = TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )

            return LoginResponse(user=user_response, tokens=tokens)

        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Email already registered")
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Registration failed: {str(e)}")

    @staticmethod
    def login(db: Session, login_data: LoginRequest) -> LoginResponse:
        """Authenticate user and return login response"""
        # Find user by email
        db_user = db.query(UserSchema).filter(
            UserSchema.email == login_data.email).first()

        if not db_user:
            track_login_attempt(success=False, method='password')
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password")

        # Verify password
        if not verify_password(login_data.password, db_user.password):
            track_login_attempt(success=False, method='password')
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password")

        # Create tokens
        token_data = {
            "sub": db_user.id,
            "email": db_user.email,
            "role": db_user.role.value
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": db_user.id})

        # Prepare response
        user_response = UserResponse(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            created_at=db_user.created_at
        )

        tokens = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        track_login_attempt(success=True, method='password')


        return LoginResponse(user=user_response, tokens=tokens)

    @staticmethod
    def refresh_access_token(db: Session,
                             refresh_token: str) -> RefreshResponse:
        """Generate new access token using refresh token"""
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token")

        # Get user from database
        db_user = db.query(UserSchema).filter(UserSchema.id == user_id).first()
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found")

        # Create new access token
        token_data = {
            "sub": db_user.id,
            "email": db_user.email,
            "role": db_user.role.value
        }

        access_token = create_access_token(token_data)

        return RefreshResponse(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    @staticmethod
    def get_current_user(db: Session, user_id: str) -> Optional[UserResponse]:
        """Get current user by ID"""
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
