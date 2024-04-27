import json
import uuid

from autobahn.twisted.websocket import WebSocketServerProtocol

from http_pkg.http_user import save_user_online_tag, get_user
from http_pkg.http_room import (
    create_room,
    create_room_user,
    set_room_role_count,
    set_room_master,
    get_room,
    set_room_close,
)


def parse_msg(data: bytes) -> tuple[str, str, str, dict]:
    data_decode = data.decode("utf-8")
    print("[websocket] received message:", data_decode)
    value = json.loads(data_decode)
    return (value["msg_id"], value["mode"], value["command"], value)


class Room:
    def __init__(self, id):
        super().__init__()
        self.id = id
        self.user_sockets: list[TcbwSocketProtocol] = []

    def add_user(self, user_socket):
        self.user_sockets.append(user_socket)

    def remove_user(self, user_socket):
        self.user_sockets.remove(user_socket)

    def is_empty(self):
        return len(self.user_sockets) == 0

    def get_any_user(self):
        return self.user_sockets[0] if len(self.user_sockets) > 0 else None


room_map: dict[str, Room] = {}


class TcbwSocketProtocol(WebSocketServerProtocol):
    def __init__(self) -> None:
        super().__init__()
        self.account: str = None
        self.room: Room = None

    def onConnect(self, request):
        self.host = request.host

    def onOpen(self):
        pass

    def onMessage(self, payload: bytes, isBinary):
        (msg_id, mode, command, info) = parse_msg(payload)
        if mode == "request":
            if command == "online":
                self.online_game(msg_id, info)
            elif command == "create-room":
                self.create_room(msg_id, info)
            elif command == "join-room":
                self.join_room(msg_id, info)
            elif command == "room-info":
                self.room_info(msg_id, info)
            elif command == "leave-room":
                self.leave_room(msg_id, info)
            elif command == "kick-out-user-from-room":
                self.kick_out_user_from_room(msg_id, info)
            elif command == "change-room-property":
                self.change_room_property(msg_id, info)

    def onClose(self, wasClean, code, reason):
        if self.account is not None:
            print(f"[websocket] {self.account} exit game, reason: {reason}")
            self.leave_room()
            save_user_online_tag(self.account, self.host, False)

    def send_ack(self, command: str, msg_id: str, info: dict):
        info["msg_id"] = msg_id
        info["mode"] = "response"
        info["command"] = command
        print(f"[websocket] ack message {info}")
        self.sendMessage(json.dumps(info, default=str).encode("utf-8"), False)

    def send_command(self, command: str, info: dict):
        info["msg_id"] = str(uuid.uuid4())
        info["mode"] = "request"
        info["command"] = command
        info["command"] = command
        print(f"[websocket] send message {info}")
        self.sendMessage(json.dumps(info, default=str).encode("utf-8"), False)

    def online_game(self, msg_id: str, info: dict):
        self.account = info["account"]
        save_user_online_tag(self.account, self.host, True)
        self.send_ack(
            "online",
            msg_id,
            {
                "msg": "上线成功",
            },
        )

    def create_room(self, msg_id: str, info: dict):
        msg = ""
        try:
            create_room(
                info["room_id"],
                self.account,
                info["room_name"],
                info["room_password"],
            )
            self.room = Room(info["room_id"])
            room_map[self.room.id] = self.room
            self.room.add_user(self)
        except Exception as ex:
            msg = "创建房间失败"
        self.send_ack(
            "create-room",
            msg_id,
            {
                "msg": msg,
            },
        )

    def join_room(self, msg_id: str, info: dict):
        room_in_db = get_room(info["room_id"])
        if int(room_in_db["password"]) == int(info["input_room_password"]):
            if info["room_id"] in room_map:
                self.room = room_map[info["room_id"]]
                for user_socket in self.room.user_sockets:
                    # 广播通知房间有人进来
                    user_socket.send_command(
                        "user-join",
                        {
                            "account": self.account,
                        },
                    )
                self.room.add_user(self)
                if msg_id is not None:
                    self.send_ack(
                        "join-room",
                        msg_id,
                        {},
                    )
            else:
                if msg_id is not None:
                    self.send_ack(
                        "join-room",
                        msg_id,
                        {
                            "msg": "房间不存在",
                        },
                    )
        else:
            if msg_id is not None:
                self.send_ack(
                    "join-room",
                    msg_id,
                    {
                        "msg": "密码错误无法加入",
                    },
                )

    def room_info(self, msg_id: str = None, info: dict = {}):
        if self.room is not None:
            response = {"room": get_room(self.room.id), "users": {}}
            for user_socket in self.room.user_sockets:
                response["users"][user_socket.account] = get_user(user_socket.account)
            if msg_id is not None:
                self.send_ack(
                    "room-info",
                    msg_id,
                    response,
                )
        else:
            if msg_id is not None:
                self.send_ack(
                    "room-info",
                    msg_id,
                    {
                        "msg": "不在房间里",
                    },
                )

    def leave_room(self, msg_id: str = None, info: dict = {}):
        if self.room is not None:
            self.room.remove_user(self)
            if self.room.is_empty():
                # 房间没人了，删除房间
                del room_map[self.room.id]
                set_room_close(self.room.id)
            else:
                for user_socket in self.room.user_sockets:
                    # 广播通知房间有人离开
                    user_socket.send_command(
                        "user-leave",
                        {
                            "account": self.account,
                        },
                    )
                # 设置新房主
                room_in_db = get_room(self.room.id)
                if room_in_db["master_account"] == self.account:
                    new_master = self.room.get_any_user()
                    set_room_master(self.room.id, new_master.account)
                    for user_socket in self.room.user_sockets:
                        # 广播通知换房主
                        user_socket.send_command(
                            "change-master-to",
                            {
                                "account": new_master.account,
                            },
                        )
            self.room = None
            if msg_id is not None:
                self.send_ack(
                    "leave-room",
                    msg_id,
                    {},
                )
        else:
            if msg_id is not None:
                self.send_ack(
                    "leave-room",
                    msg_id,
                    {
                        "msg": "不在房间里",
                    },
                )

    def kick_out_user_from_room(self, msg_id: str = None, info: dict = {}):
        if self.room is not None:
            room_in_db = get_room(self.room.id)
            if (
                room_in_db["master_account"] == self.account
                and self.account != info["account"]
            ):
                target_user_socket = None
                for user_socket in self.room.user_sockets:
                    if user_socket.account == info["account"]:
                        target_user_socket = user_socket
                        break
                if target_user_socket is not None:
                    self.room.remove_user(target_user_socket)
                    target_user_socket.room = None
                    for user_socket in self.room.user_sockets:
                        # 广播通知房间有人离开
                        user_socket.send_command(
                            "user-leave",
                            {
                                "account": target_user_socket.account,
                            },
                        )
                    # 通知这个人离开房间
                    target_user_socket.send_command(
                        "kick-out",
                        {},
                    )
                if msg_id is not None:
                    self.send_ack(
                        "kick-out-user-from-room",
                        msg_id,
                        {},
                    )
            else:
                if msg_id is not None:
                    self.send_ack(
                        "kick-out-user-from-room",
                        msg_id,
                        {
                            "msg": "你不是管理员",
                        },
                    )
        else:
            if msg_id is not None:
                self.send_ack(
                    "kick-out-user-from-room",
                    msg_id,
                    {
                        "msg": "不在房间里",
                    },
                )

    def change_room_property(self, msg_id: str = None, info: dict = {}):
        if self.room is not None:
            room_in_db = get_room(self.room.id)
            if room_in_db["master_account"] == self.account:
                set_room_role_count(
                    self.room.id,
                    info["loyal_count"],
                    info["traitor_count"],
                    info["rebel_count"],
                )
                for user_socket in self.room.user_sockets:
                    user_socket.send_command(
                        "room-property-changed",
                        {},
                    )
                if msg_id is not None:
                    self.send_ack(
                        "change-room-property",
                        msg_id,
                        {},
                    )
            else:
                if msg_id is not None:
                    self.send_ack(
                        "change-room-property",
                        msg_id,
                        {
                            "msg": "你不是管理员",
                        },
                    )
        else:
            if msg_id is not None:
                self.send_ack(
                    "change-room-property",
                    msg_id,
                    {
                        "msg": "不在房间里",
                    },
                )
