import pytest

from tests.functional.settings import test_settings

from tests.functional.testdata.responses import (
    movie_to_short_response,
)

from tests.functional.utils.helpers import (
    build_expected_page,
)


@pytest.mark.parametrize(
    'person_exists, expected_status',
    [
        (True, 200),
        (False, 404),
    ]
)
@pytest.mark.asyncio
async def test_get_person_by_id(
    person_exists,
    expected_status,
    persons_in_es,
    make_get_request,
):
    if person_exists:
        person = persons_in_es[0]
        person_id = person['uuid']
        expected_body = person
    else:
        person_id = '99999999-9999-9999-9999-999999999999'
        expected_body = {'detail': 'person_not_found'}

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{person_id}',
    )

    print(person_id, persons_in_es[0]['uuid'])

    async with response:
        body = await response.json()

        assert response.status == expected_status
        assert body == expected_body


@pytest.mark.asyncio
async def test_get_person_from_redis(
    persons_in_es,
    es_delete_document,
    make_get_request,
):
    person = persons_in_es[0]

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{person["uuid"]}',
    )

    async with first_response:
        assert first_response.status == 200
        await first_response.json()

    await es_delete_document(
        index=test_settings.es_persons_index,
        document_id=person['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{person["uuid"]}',
    )

    async with second_response:
        body = await second_response.json()

        assert second_response.status == 200
        assert body == person


@pytest.mark.parametrize(
    'invalid_person_id',
    [
        'non-valid-person-id',
        '123456',
        'not-a-uuid',
    ],
)
@pytest.mark.asyncio
async def test_get_person_by_invalid_id(
    invalid_person_id,
    make_get_request,
):
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{invalid_person_id}'
    )

    async with response:
        body = await response.json()

        assert response.status == 422

        assert 'detail' in body
        assert isinstance(body['detail'], list)
        assert body['detail'][0]['type'] == 'uuid_parsing'


@pytest.mark.parametrize(
    'query_data, person_exists, expected_status',
    [
        (
            {
                'page_number': 1,
                'page_size': 50,
            },
            True,
            200,
        ),
        (
            {
                'page_number': 1,
                'page_size': 50,
            },
            False,
            404,
        ),
    ]
)
@pytest.mark.asyncio
async def test_get_person_films(
    query_data,
    person_exists,
    expected_status,
    persons_in_es,
    movies_in_es,
    make_get_request,
):
    if person_exists:
        person = persons_in_es[0]
        person_id = person['uuid']

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
            page_number=query_data.get('page_number', 1),
            page_size=query_data.get('page_size', 50),
            response_builder=movie_to_short_response,
        )
    else:
        person_id = '99999999-9999-9999-9999-999999999999'
        expected_body = {'detail': 'person_not_found'}

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{person_id}/films',
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == expected_status
        assert body == expected_body


@pytest.mark.asyncio
async def test_get_person_films_from_redis(
    persons_in_es,
    movies_in_es,
    es_delete_document,
    make_get_request,
):
    person = persons_in_es[0]
    person_id = person['uuid']

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

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{person["uuid"]}/films',
    )

    async with first_response:
        assert first_response.status == 200
        await first_response.json()

    await es_delete_document(
        index=test_settings.es_persons_index,
        document_id=person_id,
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{person["uuid"]}/films',
    )

    async with second_response:
        body = await second_response.json()

        assert second_response.status == 200
        assert body == expected_body


@pytest.mark.parametrize(
    'invalid_person_id',
    [
        'non-valid-person-id',
        '123456',
        'not-a-uuid',
    ],
)
@pytest.mark.asyncio
async def test_get_person_films_by_invalid_id(
    invalid_person_id,
    make_get_request,
):
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{invalid_person_id}/films'
    )

    async with response:
        body = await response.json()

        assert response.status == 422

        assert 'detail' in body
        assert isinstance(body['detail'], list)
        assert body['detail'][0]['type'] == 'uuid_parsing'
