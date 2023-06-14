import inspect
import json
import logging
import types
import typing
import re
import uuid
from dataclasses import dataclass
from collections import defaultdict
from http.cookies import SimpleCookie


LOG = logging.getLogger('chasha')


class HttpError(Exception):
    MESSAGE = 'Http Error'
    STATUS_CODE = 500

    def __init__(self, message: str | None = None, status_code: int | None = None):
        message = message or self.MESSAGE
        super().__init__(message)
        self.message = message
        self.status_code = status_code or self.STATUS_CODE

    def details(self) -> dict[str, typing.Any]:
        return {
            'msg': self.message
        }


class HttpNotFound(HttpError):
    MESSAGE = 'Page not found'
    STATUS_CODE = 404


class HttpMethodNotAllowed(HttpError):
    MESSAGE = 'Method Not Allowed'
    STATUS_CODE = 405


class HttpBadRequest(HttpError):
    MESSAGE = 'Bad Request'
    STATUS_CODE = 400


class QueryParamMissing(HttpBadRequest):
    def __init__(self, message: str, fields: typing.Iterable[str] = ()):
        super().__init__(message)
        self.fields = fields

    def details(self) -> dict[str, typing.Any]:
        return {
            'msg': 'Required fields missing from request',
            'fields': self.fields,
        }


class PayloadError(HttpBadRequest):
    def details(self) -> dict[str, typing.Any]:
        return {
            'msg': 'Failed to load payload'
        }


class HttpRedirect(HttpError):
    MESSAGE = 'Redirect'
    STATUS_CODE = 307

    def __init__(self, redirect_to: str, message: str = '', status_code: int | None = None):
        super().__init__(message, status_code)
        self.to = redirect_to


EMPTY = object()


class _HtmlBody(str):
    pass


class Request:
    def __init__(self, method: str,
                 query: dict[str, list[str]],
                 headers: dict[str, str],
                 path: str = '/',
                 body: str = '',
                 raw: typing.Any = None):
        self.method = method
        self.query = query
        self.path = path
        self.body = body
        self.raw = raw
        self._headers: dict[str, str] = {
            key.lower(): value for key, value in headers.items()
        }
        self._cookies: SimpleCookie = SimpleCookie()
        cookies = self._headers.get('cookie')
        if cookies:
            self._cookies.load(cookies)

    def get_header(self, name: str, default: str | None = None) -> str | None:
        return self._headers.get(name.lower(), default)

    @property
    def headers(self) -> typing.Iterable[tuple[str, str]]:
        yield from self._headers.items()

    def get_cookie(self, name: str) -> str | None:
        if name not in self._cookies:
            return None
        return self._cookies[name].value


class Response:
    def __init__(self, status_code: int = 200):
        self.status_code: int = status_code
        self._headers: dict[str, list[str]] = defaultdict(list)
        self._cookies: SimpleCookie = SimpleCookie()
        self.body: str = ''
        self.raw: str | None = None

    def set_header(self, key: str, value: str | list[str]):
        if not isinstance(value, list):
            value = [value]
        self._headers[key.lower()] = value

    def add_header(self, key: str, value: str):
        if not isinstance(value, str):
            raise ValueError('Header value should be single string')
        self._headers[key.lower()].append(value)

    def get_header(self, key: str) -> list[str]:
        return self._headers.get(key.lower(), [])

    def get_single_header(self, key: str, default: str | None = None) -> str | None:
        values = self._headers.get(key.lower())
        if not values:
            return default
        return values[0]

    def set_cookie(self, name: str, value: str,
                   path: str | None = None,
                   max_age: int | None = None,
                   http_only: bool | None = None):
        self._cookies[name] = value
        if path is not None:
            self._cookies[name]['path'] = path
        if max_age is not None:
            self._cookies[name]['max-age'] = max_age
        if http_only is not None:
            self._cookies[name]['httponly'] = http_only

    def apply_cookies(self):
        for item in self._cookies.values():
            self.add_header('Set-Cookie', item.OutputString())

    @property
    def headers(self) -> typing.Iterable[tuple[str, list[str]]]:
        yield from self._headers.items()

    def finalize(self):
        self.apply_raw()
        self.apply_cookies()

    def apply_raw(self):
        if self.raw is None:
            # custom response
            return

        if isinstance(self.raw, _HtmlBody):
            self.body = str(self.raw)
            self.set_header('content-type', 'text/html')
        elif isinstance(self.raw, str):
            self.body = self.raw
            self.set_header('content-type', 'text/plain')
        elif isinstance(self.raw, dict) or isinstance(self.raw, list):
            self.body = json.dumps(self.raw)
            self.set_header('content-type', 'application/json')
        else:
            raise ValueError(f"Unsupported return type {type(self.raw)}")


