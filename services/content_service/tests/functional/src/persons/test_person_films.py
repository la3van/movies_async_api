"""Функциональные тесты получения фильмов персоны."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.responses import (
    movie_to_short_response,
)
from tests.functional.utils.helpers import (
    build_expected_page,
)


@pytest.mark.asyncio
async def test_get_person_films(
    persons_in_es,
    movies_in_es,
    make_get_request,
) -> None:
    person = persons_in_es[0]

    person_film_ids = {
        film['uuid']
        for film in person['films']
    }

    expected_indices = [
        index
        for index, movie in enumerate(movies_in_es)
        if movie['uuid'] in person_film_ids
    ]

    expected_body = build_expected_page(
        documents=movies_in_es,
        expected_indexes=expected_indices,
        sort_field='imdb_rating',
        reverse=True,
        page_number=1,
        page_size=50,
        response_builder=movie_to_short_response,
    )

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/persons/{person["uuid"]}/films'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == expected_body


@pytest.mark.parametrize(
    'page_number, page_size',
    [
        pytest.param(
            2,
            1,
            id='minimum-page-size-and-second-page',
        ),
        pytest.param(
            1,
            100,
            id='maximum-page-size',
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_person_films_with_pagination(
    page_number,
    page_size,
    persons_in_es,
    movies_in_es,
    make_get_request,
) -> None:
    movies_by_uuid = {
        movie['uuid']: index
        for index, movie in enumerate(movies_in_es)
    }

    persons_with_movies = []

    for person in persons_in_es:
        expected_indices = [
            movies_by_uuid[film['uuid']]
            for film in person['films']
            if film['uuid'] in movies_by_uuid
        ]

        if len(expected_indices) >= 2:
            persons_with_movies.append(
                (person, expected_indices),
            )

    assert persons_with_movies, (
        'Test data must contain a person with at least two existing films'
    )

    person, expected_indices = persons_with_movies[0]

    expected_body = build_expected_page(
        documents=movies_in_es,
        expected_indexes=expected_indices,
        sort_field='imdb_rating',
        reverse=True,
        page_number=page_number,
        page_size=page_size,
        response_builder=movie_to_short_response,
    )

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/persons/{person["uuid"]}/films'
        ),
        query_data={
            'page_number': page_number,
            'page_size': page_size,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == expected_body


@pytest.mark.asyncio
async def test_get_person_films_when_page_out_of_range(
    persons_in_es,
    movies_in_es,
    make_get_request,
) -> None:
    movie_ids = {
        movie['uuid']
        for movie in movies_in_es
    }

    person = next(
        person
        for person in persons_in_es
        if any(
            film['uuid'] in movie_ids
            for film in person['films']
        )
    )

    existing_film_count = sum(
        film['uuid'] in movie_ids
        for film in person['films']
    )

    page_size = 1
    page_number = existing_film_count + 1

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/persons/{person["uuid"]}/films'
        ),
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
async def test_get_person_films_when_person_has_no_existing_films(
    persons_in_es,
    movies_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    movies_by_uuid = {
        movie['uuid']: movie
        for movie in movies_in_es
    }

    person = next(
        person
        for person in persons_in_es
        if any(
            film['uuid'] in movies_by_uuid
            for film in person['films']
        )
    )

    existing_person_film_ids = {
        film['uuid']
        for film in person['films']
        if film['uuid'] in movies_by_uuid
    }

    assert existing_person_film_ids

    for film_id in existing_person_film_ids:
        await es_delete_document(
            index=test_settings.es_movies_index,
            document_id=film_id,
        )

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/persons/{person["uuid"]}/films'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == []


@pytest.mark.asyncio
async def test_get_person_films_from_redis(
    persons_in_es,
    movies_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    person = persons_in_es[0]

    person_film_ids = {
        film['uuid']
        for film in person['films']
    }

    expected_indices = [
        index
        for index, movie in enumerate(movies_in_es)
        if movie['uuid'] in person_film_ids
    ]

    expected_body = build_expected_page(
        documents=movies_in_es,
        expected_indexes=expected_indices,
        sort_field='imdb_rating',
        reverse=True,
        page_number=1,
        page_size=50,
        response_builder=movie_to_short_response,
    )

    assert expected_indices
    assert expected_body

    url = (
        f'{test_settings.api_prefix}'
        f'/persons/{person["uuid"]}/films'
    )

    first_response = await make_get_request(url=url)

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == expected_body

    movie_to_delete = movies_in_es[expected_indices[0]]

    await es_delete_document(
        index=test_settings.es_movies_index,
        document_id=movie_to_delete['uuid'],
    )

    second_response = await make_get_request(url=url)

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == expected_body
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_person_films_when_person_id_not_found(
    persons_in_es,
    make_get_request,
) -> None:
    missing_person_id = '99999999-9999-9999-9999-999999999999'

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/persons/{missing_person_id}/films'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body == {'detail': 'person_not_found'}


@pytest.mark.asyncio
async def test_get_person_films_by_invalid_id(
    make_get_request,
) -> None:
    invalid_person_id = 'not-a-uuid'

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{invalid_person_id}/films'
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail'][0]['loc'] == ['path', 'person_id']
        assert body['detail'][0]['type'] == 'uuid_parsing'


@pytest.mark.parametrize(
    'query_data, parameter_name, expected_error_type',
    [
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
async def test_get_person_films_with_invalid_query_parameters(
    query_data,
    parameter_name,
    expected_error_type,
    make_get_request,
) -> None:
    valid_person_id = '99999999-9999-9999-9999-999999999999'

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/persons/{valid_person_id}/films'
        ),
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert len(body['detail']) == 1

        error = body['detail'][0]

        assert error['loc'] == ['query', parameter_name]
        assert error['type'] == expected_error_type
