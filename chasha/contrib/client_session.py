import base64
import hmac
import hashlib
import json
import secrets

from chasha import DI


class BadSignature(Exception):
    pass


def _signature(value: str, *, secret: str) -> str:
    hasher = hashlib.sha256
    secret_bytes = secret.encode('ascii')
    value_bytes = value.encode('utf-8')

    key = hasher(secret_bytes).digest()
    signature: bytes = hmac.new(key, msg=value_bytes, digestmod=hasher).digest()

    b64_signature: str = base64.b64encode(signature).decode('ascii')
    return b64_signature


def sign_str(value: str, *, secret: str) -> str:
    value_bytes = value.encode('utf-8')
    b64_value: str = base64.b64encode(value_bytes).decode('ascii')
    b64_signature: str = _signature(value, secret=secret)

    return f'{b64_value}:{b64_signature}'


def sign_dict(value: dict, *, secret: str) -> str:
    return sign_str(json.dumps(value), secret=secret)


def verify_str(signed: str, *, secret: str) -> str:
    b64_value, b64_signature = signed.split(':')

    value_bytes: bytes = base64.b64decode(b64_value)
    value = value_bytes.decode('utf-8')

    if not secrets.compare_digest(b64_signature, _signature(value, secret=secret)):
        raise BadSignature()

    return value


def verify_dict(signed: str, *, secret: str) -> dict:
    value: str = verify_str(signed, secret=secret)
    return json.loads(value)


class Session:
    def __init__(self, secret: str, cookie: str = 'chasha_contrib_session'):
        self.__secret = secret
        self.__cookie_name = cookie

    def _session(self, cookies: DI.Cookies = DI.cookies()):
        signed_session = cookies.get(self.__cookie_name)
        data = {}
        try:
            if signed_session:
                data = verify_dict(signed_session, secret=self.__secret)
        except Exception:
            data = {}

        yield data
        new_signed_session = sign_dict(data, secret=self.__secret)

        if not data and signed_session is None:
            return
        if new_signed_session == signed_session:
            return

        cookies.set(self.__cookie_name, new_signed_session)

    def inject(self):
        return DI.inject(self._session)
