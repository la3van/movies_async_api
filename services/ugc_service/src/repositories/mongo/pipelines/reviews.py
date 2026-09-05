"""Aggregation pipelines для обогащения и сортировки рецензий."""

from core.pagination import ReviewCursor


def build_review_details_stages() -> list[dict]:
    """Добавить оценку автора и статистику голосов из смежных коллекций."""
    return [
        {
            "$lookup": {
                "from": "ratings",
                "let": {"author": "$user_id", "film": "$film_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$user_id", "$$author"]},
                                    {"$eq": ["$film_id", "$$film"]},
                                ]
                            }
                        }
                    },
                    {"$project": {"_id": 0, "value": 1}},
                    {"$limit": 1},
                ],
                "as": "author_rating_data",
            }
        },
        {
            "$lookup": {
                "from": "review_reactions",
                "let": {"review": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$review_id", "$$review"]}}},
                    {
                        "$group": {
                            "_id": None,
                            "likes": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$value", 1]},
                                        1,
                                        0,
                                    ]
                                }
                            },
                            "dislikes": {
                                "$sum": {
                                    "$cond": [
                                        {"$eq": ["$value", -1]},
                                        1,
                                        0,
                                    ]
                                }
                            },
                        }
                    },
                ],
                "as": "reaction_stats",
            }
        },
        {
            "$set": {
                "author_rating": {"$first": "$author_rating_data.value"},
                "likes": {
                    "$ifNull": [
                        {"$first": "$reaction_stats.likes"},
                        0,
                    ]
                },
                "dislikes": {
                    "$ifNull": [
                        {"$first": "$reaction_stats.dislikes"},
                        0,
                    ]
                },
            }
        },
        {"$set": {"helpfulness": {"$subtract": ["$likes", "$dislikes"]}}},
        {"$unset": ["author_rating_data", "reaction_stats"]},
    ]


def build_review_list_pipeline(
    *,
    film_id: str,
    sort: str,
    sort_fields: dict[str, str],
    cursor: ReviewCursor | None,
    page_size: int,
) -> list[dict]:
    """Построить seek-pagination без линейного ``$skip``."""
    descending = sort.startswith("-")
    field_name = sort[1:] if descending else sort
    mongo_field = sort_fields[field_name]
    direction = -1 if descending else 1
    comparison = "$lt" if descending else "$gt"
    stored_sort_fields = {"created_at", "updated_at"}

    pagination_field = (
        "_pagination_sort_value"
        if mongo_field == "author_rating"
        else mongo_field
    )

    seek_stage: list[dict] = []
    if cursor is not None:
        seek_stage = [
            {
                "$match": {
                    "$or": [
                        {pagination_field: {comparison: cursor.value}},
                        {
                            pagination_field: cursor.value,
                            "_id": {comparison: str(cursor.review_id)},
                        },
                    ]
                }
            }
        ]

    if mongo_field in stored_sort_fields:
        return [
            {"$match": {"film_id": film_id}},
            *seek_stage,
            {
                "$sort": {
                    mongo_field: direction,
                    "_id": direction,
                }
            },
            {"$limit": page_size},
            *build_review_details_stages(),
        ]

    details_stages = build_review_details_stages()

    if mongo_field == "author_rating":
        details_stages.append(
            {"$set": {pagination_field: {"$ifNull": ["$author_rating", -1]}}}
        )

    pipeline = [
        {"$match": {"film_id": film_id}},
        *details_stages,
        *seek_stage,
        {
            "$sort": {
                pagination_field: direction,
                "_id": direction,
            }
        },
        {"$limit": page_size},
    ]

    if pagination_field != mongo_field:
        pipeline.append({"$unset": pagination_field})

    return pipeline
