from twisted.web import resource, server
import json

import http_tool
from mysql_tool import MYSQL_TOOL


def create_room(id, master_account, name, password):
    MYSQL_TOOL.execute_update(
        f"insert into tcwb_room (id, master_account, name, password) values ('{id}', '{master_account}', '{name}', {password})"
    )


def set_room_master(id, master_account):
    MYSQL_TOOL.execute_update(
        f"update tcwb_room set master_account = '{master_account}' where id = '{id}'"
    )


def set_room_role_count(id, loyal_count, traitor_count, rebel_count):
    MYSQL_TOOL.execute_update(
        f"update tcwb_room set loyal_count = {loyal_count}, traitor_count = {traitor_count}, rebel_count = {rebel_count} where id = '{id}'"
    )


def create_room_user(room_id, user_accounts: list):
    for user_account in user_accounts:
        MYSQL_TOOL.execute_update(
            f"insert into tcwb_room_user (room_id, user_account) values ('{room_id}', '{user_account}')"
        )


class HttpRoomResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)

    """
    分页查询房间
    """

    def render_GET(self, request: server.Request):
        user_in_db = http_tool.get_user_info_from_request(request)
        if user_in_db is not None:
            offset, _, size = http_tool.get_page_info_from_request(request)
            room_list_in_db = MYSQL_TOOL.execute_query(
                f"select * from tcwb_room order by create_time desc limit {offset}, {size}"
            )
            response = {
                "data": room_list_in_db,
            }
        else:
            response = {
                "msg": "请先登录",
            }
        request.setHeader(b"Content-Type", b"application/json")
        request.write(json.dumps(response, default=str).encode())
        return b""


def install(root: resource.Resource):
    root.putChild(b"room", HttpRoomResource())
