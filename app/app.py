from fastapi import FastAPI, HTTPException, File, Form, UploadFile, Depends  # fastapi tools
from app.schemas import PostResponse, PostCreate                             # pydantic schemas
from app.db import Post, create_tables, get_async_session                    # db models & session
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()  # create tables on startup
    yield

app = FastAPI(lifespan=lifespan)  # init app

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),                       # upload file
    caption: str = Form(...),                           # post caption
    session: AsyncSession = Depends(get_async_session)  # db session
    ):
    post = Post(
        caption=caption,
        file_name="name",
        file_type="photo",
        url="placeholder_url",
    )
    session.add(post)            # add post
    await session.commit()       # save to db
    await session.refresh(post)  # refresh to get new id
    return post                  # return created post