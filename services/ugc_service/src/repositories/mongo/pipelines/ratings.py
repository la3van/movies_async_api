"""Aggregation pipeline статистики оценок фильма."""


def build_rating_stats_pipeline(film_id: str) -> list[dict]:
    """Сгруппировать оценки и построить полное распределение 0..10."""
    return [
        {"$match": {"film_id": film_id}},
        {
            "$group": {
                "_id": "$value",
                "count": {"$sum": 1},
            }
        },
        {
            "$group": {
                "_id": None,
                "rating_count": {"$sum": "$count"},
                "weighted_sum": {"$sum": {"$multiply": ["$_id", "$count"]}},
                "likes_count": {
                    "$sum": {"$cond": [{"$eq": ["$_id", 10]}, "$count", 0]}
                },
                "dislikes_count": {
                    "$sum": {"$cond": [{"$eq": ["$_id", 0]}, "$count", 0]}
                },
                "distribution": {
                    "$push": {"value": "$_id", "count": "$count"}
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "rating_count": 1,
                "average_rating": {
                    "$round": [
                        {"$divide": ["$weighted_sum", "$rating_count"]},
                        2,
                    ]
                },
                "likes_count": 1,
                "dislikes_count": 1,
                "distribution": 1,
            }
        },
    ]
