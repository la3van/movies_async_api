"""Функциональные тесты эндпоинтов фильмов."""
import pytest

from tests.functional.settings import test_settings

from tests.functional.testdata.responses import (
    movie_to_short_response,
)

from tests.functional.utils.helpers import (
    build_expected_page,
)


@pytest.mark.parametrize(
    "movie_exists, expected_status",
    [
        (True, 200),
        (False, 404),
    ],
)
@pytest.mark.asyncio
async def test_get_film_by_id(
    movie_exists,
    expected_status,
    movies_in_es,
    make_get_request,
) -> None:
    if movie_exists:
        movie = movies_in_es[0]
        movie_id = movie['uuid']
        expected_body = movie
    else:
        movie_id = '99999999-9999-9999-9999-999999999999'
        expected_body = {'detail': 'film_not_found'}

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/{movie_id}',
    )

    async with response:
        body = await response.json()

        assert response.status == expected_status
        assert body == expected_body


@pytest.mark.asyncio
async def test_get_film_from_redis(
    movies_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    movie = movies_in_es[0]

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/{movie["uuid"]}',
    )

    async with first_response:
        assert first_response.status == 200
        await first_response.json()

    await es_delete_document(
        index=test_settings.es_movies_index,
        document_id=movie['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/{movie["uuid"]}',
    )

    async with second_response:
        body = await second_response.json()

        assert second_response.status == 200
        assert body == movie


@pytest.mark.parametrize(
    'invalid_movie_id',
    [
        'non-valid-movie-id',
        '123456',
        'not-a-uuid',
    ],
)
@pytest.mark.asyncio
async def test_get_film_by_invalid_id(
    invalid_movie_id,
    make_get_request,
) -> None:
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/{invalid_movie_id}'
    )

    async with response:
        body = await response.json()

        assert response.status == 422

        assert 'detail' in body
        assert isinstance(body['detail'], list)
        assert body['detail'][0]['type'] == 'uuid_parsing'


@pytest.mark.parametrize(
    'query_data, genre_index, expected_sort',
    [
        (
            {},
            None,
            '-imdb_rating',
        ),
        (
            {
                'page_number': 2,
                'page_size': 5,
            },
            None,
            '-imdb_rating',
        ),
        (
            {
                'sort': 'imdb_rating',
                'page_number': 2,
                'page_size': 5,
            },
            None,
            'imdb_rating',
        ),
        (
            {
                'sort': '-imdb_rating',
                'page_number': 2,
                'page_size': 5,
            },
            None,
            '-imdb_rating',
        ),
        (
            {
                'sort': 'imdb_rating',
                'page_number': 1,
                'page_size': 3,
            },
            0,
            'imdb_rating',
        ),
        (
            {
                'sort': '-imdb_rating',
                'page_number': 1,
                'page_size': 3,
            },
            1,
            '-imdb_rating',
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_sorted_films(
    query_data,
    genre_index,
    expected_sort,
    movies_in_es,
    genre_documents,
    make_get_request,
) -> None:
    query_data = query_data.copy()

    if genre_index is None:
        matching_indices = range(len(movies_in_es))
    else:
        genre_uuid = genre_documents[genre_index]['uuid']
        query_data['genre'] = genre_uuid

        matching_indices = [
            index
            for index, movie in enumerate(movies_in_es)
            if any(
                genre['uuid'] == genre_uuid
                for genre in movie['genre']
            )
        ]

    sort_field = expected_sort.removeprefix('-')
    reverse = expected_sort.startswith('-')

    expected_body = build_expected_page(
        documents=movies_in_es,
        expected_indexes=matching_indices,
        sort_field=sort_field,
        reverse=reverse,
        page_number=query_data.get('page_number', 1),
        page_size=query_data.get('page_size', 50),
        response_builder=movie_to_short_response,
    )

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/',
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == 200
        assert body == expected_body


@pytest.mark.asyncio
async def test_get_sorted_films_from_redis(
    movies_in_es,
    genre_documents,
    es_delete_document,
    make_get_request,
) -> None:
    genre_uuid = genre_documents[1]['uuid']

    query_data = {
        'sort': '-imdb_rating',
        'genre': genre_uuid,
        'page_number': 1,
        'page_size': 3,
    }

    matching_indices = [
        index
        for index, movie in enumerate(movies_in_es)
        if any(
            genre['uuid'] == genre_uuid
            for genre in movie['genre']
        )
    ]

    expected_body = build_expected_page(
        documents=movies_in_es,
        expected_indexes=matching_indices,
        sort_field='imdb_rating',
        reverse=True,
        page_number=query_data['page_number'],
        page_size=query_data['page_size'],
        response_builder=movie_to_short_response,
    )

    assert expected_body

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/',
        query_data=query_data,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == 200
        assert first_body == expected_body

    await es_delete_document(
        index=test_settings.es_movies_index,
        document_id=expected_body[0]['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/',
        query_data=query_data,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == 200
        assert second_body == expected_body
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_similar_films_when_similar_found(
    movies_in_es,
    make_get_request,
) -> None:
    source_movie = movies_in_es[0]

    query_data = {
        'page_number': 1,
        'page_size': 5,
    }

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{source_movie["uuid"]}/similar'
        ),
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == 200
        assert body
        assert len(body) <= query_data['page_size']

        returned_movie_ids = {
            movie['uuid']
            for movie in body
        }

        assert source_movie['uuid'] not in returned_movie_ids

        movies_by_uuid = {
            movie['uuid']: movie
            for movie in movies_in_es
        }

        source_genre_ids = {
            genre['uuid']
            for genre in source_movie['genre']
        }

        for short_movie in body:
            full_movie = movies_by_uuid[short_movie['uuid']]

            assert short_movie == movie_to_short_response(
                full_movie,
            )

            similar_movie_genre_ids = {
                genre['uuid']
                for genre in full_movie['genre']
            }

            assert source_genre_ids & similar_movie_genre_ids


@pytest.mark.asyncio
async def test_get_similar_films_when_nothing_found(
    isolated_movie_in_es,
    make_get_request,
) -> None:
    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{isolated_movie_in_es["uuid"]}/similar'
        ),
        query_data={
            'page_number': 1,
            'page_size': 50,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == 200
        assert body == []


@pytest.mark.asyncio
async def test_get_similar_films_when_nothing_found_and_source_has_no_genres(
    movie_without_relations_in_es,
    make_get_request,
) -> None:
    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{movie_without_relations_in_es["uuid"]}/similar'
        ),
        query_data={
            'page_number': 1,
            'page_size': 50,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == 200
        assert body == []


@pytest.mark.asyncio
async def test_get_similar_films_from_redis(
    movies_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    source_movie = movies_in_es[0]

    query_data = {
        'page_number': 1,
        'page_size': 5,
    }

    url = (
        f'{test_settings.api_prefix}/films/'
        f'{source_movie["uuid"]}/similar'
    )

    first_response = await make_get_request(
        url=url,
        query_data=query_data,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == 200
        assert first_body

    await es_delete_document(
        index=test_settings.es_movies_index,
        document_id=first_body[0]['uuid'],
    )

    second_response = await make_get_request(
        url=url,
        query_data=query_data,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == 200

        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_similar_films_when_source_film_not_found(
    make_get_request,
) -> None:
    missing_film_id = (
        '99999999-9999-9999-9999-999999999999'
    )

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{missing_film_id}/similar'
        ),
        query_data={
            'page_number': 1,
            'page_size': 50,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == 200
        assert body == []
