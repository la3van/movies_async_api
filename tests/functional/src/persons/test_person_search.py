"""Функциональные тесты поиска и сортировки персон."""
import pytest
from http import HTTPStatus

from tests.functional.settings import test_settings

from tests.functional.utils.helpers import (
    build_expected_page,
)


@pytest.mark.parametrize(
    'query_data, matching_indices, expected_sort',
    [
        pytest.param(
            {},
            range(60),
            'full_name',
            id='default-parameters',
        ),
        pytest.param(
            {
                'page_number': 2,
                'page_size': 5,
            },
            range(60),
            'full_name',
            id='pagination',
        ),
        pytest.param(
            {
                'sort': '-full_name',
                'page_number': 2,
                'page_size': 5,
            },
            range(60),
            '-full_name',
            id='descending-sort',
        ),
        pytest.param(
            {
                'page_number': 2,
                'page_size': 1,
            },
            range(60),
            'full_name',
            id='minimum-page-size',
        ),
        pytest.param(
            {
                'page_number': 1,
                'page_size': 100,
            },
            range(60),
            'full_name',
            id='maximum-page-size',
        ),
        pytest.param(
            {
                'page_number': 2,
                'page_size': 100,
            },
            range(60),
            'full_name',
            id='page-out-of-range',
        ),
        pytest.param(
            {
                'query': 'Jason',
                'page_number': 2,
                'page_size': 2,
            },
            range(0, 60, 10),
            None,
            id='search-by-name',
        ),
        pytest.param(
            {
                'query': 'not-found',
                'sort': 'full_name',
                'page_number': 1,
                'page_size': 10,
            },
            [],
            'full_name',
            id='no-matches',
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

        assert response.status == HTTPStatus.OK
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

        assert first_response.status == HTTPStatus.OK
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

        assert second_response.status == HTTPStatus.OK
        assert second_body == expected_body
        assert second_body == first_body


@pytest.mark.parametrize(
    'query_data, parameter_name, expected_error_type',
    [
        pytest.param(
            {'query': ''},
            'query',
            'string_too_short',
            id='empty-query',
        ),
        pytest.param(
            {'sort': 'name'},
            'sort',
            'string_pattern_mismatch',
            id='unsupported-sort',
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
async def test_get_persons_with_invalid_query_parameters(
    query_data,
    parameter_name,
    expected_error_type,
    make_get_request,
) -> None:
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/persons/search',
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert len(body['detail']) == 1

        error = body['detail'][0]

        assert error['loc'] == ['query', parameter_name]
        assert error['type'] == expected_error_type
