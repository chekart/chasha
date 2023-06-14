from chasha import Chasha
from chasha.contrib.client_session import Session, sign_dict


def test_session_get(app: Chasha, app_request):
    secret = 'secret'
    session_data = {
        'user_id': 1
    }
    session = Session(secret=secret, cookie='session')

    @app.route('/')
    def index(data: dict = session.inject()):
        assert data == session_data
        return 'ok'

    response = app.serve(app_request(method='get', headers={
        'Cookie': f'session="{sign_dict(session_data, secret=secret)}" Path=/'
    }))
    assert response.body == 'ok'


def test_session_modify(app: Chasha, app_request):
    secret = 'secret'
    session = Session(secret=secret, cookie='session')

    @app.route('/')
    def index(data: dict = session.inject()):
        assert data == {}
        data['user_id'] = 1
        return 'ok'

    response = app.serve(app_request(method='get'))
    cookie, = response.get_header('set-cookie')
    assert f'session="{sign_dict({"user_id": 1}, secret=secret)}"; Path=/' in cookie
    assert response.body == 'ok'


def test_session_no_create(app: Chasha, app_request):
    session = Session(secret='secret', cookie='session')

    @app.route('/')
    def index(data: dict = session.inject()):
        assert data == {}
        return 'ok'

    response = app.serve(app_request(method='get'))
    assert response.get_header('set-cookie') == []
    assert response.body == 'ok'


def test_session_no_modify(app: Chasha, app_request):
    secret = 'secret'
    session_data = {
        'user_id': 1
    }
    session = Session(secret=secret, cookie='session')

    @app.route('/')
    def index(data: dict = session.inject()):
        assert data['user_id'] == 1
        return 'ok'

    response = app.serve(app_request(method='get', headers={
        'Cookie': f'session="{sign_dict(session_data, secret=secret)}" Path=/'
    }))
    assert response.get_header('set-cookie') == []
    assert response.body == 'ok'
