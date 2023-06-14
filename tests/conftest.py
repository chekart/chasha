import pytest
from chasha import Chasha, Request, Response


class TestAdapter:
    def adapt_request(self, **event):
        return Request(
            method=event['method'],
            query=event.get('query', {}),
            headers=event.get('headers', {}),
            path=event.get('path', '/'),
            body=event.get('body', ''),
            raw=event
        )

    def adapt_response(self, response: Response):
        return response


@pytest.fixture(scope='function')
def test_adapter():
    return TestAdapter()


@pytest.fixture(scope='function')
def app_request():
    def create(**event):
        return Request(
            method=event['method'],
            query=event.get('query', {}),
            headers=event.get('headers', {}),
            path=event.get('path', '/'),
            body=event.get('body', ''),
            raw=event
        )
    return create


@pytest.fixture(scope="function")
def app():
    return Chasha()
