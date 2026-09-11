from sqlalchemy import null
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.db import User, get_async_session
from app.schemas import UserResponse
from app.auth import require_admin
import uuid
router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/", response_model=list[UserResponse])
async def get_all_users(session: AsyncSession = Depends(get_async_session)) -> list[UserResponse]:
    result = await session.execute(select(User))  # query all users
    users_list = result.scalars().all()           # get user list
    return users_list

@router.delete("/delete/{user_id}")
async def delete_user_by_id(user_id: str, session: AsyncSession = Depends(get_async_session), _admin=Depends(require_admin)):
    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))  # find user
    user = result.scalars().first()                                                     # get user
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(user)
    await session.commit()
    return {"message": "User deleted successfully"} 


    
       
