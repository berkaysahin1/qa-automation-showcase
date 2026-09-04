"""Browser coverage of the core task workflow."""

import pytest
from playwright.sync_api import expect

pytestmark = [pytest.mark.e2e]


def test_a_new_account_sees_the_empty_state(signed_in):
    expect(signed_in.empty_state).to_be_visible()
    expect(signed_in.items).to_have_count(0)


def test_adding_a_task_shows_it_and_clears_the_form(signed_in):
    signed_in.add("Ship the release notes", priority="high")

    expect(signed_in.row("Ship the release notes")).to_be_visible()
    expect(signed_in.row("Ship the release notes")
           .get_by_test_id("task-priority")).to_have_text("high")
    expect(signed_in.title_input).to_have_value("")
    expect(signed_in.empty_state).to_be_hidden()


def test_completing_a_task_updates_its_state_and_the_counter(signed_in):
    signed_in.add("Review the pull request")
    expect(signed_in.open_count).to_have_text("1")

    signed_in.toggle("Review the pull request")

    expect(signed_in.row("Review the pull request")).to_have_attribute(
        "data-done", "true"
    )
    expect(signed_in.open_count).to_have_text("0")


def test_deleting_a_task_removes_it_permanently(signed_in, page):
    signed_in.add("Temporary")
    signed_in.delete("Temporary")

    expect(signed_in.items).to_have_count(0)
    page.reload()
    expect(signed_in.items).to_have_count(0)


def test_tasks_survive_a_page_reload(signed_in, page):
    signed_in.add("Persisted across reloads")
    page.reload()

    expect(signed_in.row("Persisted across reloads")).to_be_visible()


def test_an_empty_title_is_refused_client_side(signed_in):
    signed_in.title_input.fill("   ")
    signed_in.add_button.click()

    expect(signed_in.error).to_be_visible()
    expect(signed_in.items).to_have_count(0)


def test_tasks_are_listed_newest_first(signed_in):
    signed_in.add("older")
    signed_in.add("newer")

    expect(signed_in.items.get_by_test_id("task-title")).to_have_text(
        ["newer", "older"]
    )
