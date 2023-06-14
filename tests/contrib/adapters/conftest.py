import pytest
from chasha import Chasha, DI


@pytest.fixture(scope='function')
def app_test_index(app: Chasha):
    @app.get('/')
    def index():
        return 'ok'
    yield app


@pytest.fixture(scope='function')
def app_test_query(app: Chasha):
    @app.get('/')
    def index(multi: list = app.di.query(), single: str = app.di.query()):
        assert multi == ['value1', 'value2']
        assert single == 'value'
        return 'ok'
    yield app


@pytest.fixture(scope='function')
def app_test_cookies(app: Chasha):
    @app.get('/')
    def index(cookies: DI.Cookies = app.di.cookies()):
        assert cookies.get('session_id') == '1'
        assert cookies.get('session_key') == 'secret'
        cookies.set('processed', 'true')
        cookies.set('key1', 'value1')
        return 'ok'
    yield app


@pytest.fixture(scope='function')
def app_test_body(app: Chasha):
    @app.get('/')
    def index(body: str = app.di.body()):
        assert body == 'content'
        return 'ok'
    yield app


@pytest.fixture(scope='function')
def app_test_no_body(app: Chasha):
    @app.get('/')
    def index(body: str = app.di.body()):
        assert body == ''
        return 'ok'
    yield app
