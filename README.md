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
| Comments API             | 🔜 Planned             |
| Likes API                | 🔜 Planned             |
| Pagination               | 🔜 Planned             |
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
│   │   └── post_repository.py
│   │
│   ├── routes/
│   │   └── posts.py
│   │
│   ├── schemas/
│   │   └── post.py
│   │
│   ├── services/
│   │   └── post_service.py
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

The user's `userId` from the JWT is used as the `author_id` when creating posts.

---

# 📝 Posts API

The Posts API currently supports complete CRUD operations.

## Endpoints

| Method | Endpoint               | Authentication | Description          |
| ------ | ---------------------- | -------------- | -------------------- |
| POST   | `/api/posts`           | ✅ Required     | Create a post        |
| GET    | `/api/posts`           | ❌ Public       | Get all posts        |
| GET    | `/api/posts/{post_id}` | ❌ Public       | Get a single post    |
| PUT    | `/api/posts/{post_id}` | ✅ Required     | Update your own post |
| DELETE | `/api/posts/{post_id}` | ✅ Required     | Delete your own post |

---

## Create Post

```http
POST /api/posts
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request:

```json
{
  "title": "My First Post",
  "content": "This is my first blog post."
}
```

Successful response:

```http
201 Created
```

---

## Get All Posts

```http
GET /api/posts
```

Returns the available posts ordered by:

```text
created_at DESC, id DESC
```

---

## Get a Single Post

```http
GET /api/posts/1
```

If the post does not exist:

```http
404 Not Found
```

---

## Update a Post

```http
PUT /api/posts/1
Authorization: Bearer <access_token>
Content-Type: application/json
```

Example:

```json
{
  "title": "Updated Title",
  "content": "Updated content."
}
```

Only the post owner can update the post.

A different authenticated user receives:

```http
403 Forbidden
```

---

## Delete a Post

```http
DELETE /api/posts/1
Authorization: Bearer <access_token>
```

Successful deletion:

```http
204 No Content
```

Only the post owner can delete the post.

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

The `comments` and `likes` tables are already part of the database schema but their APIs will be implemented in later steps.

The project uses an **asyncpg connection pool** for async
