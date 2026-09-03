"""Aggregation pipelines для обогащения и сортировки рецензий."""


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
                                    "$cond": [{"$eq": ["$value", 1]}, 1, 0]
                                }
                            },
                            "dislikes": {
                                "$sum": {
                                    "$cond": [{"$eq": ["$value", -1]}, 1, 0]
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
                "likes": {"$ifNull": [{"$first": "$reaction_stats.likes"}, 0]},
                "dislikes": {
                    "$ifNull": [{"$first": "$reaction_stats.dislikes"}, 0]
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
    page_number: int,
    page_size: int,
) -> list[dict]:
    """Построить список рецензий с разрешённой сортировкой."""
    descending = sort.startswith("-")
    field_name = sort[1:] if descending else sort
    mongo_field = sort_fields[field_name]
    direction = -1 if descending else 1
    return [
        {"$match": {"film_id": film_id}},
        *build_review_details_stages(),
        {"$sort": {mongo_field: direction, "_id": direction}},
        {"$skip": (page_number - 1) * page_size},
        {"$limit": page_size},
    ]
