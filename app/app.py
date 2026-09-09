from app.db import User
import uuid
import os
import asyncio
import tempfile
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, File, Form, UploadFile, Depends  # fastapi tools
from app.db import Post, create_tables, get_async_session                    # db models & session
from sqlalchemy import select                                                # sql query builder
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from app.images import imagekit


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()  # create tables on startup
    yield

app = FastAPI(lifespan=lifespan)  # init app

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),                       # upload file
    caption: str = Form(""),                            # post caption
    session: AsyncSession = Depends(get_async_session)  # db session
):
    temp_file_path = None

    try:
        # read uploaded file content asynchronously
        contents = await file.read()

        # create temporary file on disk with the same file extension
        suffix = os.path.splitext(file.filename or "")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(contents)  # write content to temp file

        # upload to ImageKit using a context-managed file handle
        with open(temp_file_path, "rb") as f:
            upload_result = imagekit.files.upload(
                file=f,
                file_name=file.filename,
                use_unique_file_name=True,
                tags=["backend-upload"]
            )

        post = Post(
            caption=caption,
            url=upload_result.url,
            file_type=upload_result.file_type,
            file_name=upload_result.name,
        )
        session.add(post)            # add post
        await session.commit()       # save to db
        await session.refresh(post)  # refresh to get new id
        return post                  # return created post
    finally:
        # clean up temporary file from disk
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

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
    post_idd = uuid.UUID(post_id);
    result = await session.execute(select(Post).where(Post.id == post_idd)) #find post
    post = result.scalars().first() #get post
    if not post:
        raise HTTPException(status_code=404, detail="Post not found") # 404 error
   
    await session.delete(post)
    await session.commit()
    return {"message": "Post deleted successfully"}  # success message  



@app.post('/users/register')
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(User).where(User.email == email))  # find user by email
    user = result.scalars().first()                                           # get user
    if user:
        raise HTTPException(status_code = 403, detail = "User already exists")

    new_user = User(
        username = username,
        email = email,
        password = password
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return {"id": str(new_user.id), "username": new_user.username, "email": new_user.email, "created_at": new_user.created_at}



@app.get("/users")
async def get_all_users(session:AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(User))  # query all users
    users_list = result.scalars().all()           # get user list
    users = []
    for user in users_list:
        users.append({
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at
        })
    return users
    


@app.delete("/users/{user_id}")
async def delete_user_by_id(user_id: str, session:AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))  # find user
    user = result.scalars().first()                                                     # get user
    if not user:
        raise HTTPException(status_code = 404, detail = "User not found")
    await session.delete(user)
    await session.commit()
    return {"message": "User deleted successfully"}    