import time

from urllib.parse import urlsplit
from elasticsearch import Elasticsearch
from tests.functional.settings import test_settings


def wait_for_elastic() -> None:
    deadline = time.monotonic() + test_settings.elastic_wait_timeout

    with Elasticsearch(
        hosts=[test_settings.elastic_url],
        request_timeout=test_settings.elastic_request_timeout,
    ) as elastic_client:
        while time.monotonic() < deadline:
            if elastic_client.ping():
                return

            time.sleep(test_settings.elastic_wait_interval)

    raise RuntimeError(
        'Elasticsearch did not become available within '
        f'{test_settings.elastic_wait_timeout} seconds.',
    )


if __name__ == '__main__':
    parsed_url = urlsplit(test_settings.elastic_url)

    print('URL:', repr(test_settings.elastic_url))
    print('scheme:', repr(parsed_url.scheme))
    print('hostname:', repr(parsed_url.hostname))
    print('port:', repr(parsed_url.port))

    wait_for_elastic()
