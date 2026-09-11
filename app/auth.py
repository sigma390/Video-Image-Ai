from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import User, get_async_session
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

# Secret
secret_key = os.getenv("SECRET_KEY")

if not secret_key:
    raise ValueError("Secret key not found in environment variables")

algorithm = "HS256"
access_token_expire_minutes = 30


# Hashing password
pass_has = PasswordHash.recommended()

def hash_password(password:str):
    return pass_has.hash(password)

 #verify password   
def verify_password(password:str, hashed_password:str):
    return pass_has.verify(password, hashed_password)

# Create access token

def create_access_token(data:dict):
    to_encode=data.copy() # creating a copy
    expire=datetime.now(timezone.utc)+timedelta(minutes=access_token_expire_minutes)
    to_encode.update({"exp":expire})
    encoded_jwt=jwt.encode(to_encode,secret_key,algorithm=algorithm)
    return encoded_jwt


#dependancy Extract and validate 
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")



async def get_current_user(
    token:str = Depends(oauth2_scheme),
    session:AsyncSession=Depends(get_async_session)
)-> User :
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        raise credentials_exception

    result = await session.execute(select(User).where(User.id == user_uuid))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user
    

async def require_admin(
    current_user: User = Depends(get_current_user)
):
    if current_user.role!="admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access Required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return current_user