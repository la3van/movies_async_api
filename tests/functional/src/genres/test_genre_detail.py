"""Функциональные тесты получения жанра по идентификатору."""
import pytest
from http import HTTPStatus

from tests.functional.settings import test_settings

from tests.functional.testdata.responses import (
    genre_to_response,
)


@pytest.mark.asyncio
async def test_get_genre_by_id(
    genres_in_es,
    make_get_request,
) -> None:
    genre = genres_in_es[0]

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres/{genre["uuid"]}',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == genre_to_response(genre)


@pytest.mark.asyncio
async def test_get_genre_by_id_when_not_found(
    genres_in_es,
    make_get_request,
) -> None:
    missing_genre_id = '99999999-9999-9999-9999-999999999999'

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres/{missing_genre_id}',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body == {'detail': 'genre_not_found'}


@pytest.mark.asyncio
async def test_get_genre_from_redis(
    genres_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    genre = genres_in_es[0]

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres/{genre["uuid"]}',
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == genre_to_response(genre)

    await es_delete_document(
        index=test_settings.es_genres_index,
        document_id=genre['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres/{genre["uuid"]}',
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == genre_to_response(genre)
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_genre_by_invalid_id(
    make_get_request,
) -> None:
    invalid_genre_id = 'not-a-uuid'

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres/{invalid_genre_id}'
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail'][0]['loc'] == ['path', 'genre_id']
        assert body['detail'][0]['type'] == 'uuid_parsing'
