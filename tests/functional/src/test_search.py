"""Функциональные тесты поиска по фильмам, жанрам и персонам."""
import pytest

from tests.functional.settings import test_settings

from tests.functional.testdata.responses import (
    genre_to_response,
    movie_to_short_response,
)

from tests.functional.utils.helpers import (
    build_expected_page,
    build_expected_searched_movies,
)


@pytest.mark.parametrize(
    'query_data, matching_indices, expected_sort',
    [
        (
            {},
            range(60),
            'name',
        ),
        (
            {
                'page_number': 2,
                'page_size': 5,
            },
            range(60),
            'name',
        ),
        (
            {
                'sort': '-name',
                'page_number': 2,
                'page_size': 5,
            },
            range(60),
            '-name',
        ),
        (
            {
                'query': 'space',
                'page_number': 1,
                'page_size': 3,
            },
            range(0, 60, 10),
            None,
        ),
        (
            {
                'query': 'detective',
                'sort': 'name',
                'page_number': 2,
                'page_size': 2,
            },
            range(0, 60, 10),
            'name',
        ),
        (
            {
                'query': 'not-found',
                'sort': 'name',
                'page_number': 1,
                'page_size': 10,
            },
            [],
            'name',
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_genres_with_search(
    query_data,
    matching_indices,
    expected_sort,
    genres_in_es,
    make_get_request,
) -> None:
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres/',
        query_data=query_data,
    )

    if expected_sort is None:
        sort_field = None
        reverse = False
    else:
        sort_field = expected_sort.removeprefix('-')
        reverse = expected_sort.startswith('-')

    expected_body = build_expected_page(
        documents=genres_in_es,
        expected_indexes=matching_indices,
        sort_field=sort_field,
        reverse=reverse,
        page_number=query_data.get('page_number', 1),
        page_size=query_data.get('page_size', 50),
        response_builder=genre_to_response,
    )

    async with response:
        body = await response.json()

        assert response.status == 200
        assert body == expected_body


@pytest.mark.asyncio
async def test_get_genres_with_search_from_redis(
    genres_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    query_data = {
        'query': 'space',
        'sort': 'name',
        'page_number': 1,
        'page_size': 3,
    }

    matching_indices = range(0, 60, 10)

    expected_body = build_expected_page(
        documents=genres_in_es,
        expected_indexes=matching_indices,
        sort_field='name',
        reverse=False,
        page_number=1,
        page_size=3,
        response_builder=genre_to_response,
    )

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres',
        query_data=query_data,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == 200
        assert first_body == expected_body

    await es_delete_document(
        index=test_settings.es_genres_index,
        document_id=genres_in_es[20]['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres',
        query_data=query_data,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == 200
        assert second_body == expected_body
        assert second_body == first_body


@pytest.mark.parametrize(
    'query_data, matching_indices, expected_sort',
    [
        (
            {},
            range(60),
            'full_name',
        ),
        (
            {
                'page_number': 2,
                'page_size': 5,
            },
            range(60),
            'full_name',
        ),
        (
            {
                'sort': '-full_name',
                'page_number': 2,
                'page_size': 5,
            },
            range(60),
            '-full_name',
        ),
        (
            {
                'query': 'Jason',
                'page_number': 2,
                'page_size': 2,
            },
            range(0, 60, 10),
            None,
        ),
        (
            {
                'query': 'not-found',
                'sort': 'full_name',
                'page_number': 1,
                'page_size': 10,
            },
            [],
            'full_name',
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_persons_with_search(
    query_data,
    matching_indices,
    expected_sort,
    persons_in_es,
    make_get_request,
) -> None:
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/search',
        query_data=query_data,
    )

    if expected_sort is None:
        sort_field = None
        reverse = False
    else:
        sort_field = expected_sort.removeprefix('-')
        reverse = expected_sort.startswith('-')

    expected_body = build_expected_page(
        documents=persons_in_es,
        expected_indexes=matching_indices,
        sort_field=sort_field,
        reverse=reverse,
        page_number=query_data.get('page_number', 1),
        page_size=query_data.get('page_size', 50),
        response_builder=None,
    )

    async with response:
        body = await response.json()

        assert response.status == 200
        assert body == expected_body


@pytest.mark.asyncio
async def test_get_persons_with_search_from_redis(
    persons_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    query_data = {
        'query': 'Jason',
        'sort': 'full_name',
        'page_number': 2,
        'page_size': 2,
    }

    matching_indices = range(0, 60, 10)

    expected_body = build_expected_page(
        documents=persons_in_es,
        expected_indexes=matching_indices,
        sort_field='full_name',
        reverse=False,
        page_number=2,
        page_size=2,
        response_builder=None,
    )

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/search',
        query_data=query_data,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == 200
        assert first_body == expected_body

    await es_delete_document(
        index=test_settings.es_persons_index,
        document_id=persons_in_es[20]['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/search',
        query_data=query_data,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == 200
        assert second_body == expected_body
        assert second_body == first_body


@pytest.mark.parametrize(
    'query_data, expected_case',
    [
        (
            {
                'query': 'Space',
                'page_number': 1,
                'page_size': 50,
            },
            'title',
        ),
        (
            {
                'query': 'Detective',
                'page_number': 1,
                'page_size': 50,
            },
            'description',
        ),
        (
            {
                'query': 'Jason',
                'page_number': 1,
                'page_size': 50,
            },
            'person',
        ),
        (
            {
                'query': 'not-found',
                'page_number': 1,
                'page_size': 50,
            },
            'not_found',
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_searched_films(
    query_data,
    expected_case,
    movies_in_es,
    make_get_request,
) -> None:
    expected_movies = build_expected_searched_movies(
        movies=movies_in_es,
        expected_case=expected_case,
    )

    expected_body = {
        movie['uuid']: movie_to_short_response(movie)
        for movie in expected_movies
    }

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/search',
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        actual_body = {
            movie['uuid']: movie
            for movie in body
        }

        assert response.status == 200

        assert len(body) == len(actual_body)

        assert actual_body == expected_body


@pytest.mark.asyncio
async def test_get_searched_films_from_redis(
    movies_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    query_data = {
        'query': 'Space',
        'page_number': 1,
        'page_size': 3,
    }

    space_movie_ids = {
        movie['uuid']
        for movie in movies_in_es
        if 'Space' in movie['title']
    }

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/search',
        query_data=query_data,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == 200
        assert first_body
        assert len(first_body) == query_data['page_size']

        assert {
            movie['uuid']
            for movie in first_body
        }.issubset(space_movie_ids)

    await es_delete_document(
        index=test_settings.es_movies_index,
        document_id=first_body[0]['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/search',
        query_data=query_data,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == 200

        assert second_body == first_body
