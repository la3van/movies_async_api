"""Функциональные тесты получения персоны по идентификатору."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings


@pytest.mark.asyncio
async def test_get_person_by_id(
    persons_in_es,
    make_get_request,
) -> None:
    person = persons_in_es[0]

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{person["uuid"]}',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == person


@pytest.mark.asyncio
async def test_get_person_from_redis(
    persons_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    person = persons_in_es[0]

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{person["uuid"]}',
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == person

    await es_delete_document(
        index=test_settings.es_persons_index,
        document_id=person['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{person["uuid"]}',
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == person
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_person_by_id_when_not_found(
    persons_in_es,
    make_get_request,
) -> None:
    missing_person_id = '99999999-9999-9999-9999-999999999999'

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{missing_person_id}',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body == {'detail': 'person_not_found'}


@pytest.mark.asyncio
async def test_get_person_by_invalid_id(
    make_get_request,
) -> None:
    invalid_person_id = 'not-a-uuid'

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/{invalid_person_id}'
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail'][0]['loc'] == ['path', 'person_id']
        assert body['detail'][0]['type'] == 'uuid_parsing'
