import base64
from urllib.parse import urlparse
from chasha import Chasha, Request


class YandexCloudAdapter:
    """
    Adapter for Yandex Cloud Functions
    Binary response is not supported
    """
    def __init__(self, app: Chasha):
        self.app = app

    @staticmethod
    def _denormalize_multi_value(dikt: dict[str, list]):
        return {
            key: value[0] if len(value) == 1 else value
            for key, value in dikt.items()
        }

    @staticmethod
    def _get_path(url: str):
        result = urlparse(url)
        return result.path

    @classmethod
    def adapt_request(cls, event):
        body = event.get('body', '')
        if body and event.get('isBase64Encoded'):
            body = base64.b64decode(body).decode('utf-8')

        request = Request(
            method=event['httpMethod'],
            query=cls._denormalize_multi_value(event.get('multiValueQueryStringParameters', {})),
            headers=event.get('headers', {}),
            path=cls._get_path(event['url']),
            body=body,
            raw=event
        )
        return request

    @classmethod
    def adapt_response(cls, response):
        headers = {}
        m_headers = {}

        for key, values in response.headers:
            if len(values) > 1:
                m_headers[key] = values
            else:
                headers[key] = values[0]

        result = {
            'statusCode': response.status_code,
            'body': response.body,
            'headers': headers,
            'multiValueHeaders': m_headers,
            'isBase64Encoded': False,
        }

        return result

    def handler(self, event, _):
        request = self.adapt_request(event)
        response = self.app.serve(request)
        return self.adapt_response(response)
