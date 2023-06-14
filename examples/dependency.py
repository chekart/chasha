from chasha import Chasha, DI, InjectContext

app = Chasha()


def hello_world(context: InjectContext):
    yield f"Hello, world from attr '{context.param_name}'"


@app.route('/')
def hello(greet: str = DI.inject(hello_world)):
    return {'message': greet}


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    from chasha.contrib.adapters.wsgi import WSGIAdapter

    with make_server('', 8080, WSGIAdapter(app).handler) as httpd:
        httpd.serve_forever()
