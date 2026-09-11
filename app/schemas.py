from typing import Literal
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime




#Schema for new user registration


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


#Schema for returning user Details

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    role: str = "user"
    created_at: datetime

    class Config:
        from_attributes = True




class Token(BaseModel):
    access_token:str
    token_type:str = 'bearer'

#Schema for user login


class UserLogin(BaseModel):
    email:str
    password:str


class PostCreate(BaseModel):
    
    title:str
    content:str

class PostResponse(BaseModel):
    id:int
    title:str
    content:str