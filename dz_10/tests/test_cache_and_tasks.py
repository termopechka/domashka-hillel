import csv
from pathlib import Path

import pytest
from django.core.cache import cache, caches
from django.test import override_settings
from django.urls import reverse

from books.cache import (
    get_book_cache_key,
    get_book_detail_fragment_keys,
)
from books.tasks import (
    clear_expired_sessions,
    generate_books_report,
    send_async_email,
)


@pytest.mark.django_db(transaction=True)
def test_book_save_invalidates_low_level_fragment_and_view_caches(book_factory):
    book = book_factory()
    low_level_key = get_book_cache_key(book.pk)
    fragment_keys = get_book_detail_fragment_keys(book.pk)

    cache.set(low_level_key, book, 900)
    for fragment_key in fragment_keys:
        cache.set(fragment_key, "cached fragment", 900)
    caches["views"].set("cached-view", "cached response", 900)

    book.title = "Changed title"
    book.save()

    assert cache.get(low_level_key) is None
    assert all(cache.get(key) is None for key in fragment_keys)
    assert caches["views"].get("cached-view") is None


@pytest.mark.django_db
def test_book_detail_fragment_is_scoped_to_book(web_client, book_factory):
    cache.clear()
    first_book = book_factory(title="First cached book")
    second_book = book_factory(title="Second cached book")

    first_response = web_client.get(
        reverse("book:detail", kwargs={"pk": first_book.pk})
    )
    second_response = web_client.get(
        reverse("book:detail", kwargs={"pk": second_book.pk})
    )

    assert first_book.title in first_response.content.decode()
    assert second_book.title in second_response.content.decode()
    assert first_book.title not in second_response.content.decode()


@pytest.mark.django_db(transaction=True)
def test_book_api_view_cache_is_invalidated_when_catalog_changes(
    api_client, book_factory
):
    caches["views"].clear()
    first_book = book_factory(title="Initially cached book")
    list_url = reverse("api:catalog:books-list")

    first_response = api_client.get(list_url)
    assert first_response.status_code == 200
    assert [item["id"] for item in first_response.data["results"]] == [first_book.pk]

    second_book = book_factory(title="Book created after cache fill")
    second_response = api_client.get(list_url)

    assert second_response.status_code == 200
    assert [item["id"] for item in second_response.data["results"]] == [
        first_book.pk,
        second_book.pk,
    ]


def test_send_async_email_task_uses_django_mail_backend(mocker):
    mocked_send_mail = mocker.patch("books.tasks.send_mail", return_value=1)

    result = send_async_email(
        subject="Report ready",
        message="The report has been generated.",
        recipient_list=["reader@example.com"],
    )

    assert result == 1
    mocked_send_mail.assert_called_once()


@pytest.mark.django_db
def test_generate_books_report_task_creates_csv(tmp_path, book_factory):
    book = book_factory(title="Report Book", author="Report Author")

    with override_settings(MEDIA_ROOT=tmp_path):
        relative_report_path = generate_books_report()

    report_path = Path(tmp_path) / relative_report_path
    with report_path.open(encoding="utf-8", newline="") as report_file:
        rows = list(csv.reader(report_file))

    assert report_path.exists()
    assert rows[0] == ["id", "title", "author", "price", "stock", "category"]
    assert rows[1][0:3] == [str(book.pk), book.title, book.author]


def test_clear_expired_sessions_task_uses_management_command(mocker):
    mocked_call_command = mocker.patch("books.tasks.call_command")

    result = clear_expired_sessions()

    assert result == "Expired sessions cleanup completed"
    mocked_call_command.assert_called_once_with("clearsessions", verbosity=0)
