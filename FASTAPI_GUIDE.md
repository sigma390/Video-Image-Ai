# FastAPI & Asynchronous SQLAlchemy: Complete Reference Guide

A comprehensive, step-by-step documentation of concepts, best practices, gotchas, architecture patterns, authentication, file handling, and interview questions covered in this project.

---

## Table of Contents
1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [In-Memory CRUD & Common Python Gotchas](#2-in-memory-crud--common-python-gotchas)
3. [Request & Response Validation with Pydantic](#3-request--response-validation-with-pydantic)
4. [Asynchronous Database Setup (SQLAlchemy 2.0 + SQLite/Postgres)](#4-asynchronous-database-setup-sqlalchemy-20--sqlitepostgres)
5. [Database Relationships & Foreign Keys](#5-database-relationships--foreign-keys)
6. [FastAPI Lifespan Management](#6-fastapi-lifespan-management)
7. [Modular Routing with APIRouter](#7-modular-routing-with-apirouter)
8. [Authentication, Password Hashing & JWT](#8-authentication-password-hashing--jwt)
9. [File Uploads & Cloud Storage Integration (ImageKit)](#9-file-uploads--cloud-storage-integration-imagekit)
10. [Database Transactions Deep Dive](#10-database-transactions-deep-dive)
11. [Real-World Transaction Scenarios](#11-real-world-transaction-scenarios)
12. [Core Interview Questions & Answers](#12-core-interview-questions--answers)

---

## 1. Project Overview & Architecture

### Directory Structure
```
FastApi-Fast/
├── app/
│   ├── router/
│   │   ├── auth.py         # Registration & Login endpoints (JWT issuance)
│   │   ├── user.py         # User management endpoints (query, delete)
│   │   └── image.py        # Image upload & ImageKit integration endpoints
│   ├── app.py              # Main FastAPI application, lifespan, router registration, feed
│   ├── auth.py             # Password hashing, JWT token creation/decoding, get_current_user dependency
│   ├── db.py               # Async engine, session maker, User & Post models, relationships
│   ├── images.py           # ImageKit SDK client initialization
│   └── schemas.py          # Pydantic models for validation & response serialization
├── main.py                 # Server entry point (Uvicorn runner)
├── test.db                 # SQLite database file (created on startup)
└── pyproject.toml          # Project dependencies and configuration
```

---

## 2. In-Memory CRUD & Common Python Gotchas

### Gotcha: Slicing Dictionaries
In Python, dictionaries (`dict`) **cannot be sliced directly**:
```python
text_posts = {1: {"title": "Post 1"}, 2: {"title": "Post 2"}}

# ❌ WRONG - Throws KeyError: slice(None, 2, None)
text_posts[:2] 

# ✅ CORRECT - Convert to list of items, slice, and convert back
dict(list(text_posts.items())[:2])

# ✅ ALTERNATIVE - Return list of values
list(text_posts.values())[:2]
```

### Gotcha: `raise` vs `return` for `HTTPException`
```python
# ❌ WRONG - FastAPI returns 200 OK with the exception object as response body
return HTTPException(status_code=404, detail="Post Not Found")

# ✅ CORRECT - FastAPI interrupts execution and returns a proper 404 HTTP status code
raise HTTPException(status_code=404, detail="Post Not Found")
```

---

## 3. Request & Response Validation with Pydantic

In `app/schemas.py`:
* **`UserCreate`**: Validates registration payload (email formatting, required strings).
* **`UserResponse`**: Restricts exposed fields to `id`, `email`, `username`, `created_at`. **Excludes sensitive columns like `password`**.
* **`from_attributes = True`** (Pydantic v2): Allows Pydantic models to read data directly from ORM attributes (formerly `orm_mode = True` in v1).

```python
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

---

## 4. Asynchronous Database Setup (SQLAlchemy 2.0 + SQLite/Postgres)

In `app/db.py`:

```python
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

# Database URL for Async SQLite (aiosqlite driver)
DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 1. Base class for all ORM models
class Base(DeclarativeBase):
    pass

# 2. Connection Engine
engine = create_async_engine(DATABASE_URL)

# 3. Session Factory
# expire_on_commit=False prevents attributes from becoming unloaded after commit
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 4. Table Initialization
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 5. Dependency for Route Handlers
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

---

## 5. Database Relationships & Foreign Keys

In `app/db.py`:

```python
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)  # stores hashed password
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # One User has Many Posts
    posts = relationship("Post", back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caption = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Foreign Key linking to users.id
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    user = relationship("User", back_populates="posts")
```

### Why Relationships Matter:
1. **Referential Integrity**: `ForeignKey("users.id")` guarantees that a post cannot belong to a non-existent user.
2. **Bidirectional Navigation**: `relationship(..., back_populates="...")` allows querying `user.posts` or `post.user` cleanly via ORM.

---

## 6. FastAPI Lifespan Management

The `lifespan` context manager replaces legacy `@app.on_event("startup")` and `@app.on_event("shutdown")`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executes before app starts serving traffic
    await create_tables()
    yield
    # Executes when app is shutting down (e.g. cleanup connections)

app = FastAPI(lifespan=lifespan)
```

---

## 7. Modular Routing with APIRouter

When applications grow, defining all routes in `app.py` becomes unmaintainable. We group related routes into dedicated modules in `app/router/`.

### Creating a Router
In `app/router/user.py`:
```python
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
    result = await session.execute(select(User))
    return result.scalars().all()
```

### Registering Routers in Main App
In `app/app.py`:
```python
from app.router import auth, user, image

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(image.router)
```

### ⚠️ Common APIRouter Gotchas:
1. **`prefix` must be a string, NOT a list:**
   ```python
   # ❌ WRONG - Throws AttributeError: 'list' object has no attribute 'startswith'
   router = APIRouter(prefix=['/images'])

   # ✅ CORRECT
   router = APIRouter(prefix="/images")
   ```
2. **Module Name Collisions:**
   Naming your router module the same as another module (e.g., `app/images.py` vs `app/router/image.py`) can cause import errors if not imported explicitly (`from app.router import image`).

---

## 8. Authentication, Password Hashing & JWT

Security architecture follows the **OAuth2 with Password Flow & Bearer Token** standard:

```
[Client] ---> POST /auth/login (email & password) ---> [FastAPI]
[Client] <--- Returns JWT Access Token <--- [FastAPI]
...
[Client] ---> Request with Authorization: Bearer <Token> ---> [Protected Endpoint]
[Protected Endpoint] verifies token & extracts current user from DB
```

### 1. Password Hashing (`pwdlib`)
In `app/auth.py`:
```python
from pwdlib import PasswordHash

# Uses Argon2 / modern secure password hashing
pass_has = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return pass_has.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pass_has.verify(password, hashed_password)
```

### 2. JWT Generation & Decoding (`pyjwt`)
```python
import jwt
from datetime import datetime, timedelta, timezone

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm="HS256")
```

### 3. Protecting Routes via `get_current_user` Dependency
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")  # User UUID stored in 'sub' claim
        user_uuid = uuid.UUID(str(user_id))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    result = await session.execute(select(User).where(User.id == user_uuid))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user
```

Any endpoint needing the authenticated user simply adds:
```python
@router.post("/upload")
async def upload_file(current_user: User = Depends(get_current_user)):
    # current_user is guaranteed to be authenticated and fetched from DB
    ...
```

---

## 9. File Uploads & Cloud Storage Integration (ImageKit)

In `app/router/image.py`:
When handling uploads:
* **`UploadFile`**: Asynchronously streams uploads without loading gigantic files into memory at once.
* **`Form(...)`**: Reads multipart form text fields (e.g. caption) alongside binary files.
* **Temporary Files & `try...finally`**: Ensures disk space is freed even if network/database errors occur.

```python
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(""),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    temp_file_path = None
    try:
        contents = await file.read()
        suffix = os.path.splitext(file.filename or "")[1]

        # Write to temporary file on disk
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(contents)

        # Upload to cloud (ImageKit)
        with open(temp_file_path, "rb") as f:
            upload_result = imagekit.files.upload(
                file=f,
                file_name=file.filename,
                use_unique_file_name=True,
                tags=["backend-upload"]
            )

        # Save metadata to DB
        post = Post(
            caption=caption,
            url=upload_result.url,
            file_type=upload_result.file_type,
            user_id=current_user.id,
            file_name=upload_result.name,
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post

    finally:
        # Guarantee temp file cleanup
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
```

---

## 10. Database Transactions Deep Dive

A **Transaction** is a group of database operations executed as a single, atomic unit of work (**All-or-Nothing**).

### The ACID Principles

| Principle | Meaning | Real-World Meaning |
| :--- | :--- | :--- |
| **A - Atomicity** | All operations succeed, or all are undone. | No partial states (e.g. money deducted without recipient receiving it). |
| **C - Consistency** | Database strictly satisfies all constraints/rules. | Foreign keys, uniqueness, and check constraints are never violated. |
| **I - Isolation** | Concurrent transactions do not interfere with each other. | Other users cannot read intermediate, uncommitted changes. |
| **D - Durability** | Once committed, changes are permanent. | Data survives power failures and server crashes. |

### Core Methods: `commit`, `rollback`, `refresh`

```python
# 1. db.add(instance)
# Stages the object in the current transaction (in memory).

# 2. await db.commit()
# Writes all staged changes permanently to the database disk.

# 3. await db.rollback()
# Discards all uncommitted changes and reverts to previous state.

# 4. await db.refresh(instance)
# Re-fetches the object from the DB to populate server-generated fields (id, timestamps).
```

---

## 11. Real-World Transaction Scenarios

### Scenario A: E-Commerce Checkout
```
Transaction Starts:
  1. Deduct 1 item from Inventory (Stock 5 -> 4)
  2. Create Order record
  3. Deduct User Wallet Balance ($50)
  
If any step fails (e.g., wallet balance is too low):
  -> ROLLBACK: Inventory is restored to 5, Order is discarded.
If all steps pass:
  -> COMMIT: Order placed successfully.
```

### Scenario B: Social Media Post with File Upload (S3 / ImageKit)
* External cloud storage services cannot be rolled back via SQL `ROLLBACK`.
* **Strategy:** Upload file to cloud first -> Start DB transaction -> If DB fails, rollback DB and trigger cleanup to delete the orphaned cloud file.

### Scenario C: High Concurrency Flash Sale / Ticket Booking
* When multiple users attempt to buy the last seat at the exact same millisecond:
* Use **Row-Level Locking** (`select(...).with_for_update()`) inside an atomic transaction to ensure only one worker acquires the lock and buys the seat.

---

## 12. Core Interview Questions & Answers

### Q1: Why use `AsyncSession` and `aiosqlite`/`asyncpg` instead of standard sync drivers?
> **Answer:** FastAPI runs on an asynchronous event loop. Synchronous drivers block the event loop during disk/network I/O, preventing the server from processing other concurrent requests. Asynchronous drivers yield control back to the event loop while waiting for database queries to return, drastically increasing throughput.

### Q2: Why use `yield` instead of `return` in `get_async_session()`?
> **Answer:** `yield` turns the function into an asynchronous generator dependency. FastAPI enters the dependency to provide the active session to the route handler. Once the request finishes (or errors), control returns to the code after `yield`, ensuring the session is closed and connections return cleanly to the pool.

### Q3: Why shouldn't you return raw SQLAlchemy models without a `response_model`?
> **Answer:** The SQLAlchemy model often contains sensitive columns (such as `password` hash or internal tokens). Without a Pydantic `response_model` (e.g., `UserResponse`), you risk leaking sensitive information into JSON responses. In addition, Pydantic schemas document the exact response structure in OpenAPI/Swagger `/docs`.

### Q4: What is the purpose of the `sub` claim in a JWT?
> **Answer:** `sub` stands for **Subject** in the RFC 7519 JWT specification. It identifies the principal that is the subject of the JWT (in our application, the unique User UUID).

### Q5: Why is `OAuth2PasswordRequestForm` expecting `username` instead of `email`?
> **Answer:** The official OAuth2 specification requires form fields to be named `username` and `password`. In FastAPI, even when authenticating with email, clients submit the email in the `username` form field (`form_data.username`).

### Q6: Why use `try...finally` for temporary files during file uploads?
> **Answer:** If an exception occurs (e.g. cloud upload timeout or DB error), regular execution stops immediately. The `finally` block guarantees that the temporary file on disk is deleted, preventing disk space exhaustion and resource leaks on the server.