@dataclass
class InjectContext:
    param_name: str | None  # name of the function parameter
    param_type: type | None  # type of the function parameter if specified
    request: Request  # current request object
    response: Response  # current response object


class _Dependency:
    def __init__(self, generator: typing.Callable):
        if not inspect.isgeneratorfunction(generator):
            raise ValueError(f"Only generator functions can be injected. "
                             f"Function {generator.__name__} can not")
        self.generator = generator


class DI:
    class StatusCode:
        def __init__(self, response: Response):
            self._response = response

        def __call__(self, status_code: int):
            self._response.status_code = status_code

    class Cookies:
        def __init__(self, request: Request, response: Response):
            self._request = request
            self._response = response

        def get(self, name: str) -> str | None:
            return self._request.get_cookie(name)

        def set(self, name: str, value: str,
                path: str = '/',
                max_age: int | None = None,
                http_only: bool | None = None):
            self._response.set_cookie(
                name, value, path=path, max_age=max_age, http_only=http_only
            )

    @staticmethod
    def inject(dependency: typing.Callable):
        return _Dependency(dependency)

    @classmethod
    def status_code(cls, default_status_code: int | None = None):
        def dependency(r: Response = cls.response()):
            if default_status_code is not None:
                r.status_code = default_status_code
            yield DI.StatusCode(r)
        return cls.inject(dependency)

    @classmethod
    def cookies(cls):
        def dependency(request: Request = cls.request(), response: Response = cls.response()):
            yield cls.Cookies(request=request, response=response)
        return cls.inject(dependency)

    @classmethod
    def request(cls):
        return cls.inject(cls._request)

    @staticmethod
    def _request(context: InjectContext):
        yield context.request

    @classmethod
    def response(cls):
        return cls.inject(cls._response)

    @staticmethod
    def _response(context: InjectContext):
        yield context.response

    @classmethod
    def query(cls, name: str | None = None, default: typing.Any = EMPTY):
        def _from_query(context: InjectContext):
            param_name = name or context.param_name
            assert param_name
            try:
                value = context.request.query[param_name]
            except KeyError:
                if default is not EMPTY:
                    yield default
                    return
                if context.param_type and TypeCast.is_optional(context.param_type):
                    yield None
                    return
                raise QueryParamMissing(f"Query parameter '{param_name}' is mandatory", fields=[param_name])
            try:
                yield TypeCast.coerce_param(context.param_type, value)
            except ValueError:
                raise HttpBadRequest(f"Failed to convert parameter {param_name}")
        return cls.inject(_from_query)

    @classmethod
    def body(cls, loader=lambda data, type_: data):
        def dependency(context: InjectContext, request: Request = DI.request()):
            try:
                yield loader(request.body, context.param_type)
            except Exception:
                raise PayloadError()
        return cls.inject(dependency)

    @classmethod
    def json_body(cls):
        return cls.body(loader=lambda data, _: json.loads(data))


class Chashka:
    di = DI

    def __init__(self, path_prefix: str = ''):
        self._router = Router(prefix=path_prefix)

    def _route(self, methods: typing.Iterable[str], path: str):
        def decorator(func):
            self._router.add_route(methods, path, func)
        return decorator

    def route(self, path: str, http_methods: typing.Iterable[str] = ()):
        http_methods = http_methods or [Router.HTTP_ANY]
        return self._route(http_methods, path)

    def get(self, path: str):
        return self._route(['GET'], path)

    def post(self, path: str):
        return self._route(['POST'], path)

    def put(self, path: str):
        return self._route(['PUT'], path)

    def delete(self, path: str):
        return self._route(['DELETE'], path)

    def include_app(self, app: 'Chashka', prefix: str = ''):
        self._router.include(app._router, prefix=prefix)

    @classmethod
    def html(cls, response: str) -> _HtmlBody:
        return _HtmlBody(response)


