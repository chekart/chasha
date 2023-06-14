from chasha import Chasha, DI

app = Chasha()


@app.route('/add')
def hello(a: int = DI.query(), b: int = DI.query()):
    return {'message': a + b}


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    from chasha.contrib.adapters.wsgi import WSGIAdapter

    with make_server('', 8080, WSGIAdapter(app).handler) as httpd:
        httpd.serve_forever()
