import json
from chasha import Chasha, DI, Request, HttpNotFound, HttpRedirect


def test_ok(app: Chasha, app_request):
    @app.route('/')
    def index():
        return 'ok'

    response = app.serve(app_request(method='get'))
    assert response.status_code == 200
    assert response.get_single_header('Content-Type') == 'text/plain'
    assert response.body == 'ok'


def test_json(app: Chasha, app_request):
    @app.route('/')
    def index():
        return {'status': 'ok'}

    response = app.serve(app_request(method='get'))
    assert response.status_code == 200
    assert response.get_single_header('Content-Type') == 'application/json'
    assert isinstance(response.body, str)
    assert json.loads(response.body) == {'status': 'ok'}


def test_html(app: Chasha, app_request):
    @app.route('/')
    def index():
        return app.html('<html></html>')

    response = app.serve(app_request(method='get'))
    assert response.status_code == 200
    assert response.get_single_header('Content-Type') == 'text/html'
    assert response.body == '<html></html>'


def test_headers(app: Chasha, app_request):
    @app.route('/')
    def index(request: Request = app.di.request()):
        assert request.get_header('cAsE') == 'value'
        return 'ok'

    response = app.serve(app_request(method='get', headers={'CaSe': 'value'}))
    assert response.status_code == 200
    assert response.body == 'ok'


def test_cookies(app: Chasha, app_request):
    @app.route('/')
    def index(cookies: DI.Cookies = app.di.cookies()):
        assert cookies.get('test1') == 'value1'
        assert cookies.get('test2') == 'value2'
        cookies.set('param1', 'value1')
        cookies.set('param2', 'value2', http_only=True)
        return 'ok'

    response = app.serve(app_request(method='get', headers={'cookie': 'test1=value1; test2=value2'}))
    assert response.status_code == 200
    assert response.get_header('set-cookie') == ['param1=value1; Path=/', 'param2=value2; HttpOnly; Path=/']
    assert response.body == 'ok'


def test_redirect(app: Chasha, app_request):
    @app.route('/')
    def index():
        raise HttpRedirect('localhost')

    response = app.serve(app_request(method='get'))
    assert response.status_code == 307
    assert response.get_single_header('Content-Type') == 'text/plain'
    assert response.get_single_header('Location') == 'localhost'


def test_not_found(app: Chasha, app_request):
    response = app.serve(app_request(method='get'))
    assert response.status_code == 404
    assert json.loads(response.body) == {'detail': {'msg': 'Page not found'}}


def test_failed(app: Chasha, app_request):
    @app.route('/')
    def index():
        raise KeyError()

    response = app.serve(app_request(method='get'))
    assert response.status_code == 500
    assert response.body == ''


def test_custom_error_handler(app: Chasha, app_request):
    @app.exception_handler(KeyError)
    def on_key_error(_: KeyError, http: DI.StatusCode = app.di.status_code()):
        http(200)
        return 'http 200'

    @app.route('/')
    def index():
        raise KeyError()

    response = app.serve(app_request(method='get'))
    assert response.status_code == 200
    assert response.body == 'http 200'


def test_custom_500(app: Chasha, app_request):
    @app.handle_500()
    def on_500(_: Exception, http: DI.StatusCode = app.di.status_code()):
        http(500)
        return 'http 500'

    @app.route('/')
    def index():
        raise KeyError()

    response = app.serve(app_request(method='get'))
    assert response.status_code == 500
    assert response.body == 'http 500'


def test_custom_404(app: Chasha, app_request):
    @app.handle_404()
    def on_404(_: HttpNotFound, http: DI.StatusCode = app.di.status_code()):
        http(404)
        return 'http 404'

    response = app.serve(app_request(method='get'))
    assert response.status_code == 404
    assert response.body == 'http 404'


def test_error_in_500_handler(app: Chasha, app_request):
    @app.handle_500()
    def on_500(_: Exception):
        raise Exception()

    @app.route('/')
    def index():
        raise KeyError()

    response = app.serve(app_request(method='get'))
    assert response.status_code == 500
    assert response.body == ''
