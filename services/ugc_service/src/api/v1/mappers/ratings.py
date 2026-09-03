"""Маппинг оценок и статистики."""

from api.v1.schemas.ratings import (
    FilmRatingStatsResponse,
    RatingDistributionResponse,
    RatingResponse,
)
from models.rating import FilmRatingStats, Rating


def build_rating_response(rating: Rating) -> RatingResponse:
    return RatingResponse(
        film_id=rating.film_id,
        value=rating.value,
        created_at=rating.created_at,
        updated_at=rating.updated_at,
    )


def build_rating_stats_response(
    stats: FilmRatingStats,
) -> FilmRatingStatsResponse:
    return FilmRatingStatsResponse(
        film_id=stats.film_id,
        rating_count=stats.rating_count,
        average_rating=stats.average_rating,
        likes_count=stats.likes_count,
        dislikes_count=stats.dislikes_count,
        distribution=[
            RatingDistributionResponse(value=item.value, count=item.count)
            for item in stats.distribution
        ],
    )
