from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests

from app.databases.postgres import get_db
from app.models.auth import (
    LoginRequest, 
    SignupRequest, 
    RefreshTokenRequest,
    LoginResponse, 
    RefreshResponse
)
from app.models.user import UserResponse
from app.services.auth.service import AuthService
from app.middlewares.auth import get_current_user_required
from app.models.auth import (
    GoogleLoginRequest, 
    TokenResponse
)
from app.utils.auth import create_access_token, create_refresh_token
from app.schemas.user_schema import UserSchema

router = APIRouter(prefix="/auth", tags=["authentication"])
import os
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  


@router.post("/signup", response_model=LoginResponse)
def signup(
    signup_data: SignupRequest, 
    db: Session = Depends(get_db)
):
    """Register a new user"""
    return AuthService.signup(db, signup_data)


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest, 
    db: Session = Depends(get_db)
):
    """Login with email and password"""
    return AuthService.login(db, login_data)


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    return AuthService.refresh_access_token(db, refresh_data.refresh_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user_required)
):
    """Get current user information"""
    return current_user


@router.post("/logout")
def logout():
    """Logout (client should discard tokens)"""
    return {"message": "Successfully logged out. Please discard your tokens."}


# Test endpoints for different roles
@router.get("/test/admin")
def test_admin_access(current_user: UserResponse = Depends(get_current_user_required)):
    if current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"message": f"Hello {current_user.role.value} {current_user.full_name}!", "role": current_user.role.value}


@router.get("/test/maintainer")  
def test_maintainer_access(current_user: UserResponse = Depends(get_current_user_required)):
    if current_user.role.value not in ["MAINTAINER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Maintainer or Admin access required")
    return {"message": f"Hello {current_user.role.value} {current_user.full_name}!", "role": current_user.role.value}


@router.get("/test/any")
def test_any_access(
    current_user: UserResponse = Depends(get_current_user_required)
):
    """Test endpoint - Any authenticated user"""
    return {"message": f"Hello {current_user.role} {current_user.full_name}!", "role": current_user.role}


@router.post("/google/exchange")
def exchange_google_code(
    code_data: dict,
    db: Session = Depends(get_db)
):
    """Exchange Google OAuth code for user info"""
    try:
        code = code_data.get('code')
        if not code:
            print("No authorization code provided")
            raise HTTPException(status_code=400, detail="Authorization code required")
        
        # Debug: Print environment variables (remove in production)
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        print(f"Client ID: {client_id[:10]}..." if client_id else "Client ID: None")
        print(f"Client Secret: {client_secret[:10]}..." if client_secret else "Client Secret: None")
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Google OAuth credentials not configured")
        
        # Exchange code for access token - Use form data, not JSON
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/auth/google/callback"
        }
        
        print(f"Token request data: {token_data}")
        
        token_response = requests.post('https://oauth2.googleapis.com/token', data=token_data)
        
        print(f"Token response status: {token_response.status_code}")
        print(f"Token response text: {token_response.text}")
        
        if not token_response.ok:
            print(f"Token exchange failed: {token_response.text}")
            raise HTTPException(status_code=400, detail=f"Failed to exchange code for token: {token_response.text}")
        
        token_result = token_response.json()
        access_token = token_result.get('access_token')
        
        if not access_token:
            print("No access token received")
            raise HTTPException(status_code=400, detail="No access token received")
        
        # Get user info from Google
        user_response = requests.get(
            f'https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}'
        )
        
        if not user_response.ok:
            print(f"Failed to get user info: {user_response.text}")
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_info = user_response.json()
        
        return {
            'email': user_info.get('email'),
            'name': user_info.get('name')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"OAuth exchange error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth exchange failed: {str(e)}")
    

@router.post("/google", response_model=LoginResponse)
def google_login(
    google_data: GoogleLoginRequest, 
    db: Session = Depends(get_db)
):
    """Authenticate user via Google OAuth"""
    try:
        print(f"Google login attempt for: {google_data.email}")
        
        # Find user by email
        db_user = db.query(UserSchema).filter(UserSchema.email == google_data.email).first()
        
        if not db_user:
            raise HTTPException(
                status_code=401, 
                detail="User not found. Please contact admin to create your account first."
            )
        
        # Update name if different
        if db_user.full_name != google_data.name:
            print(f"Updating user name from '{db_user.full_name}' to '{google_data.name}'")
            db_user.full_name = google_data.name
            db.commit()
            db.refresh(db_user)
        
        # Create tokens (same as regular login)
        token_data = {
            "sub": db_user.id,
            "email": db_user.email,
            "role": db_user.role.value
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": db_user.id})
        
        # Prepare response (same as regular login)
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
        
        print(f"Successfully authenticated user: {db_user.email}")
        return LoginResponse(user=user_response, tokens=tokens)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Google login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google login failed: {str(e)}")