class Chasha(Chashka):
    def __init__(self, path_prefix: str = ''):
        super().__init__(path_prefix=path_prefix)
        self._error_handlers: dict[type, typing.Callable] = {}
        self._add_error_handler(HttpRedirect, self._redirect_handler)
        self._add_error_handler(HttpError, self._http_error_handler)
        self._add_error_handler(Exception, self._exception_handler)

    @staticmethod
    def _redirect_handler(exception: HttpRedirect, response: Response = DI.response()):
        response.status_code = exception.status_code
        response.set_header('content-type', 'text/plain')
        response.set_header('location', exception.to)

    @staticmethod
    def _http_error_handler(exception: HttpError, response: Response = DI.response()):
        response.status_code = exception.status_code
        return {
            'detail': exception.details()
        }

    @staticmethod
    def _exception_handler(_: Exception, response: Response = DI.response()):
        response.status_code = 500

    def _add_error_handler(self, exception: type, func: typing.Callable):
        self._error_handlers[exception] = func

    def _handle_error(self, exception: Exception, request: Request):
        response = Response(status_code=500)

        exception_order = sorted(self._error_handlers,
                                 key=lambda type_: len(type_.__mro__),
                                 reverse=True)

        for exception_type in exception_order:
            if isinstance(exception, exception_type):
                try:
                    handler = self._error_handlers[exception_type]
                    response.raw = self.invoke(request, response, handler, exception)
                    response.finalize()
                    return response
                except Exception as e:
                    LOG.error(f'Failed to process error handler: {e}')
                    pass

        return Response(status_code=500)

    def exception_handler(self, exception: type):
        def decorator(func: typing.Callable):
            self._add_error_handler(exception, func)
        return decorator

    def handle_404(self):
        return self.exception_handler(HttpNotFound)

    def handle_400(self):
        return self.exception_handler(HttpBadRequest)

    def handle_500(self):
        return self.exception_handler(Exception)

    def invoke(self, __request: Request, __response: Response, __func: typing.Callable, *args, **kwargs):
        context = InjectContext(
            param_name=None,
            param_type=None,
            request=__request,
            response=__response,
        )
        return self.__invoke(context, __func, *args, **kwargs)

    def __invoke(self, __context: InjectContext, __func: typing.Callable, *args, **kwargs):
        spec = inspect.signature(__func)
        di = []
        for attr, attr_spec in spec.parameters.items():
            if attr_spec.annotation is InjectContext:
                kwargs[attr] = __context

            if isinstance(attr_spec.default, _Dependency):
                context = InjectContext(
                    param_name=attr,
                    param_type=attr_spec.annotation if attr_spec.annotation != attr_spec.empty else None,
                    request=__context.request,
                    response=__context.response
                )
                gen = self.__invoke(context, attr_spec.default.generator)
                kwargs[attr] = next(gen)
                di.append(gen)
                continue

        result = __func(*args, **kwargs)

        for gen in di:
            try:
                next(gen)
            except StopIteration:
                pass
            gen.close()

        return result

    def handle_request(self, request: Request) -> Response:
        response = Response(status_code=200)
        handler, kwargs = self._router.handle_route(request.method, request.path)
        response.raw = self.invoke(request, response, handler, **kwargs)
        return response

    def serve(self, request: Request) -> Response:
        try:
            response = self.handle_request(request)
            response.finalize()
        except Exception as e:
            if not isinstance(e, HttpError):
                LOG.exception(f'Failed to process handler {e}')
            response = self._handle_error(e, request)
        return response


def _list_coercion(type_: type, value: list):
    assert isinstance(value, list)
    item_type = typing.get_args(type_)
    item_type = item_type[0] if item_type else str
    return [TypeCast.coerce_param(item_type, item) for item in value]


class TypeCast:
    COERCION = {
        int: lambda _, value: int(value),
        str: lambda _, value: str(value),
        uuid.UUID: lambda _, value: uuid.UUID(value),
        bool: lambda _, value: value.lower() == 'true',
        list: _list_coercion,
    }

    @classmethod
    def coerce_param(cls, type_, value):
        origin_type = cls.get_real_type(type_) or type_
        if origin_type not in cls.COERCION:
            raise ValueError(f"Unknown parameter type {type_}")
        coercion = cls.COERCION[origin_type]
        try:
            return coercion(type_, value)
        except Exception:
            raise ValueError(f"Failed to convert parameter to type {type_}")

    @classmethod
    def get_real_type(cls, type_: type):
        origin = typing.get_origin(type_)
        if origin is typing.Annotated:
            return typing.get_args(type_)[0]
        if cls.is_optional(type_):
            return cls.optional_type(type_)
        return origin or type_

    @classmethod
    def is_optional(cls, type_: type) -> bool:
        origin = typing.get_origin(type_)
        if origin is None:
            return False
        # type hints are amazing
        if origin is typing.Union or issubclass(origin, types.UnionType):
            type_list = typing.get_args(type_)
            if len(type_list) == 2 and types.NoneType in type_list:
                return True
        return False

    @classmethod
    def optional_type(cls, type_) -> type:
        for optional_type in typing.get_args(type_):
            if not issubclass(optional_type, types.NoneType):
                return optional_type
        return types.NoneType


@dataclass
class HttpMethodHandler:
    def __init__(self, regexp: str, handler: typing.Callable, path: str, method: str, attrs: dict[str, type]):
        self.regexp = regexp
        self.handler = handler
        self.path = path
        self.method = method
        self.attrs = attrs
        self._re = re.compile('^' + regexp + '$')

    def add_prefix(self, prefix: str) -> 'HttpMethodHandler':
        return HttpMethodHandler(
            regexp=prefix + self.regexp,
            handler=self.handler,
            path=self.path,
            method=self.method,
            attrs=self.attrs
        )

    def extract_attrs(self, path: str) -> dict:
        m = self._re.match(path)
        assert m

        kv = {}
        for attr, type_ in self.attrs.items():
            kv[attr] = TypeCast.coerce_param(type_, m.group(attr))
        return kv


