"""Shared fixtures.

The server is started once per session on a free port; state is reset between
tests instead of restarting the process. That is what keeps a suite fast enough
to run on every push rather than nightly.
"""

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass

import httpx
import pytest

STARTUP_TIMEOUT_SECONDS = 30


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def base_url() -> str:
    """Live server URL. Overrides pytest-base-url so Playwright inherits it."""
    external = os.environ.get("TASKFLOW_BASE_URL")
    if external:
        # CI can point the same suite at a deployed environment.
        yield external.rstrip("/")
        return

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    env = {**os.environ, "TASKFLOW_TEST_MODE": "1"}
    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = (process.stdout.read() or b"").decode()
            raise RuntimeError(f"server exited during startup:\n{output}")
        try:
            if httpx.get(f"{url}/health", timeout=0.5).status_code == 200:
                break
        except httpx.TransportError:
            time.sleep(0.1)
    else:
        process.terminate()
        raise RuntimeError(f"server did not become healthy within "
                           f"{STARTUP_TIMEOUT_SECONDS}s")

    yield url

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    finally:
        if process.stdout is not None:
            process.stdout.close()


@pytest.fixture(autouse=True)
def clean_state(base_url: str):
    """Every test starts against an empty database."""
    httpx.post(f"{base_url}/api/_test/reset", timeout=5).raise_for_status()
    yield


@pytest.fixture
def api(base_url: str):
    with httpx.Client(base_url=base_url, timeout=10) as client:
        yield client


@dataclass(frozen=True)
class Account:
    id: str
    email: str
    password: str
    name: str
    token: str

    @property
    def auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


@pytest.fixture
def make_account(api: httpx.Client):
    """Register + log in a user through the public API.

    Setting fixtures up over the API rather than the UI keeps browser tests
    focused on the behaviour they actually claim to cover.
    """
    counter = 0

    def _make(password: str = "correct-horse-battery") -> Account:
        nonlocal counter
        counter += 1
        email = f"user{counter}@example.com"
        registration = api.post(
            "/api/auth/register",
            json={"email": email, "password": password, "name": f"User {counter}"},
        )
        registration.raise_for_status()

        login = api.post("/api/auth/login", json={"email": email, "password": password})
        login.raise_for_status()

        return Account(
            id=registration.json()["id"],
            email=email,
            password=password,
            name=registration.json()["name"],
            token=login.json()["access_token"],
        )

    return _make


@pytest.fixture
def account(make_account) -> Account:
    return make_account()


@pytest.fixture
def authed(base_url: str, account: Account):
    """HTTP client that is already authenticated as `account`."""
    with httpx.Client(
        base_url=base_url, timeout=10, headers=account.auth_header
    ) as client:
        yield client
