"""Преобразование MongoDB documents в доменные модели."""

from models.bookmark import Bookmark
from models.rating import Rating
from models.reaction import ReviewReaction
from models.review import Review, ReviewDetails


def build_bookmark(document: dict) -> Bookmark:
    return Bookmark(
        user_id=document["user_id"],
        film_id=document["film_id"],
        created_at=document["created_at"],
    )


def build_rating(document: dict) -> Rating:
    return Rating(
        user_id=document["user_id"],
        film_id=document["film_id"],
        value=document["value"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def build_review(document: dict) -> Review:
    return Review(
        id=document["_id"],
        film_id=document["film_id"],
        user_id=document["user_id"],
        author_login=document["author_login"],
        text=document["text"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def build_review_details(document: dict) -> ReviewDetails:
    return ReviewDetails(
        **build_review(document).model_dump(),
        likes_count=document.get("likes", 0),
        dislikes_count=document.get("dislikes", 0),
        helpfulness=document.get("helpfulness", 0),
        author_rating=document.get("author_rating"),
    )


def build_reaction(document: dict) -> ReviewReaction:
    return ReviewReaction(
        user_id=document["user_id"],
        review_id=document["review_id"],
        value=document["value"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )
