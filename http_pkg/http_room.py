from twisted.web import resource, server
import json

import http_tool
from mysql_tool import MYSQL_TOOL


def create_room(id, master_account, name, password):
    MYSQL_TOOL.execute_update(
        f"insert into tcwb_room (id, master_account, name, password) values ('{id}', '{master_account}', '{name}', {password})"
    )


def get_room(id):
    return MYSQL_TOOL.execute_query_one(f"select * from tcwb_room where id = '{id}'")


def set_room_master(id, master_account):
    MYSQL_TOOL.execute_update(
        f"update tcwb_room set master_account = '{master_account}' where id = '{id}'"
    )


def set_room_close(id):
    room_in_db = MYSQL_TOOL.execute_query_one(
        f"select * from tcwb_room where id = '{id}'"
    )
    MYSQL_TOOL.execute_update(f"delete from tcwb_room where id = '{id}'")
    MYSQL_TOOL.execute_update(
        f"insert into tcwb_room_history (room_id, master_account, name, password, loyal_count, traitor_count, rebel_count) values ('{room_in_db['id']}', '{room_in_db['master_account']}', '{room_in_db['name']}', {room_in_db['password']}, {room_in_db['loyal_count']}, {room_in_db['traitor_count']}, {room_in_db['rebel_count']})"
    ),


def set_room_role_count(id, loyal_count, traitor_count, rebel_count):
    if loyal_count == "":
        loyal_count = "0"
    if traitor_count == "":
        traitor_count = "0"
    if rebel_count == "":
        rebel_count = "0"
    MYSQL_TOOL.execute_update(
        f"update tcwb_room set loyal_count = {loyal_count}, traitor_count = {traitor_count}, rebel_count = {rebel_count} where id = '{id}'"
    )


class HttpPageResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)

    """
    分页查询房间
    """

    def render_GET(self, request: server.Request):
        user_in_db = http_tool.get_user_info_from_request(request)
        if user_in_db is not None:
            offset, _, size = http_tool.get_page_info_from_request(request)
            query_dict = http_tool.get_query_dict_from_request(request)
            key_query = (
                f"and (id like '%{query_dict['key']}%' or name like '%{query_dict['key']}%')"
                if "key" in query_dict and query_dict["key"] != ""
                else ""
            )
            status_query = (
                f"and status = {query_dict['status']}"
                if "status" in query_dict and query_dict["status"] != ""
                else ""
            )
            room_list_in_db = MYSQL_TOOL.execute_query(
                f"select * from tcwb_room where 1 = 1 {key_query} {status_query} order by create_time desc limit {offset}, {size}"
            )
            response = {
                "data": room_list_in_db,
            }
        else:
            response = {
                "msg": "请先登录",
            }
            request.setResponseCode(401)
        request.setHeader(b"Content-Type", b"application/json")
        request.write(json.dumps(response, default=str).encode())
        return b""


class HttpRoomResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild(b"page", HttpPageResource())


def install(root: resource.Resource):
    root.putChild(b"room", HttpRoomResource())
