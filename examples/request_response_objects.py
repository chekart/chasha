from chasha import Chasha, Request, Response, DI

app = Chasha()


@app.route('/')
def hello(request: Request = DI.request(), response: Response = DI.response()):
    response.set_header('X-CHASHA-GREET', 'Hello, world')
    return {'message': request.get_header('user-agent')}


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    from chasha.contrib.adapters.wsgi import WSGIAdapter

    with make_server('', 8080, WSGIAdapter(app).handler) as httpd:
        httpd.serve_forever()
