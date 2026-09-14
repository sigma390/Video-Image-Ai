from app.db import Post, User, create_tables, get_async_session
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request , Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.router import image, user, auth
import time
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()  # create tables on startup
    yield

app = FastAPI(lifespan=lifespan)  # init app


#middleware for logging 
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter() #starts the counter
    print(f"Incoming request: {request.method} {request.url.path}") 
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    print(
        f"Completed: {response.status_code} "
        f"in {process_time:.4f} seconds"
    )
    return response

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(image.router)


@app.get("/feed")
async def get_feed(
    page : int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    username: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session)  # db session
):
    offset = (page - 1)* limit
    query  = select(Post)

    if username :
        query = query.join(Post.user).where(User.username == username)
        
    result = await session.execute(
        query.order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
    )  # query all posts
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