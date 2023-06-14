import base64
from chasha.contrib.adapters.yandex import YandexCloudAdapter


def test_index(app_test_index):
    event = {
        'httpMethod': 'get',
        'url': '/',
    }

    response = YandexCloudAdapter(app_test_index).handler(event, object())
    assert response == {
        'statusCode': 200,
        'body': 'ok',
        'headers': {
            'content-type': 'text/plain',
        },
        'multiValueHeaders': {},
        'isBase64Encoded': False,
    }


def test_http_method(app_test_index):
    event = {
        'httpMethod': 'post',
        'url': '/',
    }

    response = YandexCloudAdapter(app_test_index).handler(event, object())
    assert response['statusCode'] == 405
    assert "Method 'POST' not allowed for path '/'" in response['body']


def test_query(app_test_query):
    event = {
        'httpMethod': 'get',
        'url': '/?multi=value1&multi=value2&single=value',
        'queryStringParameters': {
            'multi': 'value2',
            'single': 'value',
        },
        'multiValueQueryStringParameters': {
            'multi': ['value1', 'value2'],
            'single': ['value'],
        }
    }

    response = YandexCloudAdapter(app_test_query).handler(event, object())
    assert response['statusCode'] == 200
    assert response['body'] == 'ok'


def test_cookies(app_test_cookies):
    event = {
        'httpMethod': 'get',
        'url': '/',
        'headers': {
            'Cookie': 'session_id=1; session_key=secret'
        },
    }

    response = YandexCloudAdapter(app_test_cookies).handler(event, object())
    assert response['statusCode'] == 200
    assert response['body'] == 'ok'
    assert set(response['multiValueHeaders']['set-cookie']) == {'processed=true; Path=/', 'key1=value1; Path=/'}


def test_body(app_test_body):
    data = 'content'

    event = {
        'httpMethod': 'get',
        'url': '/',
        'body': data,
    }

    response = YandexCloudAdapter(app_test_body).handler(event, object())
    assert response['statusCode'] == 200
    assert response['body'] == 'ok'


def test_body_b64(app_test_body):
    data = base64.b64encode(b'content')

    event = {
        'httpMethod': 'get',
        'url': '/',
        'body': data,
        'isBase64Encoded': True,
    }

    response = YandexCloudAdapter(app_test_body).handler(event, object())
    assert response['statusCode'] == 200
    assert response['body'] == 'ok'
