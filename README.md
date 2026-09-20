# Blog Platform API

A backend REST API for a blog platform built with **FastAPI** and **PostgreSQL**, with JWT-based authentication and a layered architecture designed for scalability and maintainability.

The project is being developed step by step to understand how a production-style backend works — from HTTP requests and authentication to database access, caching, testing, performance measurement, and deployment.

## 🚀 Current Status

| Feature                  | Status                 |
| ------------------------ | ---------------------- |
| FastAPI Foundation       | ✅ Completed            |
| Neon PostgreSQL          | ✅ Completed            |
| JWT Authentication       | ✅ Completed            |
| Posts CRUD API           | ✅ Completed & Verified |
| Comments API             | ✅ Completed & Verified |
| Likes API                | ✅ Completed & Verified |
| Pagination               | ✅ Completed & Verified |
| Redis Caching            | 🔜 Planned             |
| Cache Invalidation + TTL | 🔜 Planned             |
| Automated Testing        | 🔜 Planned             |
| Performance Measurement  | 🔜 Planned             |
| Deployment               | 🔜 Planned             |

---

## 🛠️ Tech Stack

### Currently Used

* **Python**
* **FastAPI**
* **Uvicorn**
* **PostgreSQL**
* **Neon**
* **asyncpg**
* **Pydantic**
* **JWT / PyJWT**
* **python-dotenv**

### Planned

* **Redis**
* Automated API testing
* Performance testing
* Production deployment

---

## 🏗️ Architecture

The project follows a layered backend architecture:

```text
Client
   ↓
FastAPI Routes
   ↓
JWT Authentication
   ↓
Services
   ↓
Repositories
   ↓
PostgreSQL
   ↓
Response
```

### Responsibilities

**Routes**

Handle HTTP requests, request validation, dependencies, response models, and status codes.

**Services**

Contain application/business logic such as ownership and authorization rules.

**Repositories**

Handle database operations and SQL queries using `asyncpg`.

**Schemas**

Use Pydantic models to validate incoming data and serialize API responses.

---

## 📁 Project Structure

```text
blog-platform-api/
│
├── scripts/
│   ├── init_db.py
│   └── test_connection.py
│
├── src/
│   ├── config/
│   │   └── db.py
│   │
│   ├── controllers/
│   │   └── .gitkeep
│   │
│   ├── db/
│   │   └── schema.sql
│   │
│   ├── middleware/
│   │   └── auth.py
│   │
│   ├── repositories/
│   │   ├── post_repository.py
│   │   ├── comment_repository.py
│   │   └── like_repository.py
│   │
│   ├── routes/
│   │   ├── posts.py
│   │   ├── comments.py
│   │   └── likes.py
│   │
│   ├── schemas/
│   │   ├── post.py
│   │   ├── comment.py
│   │   └── like.py
│   │
│   ├── services/
│   │   ├── post_service.py
│   │   ├── comment_service.py
│   │   └── like_service.py
│   │
│   ├── utils/
│   │   └── jwt_utils.py
│   │
│   ├── app.py
│   └── server.py
│
├── .env
├── .gitignore
├── requirements.txt
├── PROJECT_PROGRESS.md
└── README.md
```

> `.env` contains local environment variables and should never be committed to GitHub.

---

# 🔐 Authentication

The API uses **JWT-based authentication**.

For protected endpoints, the client sends:

```http
Authorization: Bearer <access_token>
```

The authentication flow is:

```text
Client
   ↓
Bearer Token
   ↓
HTTPBearer
   ↓
JWT Verification
   ↓
Decoded JWT Payload
   ↓
userId
```

The existing `get_current_user()` dependency handles authentication.

The user's `userId` from the JWT is used as the `author_id` when creating posts and comments.

---

# 📝 Posts API

The Posts API currently supports complete CRUD operations.

## Endpoints

| Method | Endpoint                            | Authentication | Description          |
| ------ | ----------------------------------- | -------------- | -------------------- |
| POST   | `/api/posts`                        | ✅ Required     | Create a post        |
| GET    | `/api/posts?page=1&limit=10`        | ❌ Public       | Get all posts (paginated) |
| GET    | `/api/posts/{post_id}`              | ❌ Public       | Get a single post    |
| PUT    | `/api/posts/{post_id}`              | ✅ Required     | Update your own post |
| DELETE | `/api/posts/{post_id}`              | ✅ Required     | Delete your own post |

**Pagination Details:**
The `GET /api/posts` endpoint accepts `page` and `limit` query parameters.
- **page**: The page number to retrieve (default: 1)
- **limit**: The number of items per page (default: 10, max: 100)
- **Ordering**: Posts are returned in deterministic newest-first ordering (`created_at DESC, id DESC`).

---

# 💬 Comments API

The Comments API currently supports complete CRUD operations.

## Endpoints

| Method | Endpoint                            | Authentication | Description             |
| ------ | ----------------------------------- | -------------- | ----------------------- |
| POST   | `/api/posts/{post_id}/comments`     | ✅ Required     | Create a comment        |
| GET    | `/api/posts/{post_id}/comments`     | ❌ Public       | Get comments for post   |
| PUT    | `/api/comments/{comment_id}`        | ✅ Required     | Update your own comment |
| DELETE | `/api/comments/{comment_id}`        | ✅ Required     | Delete your own comment |

---

# ❤️ Likes API

The Likes API allows users to like posts and retrieve like counts.

## Endpoints

| Method | Endpoint                            | Authentication | Description             |
| ------ | ----------------------------------- | -------------- | ----------------------- |
| POST   | `/api/posts/{post_id}/like`         | ✅ Required     | Like a post             |
| DELETE | `/api/posts/{post_id}/like`         | ✅ Required     | Unlike a post           |
| GET    | `/api/posts/{post_id}/likes`        | ❌ Public       | Get like count          |

---

# 🗄️ Database

The project uses **PostgreSQL hosted on Neon**.

The current schema contains:

### `posts`

```text
id
author_id
title
content
created_at
updated_at
```

### `comments`

```text
id
post_id
author_id
content
created_at
```

### `likes`

```text
post_id
user_id
created_at
```

The project uses an **asyncpg connection pool** for asynchronous database operations.
