"""Функциональные тесты эндпоинтов жанров."""
import pytest

from tests.functional.settings import test_settings

from tests.functional.testdata.responses import (
    genre_to_response,
)


@pytest.mark.parametrize(
    'genre_exists, expected_status',
    [
        (True, 200),
        (False, 404),
    ],
)
@pytest.mark.asyncio
async def test_get_genre_by_id(
    genre_exists,
    expected_status,
    genres_in_es,
    make_get_request,
) -> None:
    if genre_exists:
        genre = genres_in_es[0]
        genre_id = genre['uuid']
        expected_body = genre_to_response(genre)
    else:
        genre_id = '99999999-9999-9999-9999-999999999999'
        expected_body = {'detail': 'genre_not_found'}

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres/{genre_id}',
    )

    async with response:
        body = await response.json()

        assert response.status == expected_status
        assert body == expected_body


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
        assert first_response.status == 200
        await first_response.json()

    await es_delete_document(
        index=test_settings.es_genres_index,
        document_id=genre['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres/{genre["uuid"]}',
    )

    async with second_response:
        body = await second_response.json()

        assert second_response.status == 200
        assert body == genre_to_response(genre)


@pytest.mark.parametrize(
    'invalid_genre_id',
    [
        'non-valid-genre-id',
        '123456',
        'not-a-uuid',
    ],
)
@pytest.mark.asyncio
async def test_get_genre_by_invalid_id(
    invalid_genre_id,
    make_get_request,
) -> None:
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/genres/{invalid_genre_id}'
    )

    async with response:
        body = await response.json()

        assert response.status == 422

        assert 'detail' in body
        assert isinstance(body['detail'], list)
        assert body['detail'][0]['type'] == 'uuid_parsing'
