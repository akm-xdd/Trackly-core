import pytest
from app.utils.file_id import generate_file_id
from app.utils.auth import extract_token_from_header
from datetime import datetime, timedelta


class TestFileId:
    """Test file ID generation utility."""
    
    def test_generate_file_id_format(self):
        """Test file ID format is correct."""
        file_id = generate_file_id()
        
        assert len(file_id) == 8
        assert file_id.startswith('F')
        assert file_id[1:].isalnum()  # Rest should be alphanumeric
    
    def test_generate_file_id_unique(self):
        """Test file IDs are unique."""
        ids = [generate_file_id() for _ in range(100)]
        
        assert len(set(ids)) == 100  # All should be unique


class TestAuthUtils:
    """Test authentication utility functions."""
    
    def test_extract_token_from_header_valid(self):
        """Test extracting token from valid Bearer header."""
        header = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        
        token = extract_token_from_header(header)
        
        assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    
    def test_extract_token_from_header_invalid_scheme(self):
        """Test extracting token from invalid scheme."""
        header = "Basic sometoken"
        
        token = extract_token_from_header(header)
        
        assert token is None
    
    def test_extract_token_from_header_malformed(self):
        """Test extracting token from malformed header."""
        header = "Bearer"  # Missing token
        
        token = extract_token_from_header(header)
        
        assert token is None
    
    def test_extract_token_from_header_none(self):
        """Test extracting token from None header."""
        token = extract_token_from_header(None)
        
        assert token is None
    
    def test_extract_token_from_header_empty(self):
        """Test extracting token from empty header."""
        token = extract_token_from_header("")
        
        assert token is None


class TestTokenExpiry:
    """Test token expiry logic."""
    
    def test_create_token_with_custom_expiry(self):
        """Test creating token with custom expiry."""
        from app.utils.auth import create_access_token
        
        data = {"sub": "test-user"}
        custom_expiry = timedelta(minutes=5)
        
        token = create_access_token(data, expires_delta=custom_expiry)
        
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_verify_expired_token(self):
        """Test verifying an expired token."""
        from app.utils.auth import create_access_token, verify_token
        import time
        
        # Create token that expires in 1 second
        data = {"sub": "test-user"}
        short_expiry = timedelta(seconds=1)
        token = create_access_token(data, expires_delta=short_expiry)
        
        # Wait for token to expire
        time.sleep(2)
        
        # Should return None for expired token
        payload = verify_token(token)
        assert payload is None