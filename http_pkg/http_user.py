from twisted.web import resource, server
import json

import http_tool
from mysql_tool import MYSQL_TOOL


class HttpAuthResource(resource.Resource):
    """
    获取登录信息
    """

    def render_GET(self, request: server.Request):
        token = http_tool.get_token(request)
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
            response = {"data": user_in_db}
            request.setResponseCode(200)
        else:
            response = {
                "msg": "请先登录",
            }
            request.setResponseCode(401)
        request.setHeader(b"Content-Type", b"application/json")
        request.write(json.dumps(response, default=str).encode())
        return b""

    """
    登录或注册
    """

    def render_POST(self, request: server.Request):
        body = json.loads(request.content.read().decode("utf-8"))
        MYSQL_TOOL.execute_update(
            f"""
            insert ignore into tcwb_user (account, enc_version, password, username) values ('{body['account']}', 0, '{body['password']}', '{body['account']}')
            """
        )
        user_in_db = MYSQL_TOOL.execute_query_one(
            f"""
            select * from tcwb_user where account = '{body['account']}'                                     
            """
        )
        token = http_tool.generate_token()
        MYSQL_TOOL.execute_update(
            f"""
            insert into tcwb_user_token (token, user_account, expired_time) values ('{token}', '{user_in_db['account']}', DATE_ADD(NOW(), INTERVAL 1 YEAR))
            """
        )
        response = {"data": user_in_db, "tcwb-token": token}
        request.setHeader(b"Content-Type", b"application/json")
        request.write(json.dumps(response, default=str).encode())
        return b""

    """
    修改用户信息
    """

    def render_PUT(self, request: server.Request):
        body = json.loads(request.content.read().decode("utf-8"))
        MYSQL_TOOL.execute_update(
            f"""
            update tcwb_user username = '{body['username']}' where account = '{body['account']}'
            """
        )
        response = {}
        request.setHeader(b"Content-Type", b"application/json")
        request.write(json.dumps(response, default=str).encode())
        return b""


class HttpUserResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild(b"auth", HttpAuthResource())


def install(root: resource.Resource):
    root.putChild(b"user", HttpUserResource())
