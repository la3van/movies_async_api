"""Функциональные тесты списка, сортировки и фильтрации фильмов."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings

from tests.functional.test_data.responses import (
    movie_to_short_response,
)
from tests.functional.utils.helpers import (
    build_expected_page,
)


@pytest.mark.parametrize(
    'query_data, genre_index',
    [
        pytest.param(
            {},
            None,
            id='default-parameters',
        ),
        pytest.param(
            {
                'page_number': 2,
                'page_size': 5,
            },
            None,
            id='pagination',
        ),
        pytest.param(
            {
                'page_number': 2,
                'page_size': 1,
            },
            None,
            id='minimum-page-size',
        ),
        pytest.param(
            {
                'page_number': 1,
                'page_size': 100,
            },
            None,
            id='maximum-page-size',
        ),
        pytest.param(
            {
                'sort': 'imdb_rating',
                'page_number': 2,
                'page_size': 5,
            },
            None,
            id='ascending-sort',
        ),
        pytest.param(
            {
                'sort': '-imdb_rating',
                'page_number': 1,
                'page_size': 3,
            },
            1,
            id='genre-filter-and-descending-sort',
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_sorted_films(
    query_data,
    genre_index,
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

    expected_sort = query_data.get('sort', '-imdb_rating')
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

        assert response.status == HTTPStatus.OK
        assert body == expected_body


@pytest.mark.asyncio
async def test_get_sorted_films_when_page_out_of_range(
    movies_in_es,
    make_get_request,
) -> None:
    page_size = 1
    page_number = len(movies_in_es) + 1

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/',
        query_data={
            'page_number': page_number,
            'page_size': page_size,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == []


@pytest.mark.asyncio
async def test_get_sorted_films_when_genre_has_no_matches(
    movies_in_es,
    make_get_request,
) -> None:
    missing_genre_id = '99999999-9999-9999-9999-999999999999'

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/',
        query_data={'genre': missing_genre_id},
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == []


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

        assert first_response.status == HTTPStatus.OK
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

        assert second_response.status == HTTPStatus.OK
        assert second_body == expected_body
        assert second_body == first_body


@pytest.mark.parametrize(
    'query_data, parameter_name, expected_error_type',
    [
        pytest.param(
            {'sort': 'title'},
            'sort',
            'string_pattern_mismatch',
            id='unsupported-sort',
        ),
        pytest.param(
            {'genre': 'not-a-uuid'},
            'genre',
            'uuid_parsing',
            id='invalid-genre-uuid',
        ),
        pytest.param(
            {'page_number': 0},
            'page_number',
            'greater_than_equal',
            id='page-number-below-minimum',
        ),
        pytest.param(
            {'page_number': 'invalid'},
            'page_number',
            'int_parsing',
            id='page-number-invalid-type',
        ),
        pytest.param(
            {'page_size': 0},
            'page_size',
            'greater_than_equal',
            id='page-size-below-minimum',
        ),
        pytest.param(
            {'page_size': 101},
            'page_size',
            'less_than_equal',
            id='page-size-above-maximum',
        ),
        pytest.param(
            {'page_size': 'invalid'},
            'page_size',
            'int_parsing',
            id='page-size-invalid-type',
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_sorted_films_with_invalid_query_parameters(
    query_data,
    parameter_name,
    expected_error_type,
    make_get_request,
) -> None:
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/',
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert len(body['detail']) == 1

        error = body['detail'][0]

        assert error['loc'] == ['query', parameter_name]
        assert error['type'] == expected_error_type
