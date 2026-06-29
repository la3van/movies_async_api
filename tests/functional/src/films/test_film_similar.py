from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.testdata.responses import (
    movie_to_short_response,
)
from tests.functional.utils.helpers import (
    build_expected_page,
)


@pytest.mark.asyncio
async def test_get_similar_films_by_content_and_genres(
    similar_movies_in_es,
    make_get_request,
) -> None:
    source_movie = similar_movies_in_es[0]
    content_and_genre_match = similar_movies_in_es[1]
    genre_only_match = similar_movies_in_es[2]
    content_only_match = similar_movies_in_es[3]

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{source_movie["uuid"]}/similar'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == [
            movie_to_short_response(content_and_genre_match),
        ]

        returned_movie_ids = {
            movie['uuid']
            for movie in body
        }

        assert source_movie['uuid'] not in returned_movie_ids
        assert genre_only_match['uuid'] not in returned_movie_ids
        assert content_only_match['uuid'] not in returned_movie_ids


@pytest.mark.asyncio
async def test_get_similar_films_by_genres_when_content_match_not_found(
    movies_with_isolated_movie_in_es,
    movie_documents,
    make_get_request,
) -> None:
    source_movie = movies_with_isolated_movie_in_es

    source_genre_ids = {
        genre['uuid']
        for genre in source_movie['genre']
    }

    matching_indices = [
        index
        for index, movie in enumerate(movie_documents)
        if source_genre_ids
        & {
            genre['uuid']
            for genre in movie['genre']
        }
    ]

    expected_body = build_expected_page(
        documents=movie_documents,
        expected_indexes=matching_indices,
        sort_field='imdb_rating',
        reverse=True,
        page_number=1,
        page_size=50,
        response_builder=movie_to_short_response,
    )

    assert source_genre_ids
    assert expected_body

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{source_movie["uuid"]}/similar'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == expected_body


@pytest.mark.asyncio
async def test_get_similar_films_when_no_matches_found(
    movies_without_matches_in_es,
    make_get_request,
) -> None:
    source_movie = movies_without_matches_in_es[0]
    content_match_with_other_genre = movies_without_matches_in_es[1]
    unrelated_movie = movies_without_matches_in_es[2]

    document_ids = {
        movie['uuid']
        for movie in movies_without_matches_in_es
    }

    assert len(document_ids) == len(movies_without_matches_in_es)

    source_genre_ids = {
        genre['uuid']
        for genre in source_movie['genre']
    }

    content_match_genre_ids = {
        genre['uuid']
        for genre in content_match_with_other_genre['genre']
    }

    unrelated_genre_ids = {
        genre['uuid']
        for genre in unrelated_movie['genre']
    }

    assert source_genre_ids
    assert (
        source_movie['title']
        == content_match_with_other_genre['title']
    )
    assert (
        source_movie['description']
        == content_match_with_other_genre['description']
    )
    assert source_genre_ids.isdisjoint(
        content_match_genre_ids,
    )
    assert source_genre_ids.isdisjoint(
        unrelated_genre_ids,
    )

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{source_movie["uuid"]}/similar'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == []


@pytest.mark.asyncio
async def test_get_similar_films_when_source_has_no_genres(
    movie_without_relations_in_es,
    make_get_request,
) -> None:
    assert movie_without_relations_in_es['genre'] == []

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{movie_without_relations_in_es["uuid"]}/similar'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == []


@pytest.mark.parametrize(
    'page_number, page_size',
    [
        pytest.param(
            1,
            1,
            id='minimum-page-size-first-page',
        ),
        pytest.param(
            2,
            1,
            id='minimum-page-size-second-page',
        ),
        pytest.param(
            1,
            100,
            id='maximum-page-size',
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_similar_films_with_pagination(
    page_number,
    page_size,
    movies_with_isolated_movie_in_es,
    movie_documents,
    make_get_request,
) -> None:
    source_movie = movies_with_isolated_movie_in_es

    source_genre_ids = {
        genre['uuid']
        for genre in source_movie['genre']
    }

    matching_indices = [
        index
        for index, movie in enumerate(movie_documents)
        if source_genre_ids
        & {
            genre['uuid']
            for genre in movie['genre']
        }
    ]

    expected_body = build_expected_page(
        documents=movie_documents,
        expected_indexes=matching_indices,
        sort_field='imdb_rating',
        reverse=True,
        page_number=page_number,
        page_size=page_size,
        response_builder=movie_to_short_response,
    )

    assert expected_body

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{source_movie["uuid"]}/similar'
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
async def test_get_similar_films_when_page_out_of_range(
    movies_with_isolated_movie_in_es,
    movie_documents,
    make_get_request,
) -> None:
    source_movie = movies_with_isolated_movie_in_es

    source_genre_ids = {
        genre['uuid']
        for genre in source_movie['genre']
    }

    matching_film_count = sum(
        bool(
            source_genre_ids
            & {
                genre['uuid']
                for genre in movie['genre']
            }
        )
        for movie in movie_documents
    )

    assert matching_film_count

    page_size = 1
    page_number = matching_film_count + 1

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{source_movie["uuid"]}/similar'
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
async def test_get_similar_films_from_redis(
    movies_in_es,
    es_delete_document,
    make_get_request,
) -> None:
    movie = movies_in_es[0]

    url = (
        f'{test_settings.api_prefix}/films/'
        f'{movie["uuid"]}/similar'
    )

    first_response = await make_get_request(url=url)

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body

    await es_delete_document(
        index=test_settings.es_movies_index,
        document_id=first_body[0]['uuid'],
    )

    second_response = await make_get_request(url=url)

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_similar_films_when_source_film_not_found(
    movies_in_es,
    make_get_request,
) -> None:
    missing_film_id = '99999999-9999-9999-9999-999999999999'

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{missing_film_id}/similar'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body == {'detail': 'film_not_found'}


@pytest.mark.asyncio
async def test_get_similar_films_by_invalid_id(
    make_get_request,
) -> None:
    invalid_film_id = 'not-a-uuid'

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{invalid_film_id}/similar'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail'][0]['loc'] == ['path', 'film_id']
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
async def test_get_similar_films_with_invalid_query_parameters(
    query_data,
    parameter_name,
    expected_error_type,
    make_get_request,
) -> None:
    film_id = '99999999-9999-9999-9999-999999999999'

    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}/films/'
            f'{film_id}/similar'
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
