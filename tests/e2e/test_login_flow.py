"""Browser coverage of the sign-in journey."""

import re

import pytest
from playwright.sync_api import expect

pytestmark = [pytest.mark.e2e]


def test_valid_credentials_land_on_the_task_list(login_page, tasks_page, account):
    login_page.open().sign_in(account.email, account.password)

    expect(login_page.page).to_have_url(re.compile(r"/tasks$"))
    expect(tasks_page.current_user).to_have_text(account.email)


def test_wrong_password_shows_an_error_and_stays_on_the_form(login_page, account):
    login_page.open().sign_in(account.email, "definitely-not-it")

    expect(login_page.error).to_be_visible()
    expect(login_page.error).to_contain_text("Invalid email or password")
    expect(login_page.page).to_have_url(re.compile(r"/login$"))


def test_visiting_the_app_without_a_session_redirects_to_login(page, tasks_page):
    tasks_page.open()

    expect(page).to_have_url(re.compile(r"/login$"))


def test_signing_out_ends_the_session(signed_in, page):
    signed_in.sign_out()

    expect(page).to_have_url(re.compile(r"/login$"))
    assert page.evaluate("localStorage.getItem('taskflow.token')") is None
