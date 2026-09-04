"""Page object for /tasks."""

from playwright.sync_api import Locator, Page


class TasksPage:
    PATH = "/tasks"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.title_input = page.get_by_test_id("task-title-input")
        self.priority_select = page.get_by_test_id("task-priority-select")
        self.add_button = page.get_by_test_id("add-task")
        self.items = page.get_by_test_id("task-item")
        self.empty_state = page.get_by_test_id("empty-state")
        self.open_count = page.get_by_test_id("open-count")
        self.current_user = page.get_by_test_id("current-user")
        self.error = page.get_by_test_id("task-error")
        self.sign_out_button = page.get_by_test_id("logout")

    def open(self) -> "TasksPage":
        self.page.goto(self.PATH)
        return self

    def add(self, title: str, priority: str | None = None) -> None:
        """Add a task and wait until the list actually reflects it.

        The form clears itself only after the POST resolves; returning any
        earlier lets the next `fill()` race the reset. This is where browser
        suites become flaky, so the wait belongs in the page object rather
        than in every test that calls it.
        """
        self.title_input.fill(title)
        if priority:
            self.priority_select.select_option(priority)
        self.add_button.click()
        self.row(title).wait_for(state="visible")

    def row(self, title: str) -> Locator:
        return self.items.filter(has_text=title)

    def toggle(self, title: str) -> None:
        self.row(title).get_by_test_id("toggle-task").click()

    def delete(self, title: str) -> None:
        self.row(title).get_by_test_id("delete-task").click()

    def sign_out(self) -> None:
        self.sign_out_button.click()
