from concurrent.interpreters import get_current
from fastapi import Depends
from fastapi import APIRouter
from app.auth import get_current_user

router = APIRouter(
    prefix="/posts",
    tags=["Posts"],
    dependencies=[Depends(get_current_user)]
)




