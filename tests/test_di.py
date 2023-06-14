from chasha import Chasha, Request


def test_di(app: Chasha, app_request):
    def dependency():
        yield 'test'

    def dependency2():
        yield 42

    @app.route('/')
    def index(param1: tuple = ('some', 'param'),
              value: str = app.di.inject(dependency),
              value2: int = app.di.inject(dependency2)):
        assert value == 'test'
        assert value2 == 42
        assert param1 == ('some', 'param')
        return 'ok'

    response = app.serve(app_request(method='get'))
    assert response.body == 'ok'


def test_dependency_in_dependency(app: Chasha, app_request):
    def dependency1():
        yield 'dep1'

    def dependency2(dep: str = app.di.inject(dependency1)):
        yield dep + 'dep2'

    @app.route('/')
    def index(value: str = app.di.inject(dependency2)):
        assert value == 'dep1dep2'
        return 'ok'

    response = app.serve(app_request(method='get'))
    assert response.body == 'ok'


def test_request(app: Chasha, app_request):
    headers = {'test': 'test'}

    @app.route('/')
    def index(value: Request = app.di.request()):
        assert isinstance(value, Request)
        assert dict(value.headers) == headers
        return 'ok'

    response = app.serve(app_request(method='get', headers=headers))
    assert response.body == 'ok'


def test_body(app: Chasha, app_request):
    body = '{"status": "ok"}'

    @app.route('/')
    def index(value_str: str = app.di.body(), value_dict: dict = app.di.json_body()):
        assert isinstance(value_str, str)
        assert isinstance(value_dict, dict)
        assert value_str == body
        assert value_dict == {'status': 'ok'}
        return 'ok'

    response = app.serve(app_request(method='get', body=body))
    assert response.body == 'ok'


def test_empty_json_body(app: Chasha, app_request):
    @app.route('/')
    def index(_: dict = app.di.json_body()):
        return 'ok'

    response = app.serve(app_request(method='get', body=''))
    assert response.status_code == 400
    assert 'Failed to load payload' in response.body
