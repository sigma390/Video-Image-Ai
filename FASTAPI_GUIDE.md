# FastAPI & Asynchronous SQLAlchemy: Complete Reference Guide

A step-by-step documentation of concepts, best practices, gotchas, and interview topics covered from the beginning up to the Database setup and Transactions.

---

## Table of Contents
1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [In-Memory CRUD & Common Python Gotchas](#2-in-memory-crud--common-python-gotchas)
3. [Request & Response Validation with Pydantic](#3-request--response-validation-with-pydantic)
4. [Asynchronous Database Setup (SQLAlchemy 2.0 + SQLite/Postgres)](#4-asynchronous-database-setup-sqlalchemy-20--sqlitepostgres)
5. [FastAPI Lifespan Management](#5-fastapi-lifespan-management)
6. [Database Transactions Deep Dive](#6-database-transactions-deep-dive)
7. [Real-World Transaction Scenarios](#7-real-world-transaction-scenarios)
8. [Core Interview Questions & Answers](#8-core-interview-questions--answers)

---

## 1. Project Overview & Architecture

### Directory Structure
```
FastApi-Fast/
├── app/
│   ├── app.py          # FastAPI application, route handlers, and lifespan
│   ├── db.py           # Database engine, session maker, base model & tables
│   └── schemas.py      # Pydantic models for request & response validation
├── main.py             # Server entry point (Uvicorn runner)
├── test.db             # SQLite database file (created on startup)
└── pyproject.toml      # Project dependencies and metadata
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
* **`PostCreate`**: Validates input when clients create a post (client doesn't send `id`).
* **`PostResponse`**: Defines the data contract returned to the client (includes `id`).

```python
from pydantic import BaseModel

class PostCreate(BaseModel):
    title: str
    content: str

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
```

---

## 4. Asynchronous Database Setup (SQLAlchemy 2.0 + SQLite/Postgres)

In `app/db.py`:

```python
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, Text, DateTime, UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Database URL for Async SQLite
DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 1. Base class for all ORM models
class Base(DeclarativeBase):
    pass

# 2. Database Model
class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caption = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# 3. Connection Engine
engine = create_async_engine(DATABASE_URL)

# 4. Session Factory
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 5. Table Initialization
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 6. Dependency for Route Handlers
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

---

## 5. FastAPI Lifespan Management

The `lifespan` context manager handles startup and shutdown tasks cleanly:

In `app/app.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db import create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Code executed BEFORE application starts accepting requests ---
    await create_tables()
    yield
    # --- Code executed on application SHUTDOWN ---

# Register the lifespan with FastAPI:
app = FastAPI(lifespan=lifespan)
```

---

## 6. Database Transactions Deep Dive

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

## 7. Real-World Transaction Scenarios

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

### Scenario B: Social Media Post with File Upload (S3)
* External services (like AWS S3) cannot be rolled back with SQL.
* **Strategy:** Upload file to S3 first -> Start DB transaction -> If DB fails, rollback DB and trigger background cleanup job to remove the uploaded file from S3.

### Scenario C: High Concurrency Flash Sale / Ticket Booking
* When multiple users attempt to buy the last seat at the exact same millisecond:
* Use **Row-Level Locking** (`select(...).with_for_update()`) inside an atomic transaction to ensure only one user acquires the lock and buys the seat.

---

## 8. Core Interview Questions & Answers

### Q1: Why use `AsyncSession` and `asyncpg`/`aiosqlite` instead of standard sync drivers?
> **Answer:** FastAPI runs on a single-threaded `asyncio` event loop. Synchronous drivers block the event loop during disk/network I/O, preventing the server from handling other requests. Asynchronous drivers yield control back to the event loop while waiting for database queries, enabling high concurrency.

### Q2: Why use `yield` instead of `return` in `get_async_session()`?
> **Answer:** `yield` turns the function into an asynchronous generator. FastAPI enters the generator to yield the active session for the route, and after the response is sent, execution resumes after `yield` to ensure the session is properly closed and returned to the connection pool.

### Q3: Is `create_tables()` inside `lifespan` suitable for production?
> **Answer:** No. `create_all()` only creates tables if they do not exist; it cannot alter existing tables, add columns, or manage version history. In production, we use migration tools like **Alembic** inside CI/CD pipelines to version-control and apply schema migrations safely.
