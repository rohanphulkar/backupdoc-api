import jwt
from datetime import datetime, timedelta
from decouple import config
import re
import bcrypt, uuid
from fastapi import HTTPException, Request
from typing import Dict, Optional

JWT_SECRET = str(config('JWT_SECRET'))
JWT_ALGORITHM = str(config('JWT_ALGORITHM'))

def validate_email(email: str) -> bool:
    """Validate email format using regex pattern."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number format - allows optional country code followed by 10 digits."""
    return bool(re.match(r'^(?:\+[0-9]{1,4})?[0-9]{10}$', phone))

def validate_password(password: str) -> bool:
    """
    Validate password strength.
    Must contain:
    - At least 8 characters
    - One uppercase letter
    - One lowercase letter 
    - One number
    """
    if len(password) < 8:
        return False
    return bool(re.search(r'[A-Z]', password) and 
                re.search(r'[a-z]', password) and 
                re.search(r'[0-9]', password))

def token_response(token: str) -> Dict[str, str]:
    """Format JWT token response."""
    return {"access_token": token}

def signJWT(user_id: str) -> Dict[str, str]:
    """Generate JWT token with user ID and expiration."""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=60)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token_response(token)

def decodeJWT(token: str) -> Optional[Dict]:
    """Decode and validate JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hashed version."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), 
                         hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), 
                        bcrypt.gensalt()).decode('utf-8')

def generate_reset_token() -> str:
    """Generate unique reset token using UUID4."""
    return str(uuid.uuid4())

async def verify_jwt_token(token: str) -> bool:
    """Verify JWT token validity."""
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return bool(decoded)
    except jwt.PyJWTError:
        return False

def verify_token(request: Request) -> Dict:
    """
    Verify and decode token from request headers.
    Raises HTTPException if token is invalid.
    """
    token = request.headers.get("Authorization") or request.headers.get("authorization")
    
    if not token or not token.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Invalid or missing Authorization header"
        )
        
    try:
        token = token.split(" ")[1]
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
def get_current_user(request: Request):
    token = request.headers.get("Authorization", "authorization")
    if token.split(" ")[0] == "Bearer":
        token = token.split(" ")[1]
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or missing Authorization header")
            
    decoded_token = decodeJWT(token)
    user_id = decoded_token.get("user_id") if decoded_token else None
    return user_id