


from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
router = APIRouter(
    prefix='/images',
    tags=['Images']
)
from app.auth import get_current_user
from app.db import User, Post, create_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.images import imagekit
import os
import tempfile

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),                       # upload file
    caption: str = Form(""),    
    current_user : User = Depends(get_current_user),                        # post caption
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
            user_id= current_user.id,
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