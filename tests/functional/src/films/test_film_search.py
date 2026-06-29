"""Функциональные тесты поиска фильмов."""
import pytest
from http import HTTPStatus

from tests.functional.settings import test_settings

from tests.functional.testdata.responses import (
    movie_to_short_response,
)

from tests.functional.utils.helpers import (
    build_expected_searched_movies,
)


@pytest.mark.parametrize(
    'query_data, expected_case',
    [
        pytest.param(
            {
                'query': 'Space',
                'page_number': 1,
                'page_size': 50,
            },
            'title',
            id='search-by-title',
        ),
        pytest.param(
            {
                'query': 'Detective',
                'page_number': 1,
                'page_size': 50,
            },
            'description',
            id='search-by-description',
        ),
        pytest.param(
            {
                'query': 'Jason',
                'page_number': 1,
                'page_size': 50,
            },
            'person',
            id='search-by-person',
        ),
        pytest.param(
            {
                'query': 'not-found',
                'page_number': 1,
                'page_size': 50,
            },
            'not_found',
            id='no-matches',
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

        assert response.status == HTTPStatus.OK
        assert len(body) == len(actual_body)
        assert actual_body == expected_body


@pytest.mark.asyncio
async def test_get_searched_films_with_minimum_page_size(
    movies_in_es,
    make_get_request,
) -> None:
    matching_movie_ids = {
        movie['uuid']
        for movie in build_expected_searched_movies(
            movies=movies_in_es,
            expected_case='title',
        )
    }

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/search',
        query_data={
            'query': 'Space',
            'page_number': 1,
            'page_size': 1,
        },
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert len(first_body) == 1
        assert first_body[0]['uuid'] in matching_movie_ids

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/search',
        query_data={
            'query': 'Space',
            'page_number': 2,
            'page_size': 1,
        },
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert len(second_body) == 1
        assert second_body[0]['uuid'] in matching_movie_ids
        assert second_body[0]['uuid'] != first_body[0]['uuid']


@pytest.mark.asyncio
async def test_get_searched_films_with_maximum_page_size(
    movies_in_es,
    make_get_request,
) -> None:
    expected_movie_ids = {
        movie['uuid']
        for movie in build_expected_searched_movies(
            movies=movies_in_es,
            expected_case='title',
        )
    }

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/search',
        query_data={
            'query': 'Space',
            'page_number': 1,
            'page_size': 100,
        },
    )

    async with response:
        body = await response.json()

        actual_movie_ids = {
            movie['uuid']
            for movie in body
        }

        assert response.status == HTTPStatus.OK
        assert len(body) == len(actual_movie_ids)
        assert actual_movie_ids == expected_movie_ids


@pytest.mark.asyncio
async def test_get_searched_films_when_page_out_of_range(
    movies_in_es,
    make_get_request,
) -> None:
    matching_movies = build_expected_searched_movies(
        movies=movies_in_es,
        expected_case='title',
    )

    page_size = 1
    page_number = len(matching_movies) + 1

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/search',
        query_data={
            'query': 'Space',
            'page_number': page_number,
            'page_size': page_size,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == []


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

        assert first_response.status == HTTPStatus.OK
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

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


@pytest.mark.parametrize(
    'query_data, parameter_name, expected_error_type',
    [
        pytest.param(
            {},
            'query',
            'missing',
            id='missing-query',
        ),
        pytest.param(
            {'query': ''},
            'query',
            'string_too_short',
            id='empty-query',
        ),
        pytest.param(
            {
                'query': 'Space',
                'page_number': 0,
            },
            'page_number',
            'greater_than_equal',
            id='page-number-below-minimum',
        ),
        pytest.param(
            {
                'query': 'Space',
                'page_number': 'invalid',
            },
            'page_number',
            'int_parsing',
            id='page-number-invalid-type',
        ),
        pytest.param(
            {
                'query': 'Space',
                'page_size': 0,
            },
            'page_size',
            'greater_than_equal',
            id='page-size-below-minimum',
        ),
        pytest.param(
            {
                'query': 'Space',
                'page_size': 101,
            },
            'page_size',
            'less_than_equal',
            id='page-size-above-maximum',
        ),
        pytest.param(
            {
                'query': 'Space',
                'page_size': 'invalid',
            },
            'page_size',
            'int_parsing',
            id='page-size-invalid-type',
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_searched_films_with_invalid_query_parameters(
    query_data,
    parameter_name,
    expected_error_type,
    make_get_request,
) -> None:
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/search',
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert len(body['detail']) == 1

        error = body['detail'][0]

        assert error['loc'] == ['query', parameter_name]
        assert error['type'] == expected_error_type
