import uuid
import pytest

from chasha import Chasha, HttpNotFound, Chashka


def test_route(app: Chasha, app_request):
    @app.route('/')
    def index():
        return 'index'

    @app.route('/about')
    def about():
        return 'about'

    response = app.serve(app_request(method='get', path='/'))
    assert response.body == 'index'

    response = app.serve(app_request(method='get', path='/about'))
    assert response.body == 'about'


def test_prefix(app_request):
    app = Chasha(path_prefix='/api')

    @app.route('/test')
    def index():
        return 'index'

    response = app.serve(app_request(method='get', path='/api/test'))
    assert response.body == 'index'

    response = app.serve(app_request(method='get', path='/test'))
    assert response.status_code == 404


def test_params(app: Chasha, app_request):
    test_guid = uuid.uuid4()

    @app.route('/{lang}/{group_id}/{guid}')
    def index(lang, group_id: int, guid: uuid.UUID):
        assert isinstance(lang, str) and lang == 'ru'
        assert isinstance(group_id, int) and group_id == 42
        assert isinstance(guid, uuid.UUID) and guid == test_guid
        return 'ok'

    response = app.serve(app_request(method='get', path=f'/ru/42/{str(test_guid)}'))
    assert response.body == 'ok'


def test_duplicate_param(app: Chasha, app_request):
    with pytest.raises(ValueError) as e:
        @app.route('/{param}/{param}')
        def index(param):
            return 'ok'
    assert e.match('Duplicate attribute param')


def test_param_missing(app: Chasha, app_request):
    with pytest.raises(ValueError) as e:
        @app.route('/{param}')
        def index():
            return 'ok'
    assert e.match('Route parameter param missing from the function signature')


def test_param_not_supported_type(app: Chasha):
    class NotSupported:
        pass

    with pytest.raises(ValueError) as e:
        @app.route('/{param}')
        def index(param: NotSupported):
            return 'ok'
    assert e.match('Unsupported parameter type')


def test_cast_fail(app: Chasha, app_request):
    @app.route('/{param}')
    def index(param: int):
        return 'ok'

    with pytest.raises(HttpNotFound):
        app.handle_request(app_request(method='get', path='/test'))


def test_order(app: Chasha, app_request):
    @app.route('/index')
    def index():
        return 'index'

    @app.route('/{path}')
    def handler(path: str):
        return 'path'

    @app.route('/about')
    def about():
        return 'about'

    response = app.serve(app_request(method='get', path='/about'))
    assert response.body == 'path'

    response = app.serve(app_request(method='get', path='/index'))
    assert response.body == 'index'


def test_404(app: Chasha, app_request):
    @app.route('/')
    def index():
        return 'ok'

    with pytest.raises(HttpNotFound):
        app.handle_request(app_request(method='get', path='/unknown'))


def test_method(app: Chasha, app_request):
    @app.get('/')
    def index_get():
        return 'get'

    @app.post('/')
    def index_post():
        return 'post'

    response = app.serve(app_request(method='get'))
    assert response.body == 'get'

    response = app.serve(app_request(method='post'))
    assert response.body == 'post'


def test_sub_app(app: Chasha, app_request):
    subsub = Chashka(path_prefix='/subsub')
    sub = Chashka(path_prefix='/sub')

    @subsub.route('/test')
    def index_subsub():
        return 'index subsub'

    @sub.route('/test')
    def index_sub():
        return 'index sub'

    @app.route('/test')
    def index_root():
        return 'index main'

    sub.include_app(subsub, prefix='/include')
    app.include_app(sub)

    response = app.serve(app_request(method='get', path='/test'))
    assert response.body == 'index main'

    response = app.serve(app_request(method='get', path='/sub/test'))
    assert response.body == 'index sub'

    response = app.serve(app_request(method='get', path='/sub/include/subsub/test'))
    assert response.body == 'index subsub'


def test_duplicate_route(app: Chasha, app_request):
    @app.get('/')
    def index_1():
        return 'get'

    with pytest.raises(ValueError) as err:
        @app.get('/')
        def index_2():
            return 'get'

    err.match("Route for method 'GET' on path '/' already exists")


def test_duplicate_route_any_post(app: Chasha, app_request):
    @app.route('/')
    def index_any():
        return 'any'

    with pytest.raises(ValueError) as err:
        @app.post('/')
        def index_post():
            return 'post'
    err.match("Route for any method on path '/' already exists")


def test_duplicate_route_get_any(app: Chasha, app_request):
    @app.get('/')
    def index_get():
        return 'get'

    @app.post('/')
    def index_post():
        return 'post'

    with pytest.raises(ValueError) as err:
        @app.route('/')
        def index():
            return 'any'
    err.match(r"Routes for methods \(GET, POST\) on path '/' already exist")
