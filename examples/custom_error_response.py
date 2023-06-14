from chasha import Chasha

app = Chasha()


@app.handle_500()
def on_500(_: Exception):
    return {'message': 'ooops'}


@app.route('/')
def hello():
    raise Exception()


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    from chasha.contrib.adapters.wsgi import WSGIAdapter

    with make_server('', 8080, WSGIAdapter(app).handler) as httpd:
        httpd.serve_forever()
