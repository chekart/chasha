import typing
import urllib.parse
import email.message
from http import HTTPStatus
from urllib.parse import urlparse
from chasha import Chasha, Request


class WSGIAdapter:
    MAX_LENGTH = 100 * 1000 * 1000
    HEADER_PREFIX = 'HTTP_'

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
    def _get_query(cls, qs: str) -> dict[str, list]:
        if not qs:
            return {}
        result = urllib.parse.parse_qs(qs)
        return cls._denormalize_multi_value(result)

    @classmethod
    def _get_headers(cls, environ: dict[str, str]):
        headers = {}
        for key, value in environ.items():
            if not key.startswith(cls.HEADER_PREFIX):
                continue
            name = key[len(cls.HEADER_PREFIX):].lower().replace('_', '-')
            headers[name] = value

        return headers

    @classmethod
    def _parse_content_charset(cls, environ: dict[str, str]):
        message = email.message.Message()  # whatever
        message['content-type'] = environ.get('CONTENT_TYPE', 'text/plain')
        params = dict(message.get_params() or ())
        return params.get('charset', 'utf-8')

    @classmethod
    def _get_body(cls, environ: dict[str, typing.Any]):
        if 'wsgi.input' not in environ:
            return ''
        content_length = environ.get('CONTENT_LENGTH') or 0
        if not content_length:
            return ''

        content_charset = cls._parse_content_charset(environ)
        length = int(content_length)
        data = environ['wsgi.input'].read(length)
        return data.decode(content_charset)

    @classmethod
    def adapt_request(cls, environ):
        request = Request(
            method=environ['REQUEST_METHOD'].upper(),
            query=cls._get_query(environ.get('QUERY_STRING')),
            headers=cls._get_headers(environ),
            path=cls._get_path(environ.get('PATH_INFO', '/')),
            body=cls._get_body(environ),
            raw=environ
        )
        return request

    @classmethod
    def get_status(cls, status_code) -> str:
        status = HTTPStatus(status_code)
        return f'{status.value} {status.phrase}'

    def handler(self, environ, start_response) -> typing.Iterable[bytes]:
        request = self.adapt_request(environ)
        response = self.app.serve(request)

        headers = []
        for key, values in response.headers:
            for value in values:
                headers.append((key, value))

        start_response(self.get_status(response.status_code), headers)
        return [response.body.encode('latin-1')]
