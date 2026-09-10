from app.db import Post, create_tables, get_async_session
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.router import image, user, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()  # create tables on startup
    yield

app = FastAPI(lifespan=lifespan)  # init app

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(image.router)


@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session)  # db session
):
    result = await session.execute(select(Post))  # query all posts
    posts = result.scalars().all()                # get post list
    post_data = []
    for post in posts:
        post_data.append({
            "id": str(post.id),
            "caption": post.caption,
            "user_id": post.user_id,
            "file_name": post.file_name,
            "file_type": post.file_type,
            "url": post.url,
            "created_at": post.created_at
        })
    return post_data


@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,                  # post id to delete
    session: AsyncSession = Depends(get_async_session)  # db session
):
    post_idd = uuid.UUID(post_id)
    result = await session.execute(select(Post).where(Post.id == post_idd))  # find post
    post = result.scalars().first()  # get post
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")  # 404 error

    await session.delete(post)
    await session.commit()
    return {"message": "Post deleted successfully"}  # success message