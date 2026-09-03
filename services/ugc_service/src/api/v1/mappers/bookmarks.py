"""Маппинг закладок."""

from api.v1.schemas.bookmarks import BookmarkResponse
from models.bookmark import Bookmark


def build_bookmark_response(bookmark: Bookmark) -> BookmarkResponse:
    return BookmarkResponse(
        film_id=bookmark.film_id,
        created_at=bookmark.created_at,
    )
