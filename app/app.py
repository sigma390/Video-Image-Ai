from fastapi import FastAPI, HTTPException, File, Form, UploadFile, Depends  # fastapi tools
from app.schemas import PostResponse, PostCreate                             # pydantic schemas
from app.db import Post, create_tables, get_async_session                    # db models & session
from sqlalchemy import select                                                # sql query builder
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

@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session)  # db session
):
    result = await session.execute(select(Post))  # query all posts
    posts = result.scalars().all()                # get post list
    post_data = []
    for post in posts:
        post_data.append({
            "id":str(post.id),
            "caption": post.caption,
            "file_name": post.file_name,
            "file_type": post.file_type,
            "url": post.url,
            "created_at": post.created_at
        })
    return post_data
