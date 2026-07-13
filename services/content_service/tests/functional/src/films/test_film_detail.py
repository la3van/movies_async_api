"""Функциональные тесты получения фильма по идентификатору."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings


@pytest.mark.asyncio
async def test_get_film_by_id(
    movies_in_es,
    make_get_request,
) -> None:
    movie = movies_in_es[0]

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/{movie["uuid"]}',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == movie


@pytest.mark.asyncio
async def test_get_film_by_id_without_relations(
    movie_without_relations_in_es,
    make_get_request,
) -> None:
    movie = movie_without_relations_in_es

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/{movie["uuid"]}',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == movie
        assert body['imdb_rating'] is None
        assert body['description'] is None
        assert body['genre'] == []
        assert body['actors'] == []
        assert body['writers'] == []
        assert body['directors'] == []


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
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == movie

    await es_delete_document(
        index=test_settings.es_movies_index,
        document_id=movie['uuid'],
    )

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/{movie["uuid"]}',
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == movie
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_film_by_id_when_not_found(
    movies_in_es,
    make_get_request,
) -> None:
    missing_movie_id = '99999999-9999-9999-9999-999999999999'

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/{missing_movie_id}'
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body == {'detail': 'film_not_found'}


@pytest.mark.asyncio
async def test_get_film_by_invalid_id(
    make_get_request,
) -> None:
    invalid_movie_id = 'not-a-uuid'

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/films/{invalid_movie_id}'
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail'][0]['loc'] == ['path', 'film_id']
        assert body['detail'][0]['type'] == 'uuid_parsing'
