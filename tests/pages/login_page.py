"""Page object for /login.

Locators live here and nowhere else: when the markup changes, exactly one
file changes with it.
"""

from playwright.sync_api import Page


class LoginPage:
    PATH = "/login"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.email = page.get_by_test_id("email-input")
        self.password = page.get_by_test_id("password-input")
        self.submit = page.get_by_test_id("submit-login")
        self.error = page.get_by_test_id("login-error")

    def open(self) -> "LoginPage":
        self.page.goto(self.PATH)
        return self

    def sign_in(self, email: str, password: str) -> None:
        self.email.fill(email)
        self.password.fill(password)
        self.submit.click()
