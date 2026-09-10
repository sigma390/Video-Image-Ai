from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import User, get_async_session
from app.schemas import UserResponse

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/", response_model=list[UserResponse])
async def get_all_users(session: AsyncSession = Depends(get_async_session)) -> list[UserResponse]:
    result = await session.execute(select(User))  # query all users
    users_list = result.scalars().all()           # get user list
    return users_list