class HttpRouteHandler:
    def __init__(self, regexp: str):
        self.regexp = regexp
        self._re = re.compile('^' + regexp + '$')
        self.method_handlers: dict[str, HttpMethodHandler] = {}

    def is_match(self, path: str) -> bool:
        return bool(self._re.match(path))

    def get_handler(self, method: str, path: str) -> tuple[typing.Callable, dict[str, typing.Any]]:
        method = method.upper()

        if Router.HTTP_ANY in self.method_handlers:
            method = Router.HTTP_ANY
        elif method not in self.method_handlers:
            raise HttpMethodNotAllowed(f"Method '{method}' not allowed for path '{path}'")

        handler = self.method_handlers[method]
        kwargs = handler.extract_attrs(path)
        return handler.handler, kwargs


class Router:
    HTTP_ANY = '__ANY__'
    ROUTE_ATTR_REGEX = {
        int: "[0-9]+",
        str: "[^/]+",
        bool: "(true|false)",
        uuid.UUID: "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    }

    def __init__(self, prefix: str = ''):
        self._validate_prefix(prefix)
        self._prefix: str = prefix
        self._routes: dict[str, HttpRouteHandler] = {}

    @classmethod
    def _validate_prefix(cls, prefix: str):
        if prefix and not prefix.startswith('/'):
            raise ValueError('prefix should start with /')
        if prefix == '/':
            raise ValueError('prefix can not be /')

    def include(self, router: 'Router', prefix: str = ''):
        self._validate_prefix(prefix)
        prefix = self._prefix + prefix
        for regexp, route_handler in router._routes.items():
            new_regexp = prefix + regexp
            for method_handler in route_handler.method_handlers.values():
                self._add_handler(new_regexp, method_handler.add_prefix(prefix))

    def _add_handler(self, regexp: str, spec: HttpMethodHandler):
        if regexp not in self._routes:
            self._routes[regexp] = HttpRouteHandler(regexp)

        handler = self._routes[regexp]
        if Router.HTTP_ANY in handler.method_handlers:
            raise ValueError(f"Route for any method on path '{spec.path}' already exists")
        if spec.method in handler.method_handlers:
            raise ValueError(f"Route for method '{spec.method}' on path '{spec.path}' already exists")
        if spec.method == Router.HTTP_ANY and handler.method_handlers:
            raise ValueError(f"Routes for methods ({', ' .join(handler.method_handlers.keys())}) "
                             f"on path '{spec.path}' already exist")
        handler.method_handlers[spec.method] = spec

    def add_route(self, methods: typing.Iterable[str], path: str, handler: typing.Callable):
        if not path.startswith('/'):
            raise ValueError('Path should start with /')

        parts = path.split('/')
        attrs = {}
        handler_regexp_parts = []
        regexp_parts = []
        spec = inspect.signature(handler)

        for part in parts:
            if not (part.startswith('{') and part.endswith('}')):
                handler_regexp_parts.append(re.escape(part))
                regexp_parts.append(re.escape(part))
                continue

            part = part[1:-1]
            if part in attrs:
                raise ValueError(f"Duplicate attribute {part}")

            if part not in spec.parameters:
                raise ValueError(f"Route parameter {part} missing from the function signature")
            attr_spec = spec.parameters[part]

            attrs[part] = attr_spec.annotation if attr_spec.annotation is not spec.empty else str
            try:
                part_regex = self.ROUTE_ATTR_REGEX[attrs[part]]
            except KeyError:
                raise ValueError(f'Unsupported parameter type {attrs[part]}')
            handler_regexp_parts.append(f"(?P<{part}>{part_regex})")
            regexp_parts.append(f"({part_regex})")

        handler_regexp = '/'.join(handler_regexp_parts)
        regexp = '/'.join(regexp_parts)
        if self._prefix:
            handler_regexp = self._prefix + handler_regexp
            regexp = self._prefix + regexp

        for method in methods:
            self._add_handler(regexp, HttpMethodHandler(
                regexp=handler_regexp,
                handler=handler,
                method=method.upper(),
                attrs=attrs,
                path=path
            ))

    @classmethod
    def _compile_regexp(cls, regexp: str, spec: dict[str, typing.Any]):
        spec['re'] = re.compile('^' + regexp + '$')

    def handle_route(self, method: str, path: str) -> tuple[typing.Callable, dict[str, typing.Any]]:
        method = method.upper()
        for route_handler in self._routes.values():
            if not route_handler.is_match(path):
                continue
            return route_handler.get_handler(method, path)
        raise HttpNotFound()
