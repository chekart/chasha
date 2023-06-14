import uuid
import pytest
import typing

from chasha import Chasha, HttpBadRequest


def test_params_injected(app: Chasha, app_request):
    @app.route('/')
    def index(param1: str = app.di.query(), param2: str = app.di.query()):
        assert param1 == 'test1'
        assert param2 == 'test2'
        return 'ok'

    response = app.serve(app_request(method='get', query={'param1': 'test1', 'param2': 'test2'}))
    assert response.body == 'ok'


def test_name_override(app: Chasha, app_request):
    @app.route('/')
    def index(param1: str = app.di.query(name='param')):
        assert param1 == 'test2'
        return 'ok'

    response = app.serve(app_request(method='get', query={'param1': 'test1', 'param': 'test2'}))
    assert response.body == 'ok'


def test_missing_value(app: Chasha, app_request):
    @app.route('/')
    def index(param=app.di.query()):
        return str(param)

    with pytest.raises(HttpBadRequest) as e:
        app.handle_request(app_request(method='get'))

    assert "parameter 'param' is mandatory" in str(e)


def test_missing_none_value(app: Chasha, app_request):
    @app.route('/')
    def index(param1: str | None = app.di.query(),
              param2: typing.Optional[str] = app.di.query(),
              param3: typing.Union[str, None] = app.di.query()):
        assert param1 is None
        assert param2 is None
        assert param3 is None
        return 'ok'

    response = app.serve(app_request(method='get'))
    assert response.body == 'ok'


def test_default_value(app: Chasha, app_request):
    @app.route('/')
    def index(param1: str | None = app.di.query(default='value')):
        assert param1 == 'value'
        return 'ok'

    response = app.serve(app_request(method='get'))
    assert response.body == 'ok'


def test_default_type(app: Chasha, app_request):
    @app.route('/')
    def index(param1=app.di.query(default='value')):
        assert isinstance(param1, str) and param1 == 'value'
        return 'ok'

    response = app.serve(app_request(method='get'))
    assert response.body == 'ok'


def test_simple_type_cast(app: Chasha, app_request):
    guid = uuid.uuid4()

    @app.route('/')
    def index(str_param: str = app.di.query(),
              int_param: int = app.di.query(),
              bool_param: bool = app.di.query(),
              uuid_param: uuid.UUID = app.di.query()):
        assert str_param == 'value'
        assert isinstance(int_param, int) and int_param == 42
        assert isinstance(bool_param, bool) and bool_param
        assert isinstance(uuid_param, uuid.UUID) and uuid_param == guid
        return 'ok'

    response = app.serve(app_request(method='get', query={
        'str_param': 'value',
        'int_param': '42',
        'bool_param': 'true',
        'uuid_param': str(guid)
    }))
    assert response.body == 'ok'


def test_list_type_cast(app: Chasha, app_request):
    @app.route('/')
    def index(list_param: list = app.di.query(),
              int_list_param: list[int] = app.di.query()):
        assert isinstance(list_param[0], str) and list_param == ['value1', 'value2']
        assert isinstance(int_list_param[0], int) and int_list_param == [1, 2, 3]
        return 'ok'

    response = app.serve(app_request(method='get', query={
        'list_param': ['value1', 'value2'],
        'int_list_param': ['1', '2', '3'],
    }))
    assert response.body == 'ok'


def test_wrong_type_cast(app: Chasha, app_request):
    @app.route('/')
    def index(param: int = app.di.query()):
        return str(param)

    with pytest.raises(HttpBadRequest) as e:
        app.handle_request(app_request(method='get', query={
            'param': 'not an int',
        }))
    assert e.match('Failed to convert parameter param')


def test_unsupported_type_type_cast(app: Chasha, app_request):
    class MyType:
        pass

    @app.route('/')
    def index(param: MyType = app.di.query()):
        return str(param)

    with pytest.raises(HttpBadRequest) as e:
        app.handle_request(app_request(method='get', query={
            'param': 'not an MyType',
        }))
    assert e.match('Failed to convert parameter param')
