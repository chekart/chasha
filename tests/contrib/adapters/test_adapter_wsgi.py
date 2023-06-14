from io import BytesIO

from chasha.contrib.adapters.wsgi import WSGIAdapter


def success_start_response(status, headers):
    assert status == '200 OK'
    assert ('content-type', 'text/plain') in headers


def test_index(app_test_index):
    environ = {
        'REQUEST_METHOD': 'get',
        'PATH_INFO': '/',
    }

    body, = WSGIAdapter(app_test_index).handler(environ, success_start_response)
    assert body == b'ok'


def test_http_method(app_test_index):
    environ = {
        'REQUEST_METHOD': 'post',
        'PATH_INFO': '/',
    }

    def start_response(status_code, _):
        assert status_code == '405 Method Not Allowed'

    body, = WSGIAdapter(app_test_index).handler(environ, start_response)
    assert b"Method 'POST' not allowed for path '/'" in body


def test_query(app_test_query):
    environ = {
        'REQUEST_METHOD': 'get',
        'PATH_INFO': '/',
        'QUERY_STRING': 'multi=value1&multi=value2&single=value',
    }

    body, = WSGIAdapter(app_test_query).handler(environ, success_start_response)
    assert body == b'ok'


def test_cookies(app_test_cookies):
    environ = {
        'REQUEST_METHOD': 'get',
        'PATH_INFO': '/',
        'HTTP_COOKIE': 'session_id=1; session_key=secret',
    }

    def start_response(status_code, headers):
        assert status_code == '200 OK'
        assert ('set-cookie', 'processed=true; Path=/') in headers
        assert ('set-cookie', 'key1=value1; Path=/') in headers

    body, = WSGIAdapter(app_test_cookies).handler(environ, start_response)
    assert body == b'ok'


def test_body(app_test_body):
    data = b'content'

    environ = {
        'REQUEST_METHOD': 'get',
        'PATH_INFO': '/',
        'CONTENT_LENGTH': str(len(data)),
        'wsgi.input': BytesIO(data)
    }

    body, = WSGIAdapter(app_test_body).handler(environ, success_start_response)
    assert body == b'ok'


def test_body_no_content_length(app_test_no_body):
    environ = {
        'REQUEST_METHOD': 'get',
        'PATH_INFO': '/',
        'wsgi.input': BytesIO(b'content')
    }

    body, = WSGIAdapter(app_test_no_body).handler(environ, success_start_response)
    assert body == b'ok'


def test_body_empty_content_length(app_test_no_body):
    environ = {
        'REQUEST_METHOD': 'get',
        'PATH_INFO': '/',
        'CONTENT_LENGTH': '',
        'wsgi.input': BytesIO(b'content')
    }

    body, = WSGIAdapter(app_test_no_body).handler(environ, success_start_response)
    assert body == b'ok'
