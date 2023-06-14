import os
import uuid

from chasha import Chasha, Chashka, DI, HttpNotFound
from chasha.contrib.client_session import Session
from chasha.contrib.adapters.yandex import YandexCloudAdapter

PATH = os.path.dirname(__file__)

app = Chasha()
api = Chashka(path_prefix='/api')

session = Session(secret='top secret')


@app.get('/')
def index():
    with open(os.path.join(PATH, 'todo_list.html')) as fd:
        html = fd.read()
    return app.html(html)


def ensure_todo(session_data: dict):
    if 'todo' not in session_data:
        session_data['todo'] = {}


@api.get('/todo')
def todo_list(session_data: dict = session.inject()):
    ensure_todo(session_data)
    return [
        {'id': guid} | data for guid, data in session_data['todo'].items()
    ]


@api.post('/todo')
def todo_add(session_data: dict = session.inject(), payload: dict = DI.json_body()):
    ensure_todo(session_data)
    guid = str(uuid.uuid4())

    session_data['todo'][guid] = {
        'name': payload['name']
    }
    return {'id': guid}


@api.delete('/todo/{item_id}')
def todo_delete(item_id: str, session_data: dict = session.inject()):
    ensure_todo(session_data)

    if item_id not in session_data['todo']:
        raise HttpNotFound()

    del session_data['todo'][item_id]
    return {'id': item_id}


app.include_app(api)


def handler(event, context):
    return YandexCloudAdapter(app).handler(event, context)


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    from chasha.contrib.adapters.wsgi import WSGIAdapter

    with make_server('', 8080, WSGIAdapter(app).handler) as httpd:
        httpd.serve_forever()
