Chasha
---

Chasha (rus: Chalice) is a microframework for use in serverless applications on lambdas/cloud functions.
It does not have any dependencies only using standard library
Since changing version on serverless functions is simple, the minimal python requirement is 3.10

Supported platforms:
* __Yandex Cloud__
* __WSGI__ - for testing purposes (if you need something similar - just take FastAPI)

### Installation

```
pip install chasha
```

### Getting started

A minimal Chasha app looks like this

```python
from chasha import Chasha

app = Chasha()

@app.route('/')
def hello():
    return {'message': 'hello'}

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    from chasha.contrib.adapters.wsgi import WSGIAdapter
    
    with make_server('', 8080, WSGIAdapter(app).handler) as httpd:
        httpd.serve_forever()
```

First you need to create an app, then you can use the following decorators to create route handlers:
* `route(path: str, http_methods: list[str] = None)` 
Creates a route on the following path, when specified without `http_methods` kwargs handles any HTTp verb
* `get(path: str)` Shortcut for `route(path, http_methods=['GET'])`
* `post(path: str)` Shortcut for `route(path, http_methods=['POST'])`

The handler function returns content of the response, 
it could be of type dict for json responses, string for raw data response and special wrapper for html response
```python
@app.route('/')
def hello():
    return app.html('<html><body>Hello World</body></html>')
```

#### Sub routers

In order to organize your api routes sub routers are introduced. The sub router called `Chashka` (Small Chasha, rus: cup)

```python
app = Chasha()
api = Chashka(path_prefix='/api')

# routes

app.include_app(api)
```

#### Path parameters

Path parameters declared as python format string and passed to the handler function with the same name.
Type will be converted based on function argument type annotation

```python
@app.get('/items/{item_id}')
def get_item(item_id: int):
    return {'id': item_id}
```

### Dependency Injection

Chasha supports simple but powerful DI mechanism, lets break down the following example

```python
from chasha import Chasha, DI, InjectContext

app = Chasha()

def hello_world(context: InjectContext):
    # startup
    yield f"Hello, world from attr '{context.param_name}'"
    # teardown

@app.route('/')
def hello(greet: str = DI.inject(hello_world)):
    return {'message': greet}
```

Function `hello_world` will be injected into handler `hello` as `greet` function parameter.

There is a special non-required attribute in dependency function with the type `InjectContext` 
(name of the argument does not matter) which contains context of the current injection. 
`InjectContext` should be considered as advanced usage since there are already implemented dependencies
for basic needs.

#### Request and Response object

Sometimes it's needed to access current Request and modify Response objects, there are corresponding dependencies for this case:

```python
@app.route('/')
def hello(request: Request = DI.request(), response: Response = DI.response()):
    response.set_header('X-CHASHA-GREET', 'Hello, world')
    return {'message': request.get_header('user-agent')}
```

#### Query Params

It's possible to access query parameters via `Request` object, but it's preferred to use special injection

```python
@app.route('/add')
def hello(a: int = DI.query(), b: int = DI.query()):
    return {'message': a + b}
```

Dependency `query(name: str, default = None)` can override name and provide default, 
in case the parameter is missing and no default provided response will fail with 405 code

#### Request payload

It's possible to access query parameters via `Request` object, but it's preferred to use special injection

```python
@app.route('/add')
def hello(data: int = DI.json_body()):
    return {'message': data}
```

#### Cookies

To read and set cookies use special injection `DI.cookies`

```python
@app.route('/')
def index(cookies: DI.Cookies = DI.cookies()):
    cookies.set('greeted', 'true')
    return {'message': cookies.get('greet')}
```

#### Exception handling

To handle uncaught exception use decorator `Chasha.exception_handler` and it's shortcuts 
`handle_500` and `handle_404`
Handler takes one positional argument - raised exception, also handler fully supports dependencies.

```python
@app.handle_500()
def on_500(_: Exception):
    return {'message': 'ooops'}

@app.route('/')
def hello():
    raise Exception()
```

#### Serve requests

After you create your app - you need to serve HTTP requests somehow, for this you need to use adapters.
Add the following lines of code to your API Gateway Cloud Function handler to start using Chasha over Yandex Cloud

```python
def handler(event, context):
    from chasha.contrib.adapters.yandex import YandexCloudAdapter
    return YandexCloudAdapter(app).handler(event, context)
```

#### WSGI Adapter

Chasha also ships with WSGI adapter to ease local development, it can be used with any wsgi app server of choice, 
or even with builtin server

```python
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    from chasha.contrib.adapters.wsgi import WSGIAdapter

    with make_server('', 8080, WSGIAdapter(app).handler) as httpd:
        httpd.serve_forever()
```