"""Тестовые документы фильмов."""

import copy
from typing import Any

import pytest


@pytest.fixture(name="movie_documents", scope="session")
def movie_documents(
    person_documents: list[dict[str, Any]],
    genre_documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Формирует тестовые документы фильмов."""
    documents = []
    movie_number = 0
    for person in person_documents:
        person_info = {
            "uuid": person["uuid"],
            "full_name": person["full_name"],
        }

        for film_reference in person["films"]:
            roles = film_reference["roles"]

            primary_genre = genre_documents[
                movie_number % len(genre_documents)
            ]

            movie_genres = [
                {
                    "uuid": primary_genre["uuid"],
                    "name": primary_genre["name"],
                },
            ]

            if movie_number % 5 == 0:
                secondary_genre = genre_documents[
                    (movie_number + 1) % len(genre_documents)
                ]

                movie_genres.append(
                    {
                        "uuid": secondary_genre["uuid"],
                        "name": secondary_genre["name"],
                    },
                )

            documents.append(
                {
                    "uuid": film_reference["uuid"],
                    "title": (
                        f"Space Movie {movie_number:03d}"
                        if movie_number % 10 == 0
                        else f"Action Movie {movie_number:03d}"
                    ),
                    "imdb_rating": round(
                        5.0 + (movie_number % 50) / 10,
                        1,
                    ),
                    "description": (
                        f"Detective investigation {movie_number:03d}"
                        if movie_number % 15 == 0
                        else f"Epic battle story {movie_number:03d}"
                    ),
                    "genre": movie_genres,
                    "actors": (
                        [person_info.copy()] if "actor" in roles else []
                    ),
                    "writers": (
                        [person_info.copy()] if "writer" in roles else []
                    ),
                    "directors": (
                        [person_info.copy()] if "director" in roles else []
                    ),
                },
            )

            movie_number += 1

    return documents


@pytest.fixture(name="isolated_movie_document", scope="session")
def isolated_movie_document(
    movie_documents: dict[str, Any],
) -> dict[str, Any]:
    """Формирует фильм с уникальными содержимым и связями."""
    isolated_movie = copy.deepcopy(movie_documents[0])

    isolated_movie["uuid"] = "ffffffff-ffff-ffff-ffff-fffffffffff1"
    isolated_movie["title"] = "Completely Unique Isolated Film"
    isolated_movie["description"] = "Unrepeatable isolated description"

    return isolated_movie


@pytest.fixture(
    name="movies_without_matches_documents",
    scope="session",
)
def movies_without_matches_documents(
    isolated_movie_document: dict[str, Any],
    movie_documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Формирует фильмы для проверки отсутствия похожих результатов."""
    content_match_with_other_genre = copy.deepcopy(
        isolated_movie_document,
    )
    content_match_with_other_genre["uuid"] = (
        "ffffffff-ffff-ffff-ffff-fffffffffff3"
    )
    content_match_with_other_genre["genre"] = copy.deepcopy(
        movie_documents[2]["genre"],
    )

    unrelated_movie = copy.deepcopy(movie_documents[3])

    return [
        isolated_movie_document,
        content_match_with_other_genre,
        unrelated_movie,
    ]


@pytest.fixture(name="movie_without_relations_document", scope="session")
def movie_without_relations_document() -> dict[str, Any]:
    """Формирует фильм без жанров и связанных персон."""
    return {
        "uuid": "ffffffff-ffff-ffff-ffff-fffffffffff2",
        "title": "Movie Without Relations",
        "imdb_rating": None,
        "description": None,
        "genre": [],
        "actors": [],
        "writers": [],
        "directors": [],
    }


@pytest.fixture(name="similar_movies_documents", scope="session")
def similar_movies_documents() -> list[dict[str, Any]]:
    """Формирует детерминированные фильмы для проверки more_like_this."""
    matching_genre = {
        "uuid": "dddddddd-dddd-dddd-dddd-ddddddddddd1",
        "name": "Matching Genre",
    }
    other_genre = {
        "uuid": "dddddddd-dddd-dddd-dddd-ddddddddddd2",
        "name": "Other Genre",
    }

    source_movie = {
        "uuid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1",
        "title": "Nebulor Quasaris",
        "imdb_rating": 8.0,
        "description": "Cryovanta Zephyrium",
        "genre": [matching_genre],
        "actors": [],
        "writers": [],
        "directors": [],
    }

    content_and_genre_match = {
        "uuid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee2",
        "title": "Nebulor Quasaris",
        "imdb_rating": 9.0,
        "description": "Cryovanta Zephyrium",
        "genre": [matching_genre],
        "actors": [],
        "writers": [],
        "directors": [],
    }

    genre_only_match = {
        "uuid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee3",
        "title": "Granite Harbor",
        "imdb_rating": 7.0,
        "description": "Silent Orchard",
        "genre": [matching_genre],
        "actors": [],
        "writers": [],
        "directors": [],
    }

    content_only_match = {
        "uuid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee4",
        "title": "Nebulor Quasaris",
        "imdb_rating": 10.0,
        "description": "Cryovanta Zephyrium",
        "genre": [other_genre],
        "actors": [],
        "writers": [],
        "directors": [],
    }

    return [
        source_movie,
        content_and_genre_match,
        genre_only_match,
        content_only_match,
    ]
