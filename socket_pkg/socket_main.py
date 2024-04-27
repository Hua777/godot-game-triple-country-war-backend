import json
import uuid

from twisted.internet import protocol

from http_pkg.http_user import save_user_online_tag
from http_pkg.http_room import (
    create_room,
    create_room_user,
    set_room_role_count,
    set_room_master,
    get_room,
)

SPLIT_STR = "[SPLIT]"


def make_msg(info: dict, msg_id: str = None, command: str = "ack") -> bytes:
    if msg_id is None:
        msg_id = str(uuid.uuid4())
    msg = f"{msg_id}{SPLIT_STR}{command}{SPLIT_STR}{json.dumps(info)}"
    return msg.encode("utf-8")


def parse_msg(data: bytes) -> tuple[str, str, dict]:
    data_decode = data.decode("utf-8")
    print("received message:", data_decode)
    split_array = data_decode.split(SPLIT_STR)
    msg_id = split_array[0]
    command = split_array[1]
    value = split_array[2]
    return (msg_id, command, json.loads(value))


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


class TcbwSocketProtocol(protocol.Protocol):
    def __init__(self, addr) -> None:
        super().__init__()
        self.addr = addr
        self.account: str = None
        self.room: Room = None

    def connectionMade(self):
        pass

    def write(self, info: dict, msg_id: str = None, command: str = "ack"):
        self.transport.write(make_msg(info, msg_id, command))

    def create_room(self, msg_id: str, info: dict):
        create_room(
            info["room_id"],
            self.account,
            info["room_name"],
            info["room_password"],
        )
        self.room = Room(info["room_id"])
        room_map[self.room.id] = self.room
        self.room.add_user(self)

    def join_room(self, msg_id: str, info: dict):
        room_in_db = get_room(info["room_id"])
        if room_in_db["password"] == info["input_room_password"]:
            self.room = room_map[info["room_id"]]
            for user_socket in self.room.user_sockets:
                # 广播通知房间有人进来
                user_socket.write(
                    {
                        "account": self.account,
                    },
                    command="user-join",
                )
            self.room.add_user(self)
            if msg_id is not None:
                self.write(
                    {
                        "msg": "加入房间成功",
                    },
                    msg_id=msg_id,
                )
        else:
            if msg_id is not None:
                self.write(
                    {
                        "msg": "密码错误无法加入",
                    },
                    msg_id=msg_id,
                )

    def leave_room(self, msg_id: str, info: dict):
        if self.room is not None:
            self.room.remove_user(self)
            if self.room.is_empty():
                # 房间没人了，删除房间
                del room_map[self.room.id]
            else:
                # 设置新房主
                new_master = self.room.get_any_user()
                set_room_master(self.room.id, new_master.account)
                for user_socket in self.room.user_sockets:
                    # 广播通知房间有人离开
                    user_socket.write(
                        {
                            "account": self.account,
                        },
                        command="user-leave",
                    )
                    # 广播通知换房主
                    user_socket.write(
                        {
                            "account": new_master.account,
                        },
                        command="change-master-to",
                    )
            self.room = None
            if msg_id is not None:
                self.write(
                    {
                        "msg": "离开房间成功",
                    },
                    msg_id=msg_id,
                )
        else:
            if msg_id is not None:
                self.write(
                    {
                        "msg": "不在房间里",
                    },
                    msg_id=msg_id,
                )

    def online_game(self, msg_id: str, info: dict):
        self.account = info["account"]
        save_user_online_tag(self.account, self.addr.host, self.addr.port, True)
        self.write(
            {},
            msg_id=msg_id,
        )

    def dataReceived(self, data: bytes):
        try:
            (msg_id, command, info) = parse_msg(data)
            if command == "online":
                self.online_game(msg_id, info)
            elif command == "create-room":
                self.create_room(msg_id, info)
            elif command == "join-room":
                self.join_room(msg_id, info)
            elif command == "leave-room":
                self.leave_room(msg_id, info)
        except Exception as ex:
            print("data received error:", ex)

    def connectionLost(self, reason):
        self.leave_room()
        if self.account is not None:
            print(f"{self.account} exit game, reason: {reason}")
            save_user_online_tag(self.account, self.addr.host, self.addr.port, False)


class TcbwSocketFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return TcbwSocketProtocol(addr)
