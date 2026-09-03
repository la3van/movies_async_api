"""Маппинг рецензий и голосов."""

from api.v1.schemas.reviews import ReactionResponse, ReviewResponse
from models.reaction import ReactionValue, ReviewReaction
from models.review import ReviewDetails


def build_review_response(review: ReviewDetails) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        film_id=review.film_id,
        author_id=review.user_id,
        author_login=review.author_login,
        text=review.text,
        published_at=review.created_at,
        updated_at=review.updated_at,
        likes_count=review.likes_count,
        dislikes_count=review.dislikes_count,
        helpfulness=review.helpfulness,
        author_rating=review.author_rating,
    )


def build_reaction_response(reaction: ReviewReaction) -> ReactionResponse:
    return ReactionResponse(
        review_id=reaction.review_id,
        value="like" if reaction.value == ReactionValue.LIKE else "dislike",
        created_at=reaction.created_at,
        updated_at=reaction.updated_at,
    )
