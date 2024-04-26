from twisted.web import server
import secrets
from mysql_tool import MYSQL_TOOL


def get_token(request: server.Request):
    token = request.getHeader("tcwb-token")
    if token is None:
        if b"tcwb-token" in request.args:
            token = request.args.get(b"tcwb-token")[0].decode("utf-8")
    return token


def generate_token():
    token = secrets.token_hex(32)
    return token


def get_user_info_from_request(request: server.Request):
    token = get_token(request)
    if token is None:
        return None
    token_in_db = MYSQL_TOOL.execute_query_one(
        f"""
        select * from tcwb_user_token where token = '{token}' and expired_time >= now()
        """
    )
    if token_in_db is not None:
        user_in_db = MYSQL_TOOL.execute_query_one(
            f"""
            select * from tcwb_user where account = '{token_in_db['user_account']}'
            """
        )
        return user_in_db
    return None


def get_page_info_from_request(request: server.Request):
    page = 0
    size = 10
    if b"page" in request.args:
        page = int(request.args[b"page"][0])
    if b"size" in request.args:
        size = int(request.args[b"size"][0])
    offset = page * size
    return (offset, page, size)
