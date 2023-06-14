from chasha import Chasha

app = Chasha()


HTML = """
<html lang="en">
<head>
    <title>Greet</title>
</head>
<body>
    <h1>Hello World</h1>
</body>
</html>
"""


@app.route('/')
def hello():
    return app.html(HTML)


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    from chasha.contrib.adapters.wsgi import WSGIAdapter

    with make_server('', 8080, WSGIAdapter(app).handler) as httpd:
        httpd.serve_forever()
