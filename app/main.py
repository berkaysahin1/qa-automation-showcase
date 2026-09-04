"""TaskFlow — a small but realistic API + UI used as the system under test.

It exists so the test suite in `tests/` has something honest to exercise:
JWT auth, per-user data isolation, validation, pagination, and a browser UI.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import (
    LoginRequest,
    RegisterRequest,
    TaskCreate,
    TaskPage,
    TaskResponse,
    TaskUpdate,
    TokenResponse,
    UserResponse,
)
from app.store import store

BASE_DIR = Path(__file__).resolve().parent
SECRET = os.environ.get("TASKFLOW_SECRET", "dev-secret-not-for-production")
TOKEN_TTL_MINUTES = int(os.environ.get("TASKFLOW_TOKEN_TTL", "60"))
TEST_MODE = os.environ.get("TASKFLOW_TEST_MODE") == "1"

app = FastAPI(title="TaskFlow", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
bearer = HTTPBearer(auto_error=False)


def issue_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(minutes=TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "token expired"
        ) from None
    except jwt.InvalidTokenError:
        # `from None`: the decode error must not reach the client.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid token"
        ) from None
    user = store.get_user_by_id(payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown subject")
    return user


def as_task_response(task: dict) -> TaskResponse:
    return TaskResponse(**{k: v for k, v in task.items() if k != "owner_id"})


# --- auth ---------------------------------------------------------------
@app.post("/api/auth/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest) -> UserResponse:
    try:
        user = store.create_user(body.email, body.password, body.name)
    except ValueError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "email already registered"
        ) from None
    return UserResponse(id=user["id"], email=user["email"], name=user["name"])


@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    user = store.get_user_by_email(body.email)
    if user is None or not store.verify_password(body.password, user["password"]):
        # Same message for both branches: no user enumeration.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenResponse(access_token=issue_token(user["id"]))


@app.get("/api/me", response_model=UserResponse)
def me(user: dict = Depends(current_user)) -> UserResponse:
    return UserResponse(id=user["id"], email=user["email"], name=user["name"])


# --- tasks --------------------------------------------------------------
@app.get("/api/tasks", response_model=TaskPage)
def list_tasks(
    user: dict = Depends(current_user),
    done: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TaskPage:
    rows = store.list_tasks(user["id"], done=done)
    window = rows[offset : offset + limit]
    return TaskPage(
        items=[as_task_response(t) for t in window],
        total=len(rows),
        limit=limit,
        offset=offset,
    )


@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    body: TaskCreate, user: dict = Depends(current_user)
) -> TaskResponse:
    task = store.create_task(user["id"], body.title, body.notes, body.priority)
    return as_task_response(task)


def owned_task(task_id: str, user: dict) -> dict:
    task = store.get_task(task_id)
    # A task owned by someone else is reported as absent, not as forbidden:
    # 403 would leak the existence of other users' rows.
    if task is None or task["owner_id"] != user["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return task


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, user: dict = Depends(current_user)) -> TaskResponse:
    return as_task_response(owned_task(task_id, user))


@app.patch("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str, body: TaskUpdate, user: dict = Depends(current_user)
) -> TaskResponse:
    task = owned_task(task_id, user)
    task.update(body.model_dump(exclude_unset=True))
    return as_task_response(task)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, user: dict = Depends(current_user)) -> None:
    owned_task(task_id, user)
    store.delete_task(task_id)


# --- test-only helpers --------------------------------------------------
@app.post("/api/_test/reset", status_code=204, include_in_schema=False)
def reset_state() -> None:
    """Wipe all state. Only mounted when TASKFLOW_TEST_MODE=1."""
    if not TEST_MODE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    store.reset()


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}


# --- UI -----------------------------------------------------------------
@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse("/login")


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html")


@app.get("/tasks", response_class=HTMLResponse, include_in_schema=False)
def tasks_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "tasks.html")
