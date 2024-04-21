from twisted.web import server
import secrets


def get_token(request: server.Request):
    token = request.getHeader("tcwb-token")
    if token is None:
        token = request.args.get(b"tcwb-token", [None])[0].decode("utf-8")
    return token


def generate_token():
    token = secrets.token_hex(32)
    return token
