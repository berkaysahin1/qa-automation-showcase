"""In-memory persistence for the demo app.

Deliberately dependency-free: the point of this repository is the test
architecture, not the storage engine. Swapping this module for a real
repository layer does not change a single test.
"""

import hashlib
import os
import secrets
import threading
from datetime import UTC, datetime

_PBKDF2_ROUNDS = 120_000


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.users: dict[str, dict] = {}
        self.tasks: dict[str, dict] = {}

    # -- users -----------------------------------------------------------
    def hash_password(self, password: str, salt: bytes | None = None) -> str:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, _PBKDF2_ROUNDS
        )
        return f"{salt.hex()}${digest.hex()}"

    def verify_password(self, password: str, stored: str) -> bool:
        salt_hex, digest_hex = stored.split("$", 1)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), _PBKDF2_ROUNDS
        )
        return secrets.compare_digest(candidate.hex(), digest_hex)

    def create_user(self, email: str, password: str, name: str) -> dict:
        with self._lock:
            key = email.lower()
            if key in self.users:
                raise ValueError("email already registered")
            user = {
                "id": secrets.token_hex(8),
                "email": key,
                "name": name,
                "password": self.hash_password(password),
            }
            self.users[key] = user
            return user

    def get_user_by_email(self, email: str) -> dict | None:
        return self.users.get(email.lower())

    def get_user_by_id(self, user_id: str) -> dict | None:
        return next((u for u in self.users.values() if u["id"] == user_id), None)

    # -- tasks -----------------------------------------------------------
    def create_task(
        self, owner_id: str, title: str, notes: str, priority: str
    ) -> dict:
        with self._lock:
            task = {
                "id": secrets.token_hex(8),
                "owner_id": owner_id,
                "title": title,
                "notes": notes,
                "priority": priority,
                "done": False,
                "created_at": datetime.now(UTC),
            }
            self.tasks[task["id"]] = task
            return task

    def list_tasks(self, owner_id: str, done: bool | None = None) -> list[dict]:
        rows = [t for t in self.tasks.values() if t["owner_id"] == owner_id]
        if done is not None:
            rows = [t for t in rows if t["done"] is done]
        return sorted(rows, key=lambda t: t["created_at"], reverse=True)

    def get_task(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            self.tasks.pop(task_id, None)

    def reset(self) -> None:
        with self._lock:
            self.users.clear()
            self.tasks.clear()


store = Store()
