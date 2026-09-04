import pytest
from playwright.sync_api import Page

from tests.pages import LoginPage, TasksPage

pytestmark = pytest.mark.e2e


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    return LoginPage(page)


@pytest.fixture
def tasks_page(page: Page) -> TasksPage:
    return TasksPage(page)


@pytest.fixture
def signed_in(page: Page, account, tasks_page: TasksPage) -> TasksPage:
    """Start the test already authenticated.

    The session is seeded straight into storage instead of driving the login
    form, so a broken login page fails one test rather than all of them.
    """
    page.goto(LoginPage.PATH)  # establishes the origin storage belongs to
    page.evaluate(
        "token => localStorage.setItem('taskflow.token', token)", account.token
    )
    return tasks_page.open()
