# Project Progress

## Step 4: Posts API Implementation

### What was built
We built a RESTful API for managing blog posts, fully integrating it into the existing FastAPI backend. The API handles complete CRUD (Create, Read, Update, Delete) functionality. Authentication is enforced on endpoints that mutate data, ensuring only valid users can create, update, or delete posts, and ownership rules guarantee that users can only modify their own posts. 

### Why `schemas/` was created
In FastAPI, `pydantic` schemas are essential for data validation and serialization. We created a `schemas/` directory (specifically `src/schemas/post.py`) to define exactly what a valid request body looks like (e.g., `PostCreate` requiring `title` and `content`) and what the response payload should contain (`PostResponse`). This guarantees bad data is rejected automatically with a 422 error before it even reaches our application logic.

### Why controllers were not used
While traditional MVC (Model-View-Controller) frameworks heavily rely on controllers, FastAPI applications often adopt a more streamlined architecture. We skipped a dedicated `controllers/` layer because our `routes` are designed to be thin, primarily handling HTTP concerns (like dependency injection and response formatting) while directly deferring all orchestration and business rules to the `services` layer. Adding controllers would have introduced unnecessary boilerplate without providing architectural benefit.

### Purpose of `routes/posts.py`
This file acts as the entry point for all HTTP requests aimed at `/api/posts`. It registers the specific HTTP verbs (`GET`, `POST`, `PUT`, `DELETE`), defines response models, injects required dependencies (like `get_current_user` and `get_pool`), and maps the requests directly to the corresponding functions in `post_service.py`.

### Purpose of `post_service.py`
The service layer contains the application's business logic. Its job is to orchestrate operations. For example, before updating a post, the service fetches the existing post and applies the business rule checking whether the `author_id` matches the current `user_id`. If business rules fail, it raises HTTP exceptions (like 403 Forbidden). If they pass, it delegates data persistence to the repository.

### Purpose of `post_repository.py`
The repository handles all direct database access. It encapsulates the SQL queries (`INSERT`, `SELECT`, `UPDATE`, `DELETE`) executed via `asyncpg`. It knows nothing about HTTP contexts or complex business validations—its only job is executing queries securely and mapping the database rows back into Python dictionaries.

### CRUD operations
The API supports full CRUD capabilities:
- **C**reate: `POST /api/posts` inserts a new row into the PostgreSQL database.
- **R**ead: `GET /api/posts` returns a list of posts, and `GET /api/posts/{post_id}` returns a single post.
- **U**pdate: `PUT /api/posts/{post_id}` dynamically generates a SQL `UPDATE` statement based on which fields (`title`, `content`) are provided.
- **D**elete: `DELETE /api/posts/{post_id}` removes the corresponding row.

### Authentication flow
Authentication is managed via JSON Web Tokens (JWT). For protected endpoints, the route requires `current_user: dict = Depends(get_current_user)`. FastAPI automatically intercepts the request, extracts the Bearer token from the `Authorization` header, and passes it to the `verify_jwt_token` function. If the token is valid and unexpired, the decoded user payload is passed to the route.

### Ownership/authorization flow
Authentication verifies *who* the user is, but Authorization verifies *what they are allowed to do*. The ownership flow is enforced in the `post_service.py`. When an update or delete request arrives, the service extracts the `userId` from the JWT payload and converts it to a UUID. It then fetches the target post from the database and compares the `author_id` of the post with the current `user_uuid`. If they don't match, the operation is immediately halted and a `403 Forbidden` is returned.

### Database interaction
We interact with the Neon PostgreSQL database entirely asynchronously using `asyncpg`. The `get_pool()` dependency manages connection pooling, injecting a ready-to-use pool into the repository layer. The repository then uses `async with self.pool.acquire() as connection:` to check out a connection, executes parameterized queries (e.g., `WHERE id = $1`) to prevent SQL injection, and returns the result.

### Request → Route → Service → Repository → PostgreSQL flow
1. **Client** sends `POST /api/posts` with JSON body and JWT.
2. **FastAPI Route** catches it. Dependency injection runs `get_current_user`, yielding `user_id`. Pydantic validates the JSON payload into a `PostCreate` object.
3. The Route calls the **Service** method `create_post(user_id, post_data)`.
4. The Service validates the `user_id` as a valid UUID, then calls the **Repository** method `create_post`.
5. The Repository checks out a connection from the pool and runs the `INSERT` SQL query with parameterized inputs against **PostgreSQL**.
6. Data is returned up the chain, serialized, and sent back as a `201 Created` HTTP response.

### Important FastAPI concepts used
- **Dependency Injection**: `Depends()` was heavily utilized to cleanly inject database pools and authentication payloads into route handlers without cluttering the code.
- **`APIRouter`**: Used to group all post-related endpoints together in `src/routes/posts.py`, which is then attached to the main app in `src/app.py`.
- **Response Models**: Utilizing `response_model=PostResponse` in route decorators guarantees that outgoing data conforms to our expected schema (and auto-generates documentation).

### Important asyncpg concepts used
- **Connection Pools**: Managed globally via `asyncpg.create_pool()` to efficiently handle high concurrency.
- **`fetchrow()` and `fetch()`**: Used to execute queries that return a single row or multiple rows respectively.
- **Parameterization (`$1`, `$2`)**: Prevents SQL injection by treating inputs strictly as literal values rather than executable code.

### HTTP status codes used
- `200 OK`: Successful GET and PUT requests.
- `201 Created`: Successful POST request.
- `204 No Content`: Successful DELETE request (the response has no body).
- `401 Unauthorized`: Request missing a JWT or providing an invalid one.
- `403 Forbidden`: User attempts to modify a post they do not own.
- `404 Not Found`: Requesting a `post_id` that does not exist in the database.
- `422 Unprocessable Entity`: Request body is missing required fields or violates Pydantic rules.

### Tests performed
An end-to-end Python test script was built to interact directly with the running server using `requests`. The tests covered:
- Server Health Check (`GET /health`)
- Retrieving all posts (`GET /api/posts`)
- Handling invalid IDs (`GET /api/posts/9999999` -> 404)
- Creating a post with a valid JWT (`POST /api/posts/`)
- Retrieving the newly created post (`GET /api/posts/{id}`)
- Updating the post (`PUT /api/posts/{id}`)
- **Ownership Test**: Attempting to update and delete the post using a completely different user's JWT (`PUT/DELETE` -> 403 Forbidden)
- Invalid JSON body structures (`POST` -> 422)
- Missing Authorization headers (`POST` -> 401)
- Deleting the post successfully as the owner (`DELETE` -> 204)

### Actual test results
All tests passed successfully on the first comprehensive run.
- Code 200 returned for `GET /health` and `GET /api/posts`.
- Code 201 returned for `POST /api/posts`.
- Code 403 returned exactly as expected when User 2 attempted to update/delete User 1's post.
- Code 422 correctly caught a missing `title` and `content`.
- Code 401 correctly caught unauthenticated POST attempts.

### Any issue found and how it was fixed
- **PYTHONPATH Resolution in Subprocesses**: While writing the automated end-to-end test script, launching the FastAPI server using `subprocess.Popen(["python", "src/server.py"])` initially failed with a `ModuleNotFoundError` for `src`. This was fixed by programmatically injecting `PYTHONPATH` pointing to the project root into the subprocess environment variables, allowing Python to resolve the local package paths correctly during testing.
