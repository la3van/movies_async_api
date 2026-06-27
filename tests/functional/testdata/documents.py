import copy
import pytest
import uuid
import random


@pytest.fixture(name='movie_documents', scope='session')
def movie_documents(
    person_documents: list[dict],
    genre_documents: list[dict],
) -> list[dict]:
    documents = []
    movie_number = 0
    for person in person_documents:
        person_info = {
            'uuid': person['uuid'],
            'full_name': person['full_name'],
        }

        for film_reference in person['films']:
            roles = film_reference['roles']

            primary_genre = genre_documents[
                movie_number % len(genre_documents)
            ]

            movie_genres = [
                {
                    'uuid': primary_genre['uuid'],
                    'name': primary_genre['name'],
                },
            ]

            if movie_number % 5 == 0:
                secondary_genre = genre_documents[
                    (movie_number + 1) % len(genre_documents)
                ]

                movie_genres.append(
                    {
                        'uuid': secondary_genre['uuid'],
                        'name': secondary_genre['name'],
                    },
                )

            documents.append(
                {
                    'uuid': film_reference['uuid'],

                    'title': (
                        f'Space Movie {movie_number:03d}'
                        if movie_number % 10 == 0
                        else f'Action Movie {movie_number:03d}'
                    ),

                    'imdb_rating': round(
                        5.0 + (movie_number % 50) / 10,
                        1,
                    ),

                    'description': (
                        f'Detective investigation {movie_number:03d}'
                        if movie_number % 15 == 0
                        else f'Epic battle story {movie_number:03d}'
                    ),

                    'genre': movie_genres,

                    'actors': (
                        [person_info.copy()]
                        if 'actor' in roles
                        else []
                    ),

                    'writers': (
                        [person_info.copy()]
                        if 'writer' in roles
                        else []
                    ),

                    'directors': (
                        [person_info.copy()]
                        if 'director' in roles
                        else []
                    ),
                },
            )

            movie_number += 1

    return documents


@pytest.fixture(name='isolated_movie_document', scope='session')
def isolated_movie_document(
    movie_documents,
) -> list[dict]:
    isolated_movie = copy.deepcopy(movie_documents[0])

    isolated_movie['uuid'] = (
        'ffffffff-ffff-ffff-ffff-fffffffffff1'
    )
    isolated_movie['title'] = (
        'Completely Unique Isolated Film'
    )
    isolated_movie['description'] = (
        'Unrepeatable isolated description'
    )

    return isolated_movie


@pytest.fixture(name='movie_without_relations_document', scope='session')
def movie_without_relations_document() -> dict:
    return {
        'uuid': 'ffffffff-ffff-ffff-ffff-fffffffffff2',
        'title': 'Movie Without Relations',
        'imdb_rating': None,
        'description': None,
        'genre': [],
        'actors': [],
        'writers': [],
        'directors': [],
    }


@pytest.fixture(name='genre_documents', scope='session')
def genre_documents() -> list[dict]:
    return [
        {
            'uuid': str(uuid.UUID(int=number + 1)),
            'name': (
                f'Space Genre {number:02d}'
                if number % 10 == 0
                else f'Action Genre {number:02d}'
            ),
            'description': (
                f'Detective stories {number:02d}'
                if number % 10 == 0
                else f'Epic battles {number:02d}'
            ),
        }
        for number in range(60)
    ]


@pytest.fixture(name='person_documents', scope='session')
def person_documents() -> list[dict]:
    rng = random.Random(42)

    return [
        {
            'uuid': str(uuid.UUID(int=person_number + 1)),
            'full_name': (
                f'Jason full_name {person_number:02d}'
                if person_number % 10 == 0
                else f'Erik full_name {person_number:02d}'
            ),
            'films': [
                {
                    'uuid': str(uuid.UUID(
                        int=person_number * 10 + film_number + 1)
                    ),
                    'roles': rng.sample(
                        ['actor', 'writer', 'director'],
                        k=rng.randint(1, 3),
                    ),
                }
                for film_number in range(rng.randint(1, 10))
            ],
        }
        for person_number in range(60)
    ]
